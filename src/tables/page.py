import streamlit as st
from datetime import datetime
from html import escape

from src.ui.state import currency, refresh_order_table_state
from src.ui.styles import inject_css
from src.users.permissions import can_change_table, can_manage_tables

from streamlit_autorefresh import st_autorefresh


STATUS_STYLE = {
    "Trống": ("available", "#51CF66"),
    "Đang phục vụ": ("serving", "#FF922B"),
    "Chờ thanh toán": ("payment", "#FCC419"),
    "Cần dọn": ("cleaning", "#ADB5BD"),
}


def get_tables_status():
    return st.session_state.reporting_service.table_statuses(
        st.session_state.table_service.list_tables(),
        st.session_state.orders,
    )


def _render_table_card(table, can_delete=False, can_change=False):
    style, _ = STATUS_STYLE.get(table["status"], STATUS_STYLE["Cần dọn"])
    total_line = f"Tạm tính: {currency(table['total'])}" if table["total"] is not None else "Chưa có đơn"
    st.markdown(
        f"""
        <div class="table-card table-card--{style}">
            <div class="table-card__name">{escape(table['name'])}</div>
            <div class="table-card__seats">{table['seats']} chỗ ngồi</div>
            <div class="table-card__status">{escape(table['status'])}</div>
            <div class="table-card__meta">{escape(table['seated_time'])} · {escape(total_line)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown('<div class="table-select-button">', unsafe_allow_html=True)
    if st.button("Chọn bàn", key=f"select_{table['name']}", use_container_width=True):
        st.session_state.selected_table = table["name"]
        st.session_state.current_page = "Tạo đơn hàng"
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)
    if can_delete:
        if st.button(
            "Xoá bàn",
            key=f"delete_table_{table['name']}",
            use_container_width=True,
        ):
            st.session_state.pending_table_delete = table["name"]
            st.rerun()
    if can_change and table["status"] in {"Đang phục vụ", "Chờ thanh toán"}:
        if st.button(
            "Đổi bàn",
            key=f"change_table_{table['name']}",
            use_container_width=True,
        ):
            st.session_state.changing_table = table["name"]
            st.rerun()


def _render_change_table() -> None:
    if not can_change_table(st.session_state.get("authenticated_user")):
        return
    source_table = st.session_state.get("changing_table")
    if not source_table:
        return

    st.subheader(f"Đổi bàn: {source_table} →")
    available_tables = st.session_state.table_service.available_tables()
    if available_tables:
        target_table = st.selectbox(
            "Chọn bàn đang Trống",
            available_tables,
            key="change_table_target",
        )
    else:
        target_table = None
        st.info("Hiện không còn bàn trống để chuyển đơn.")

    confirm_column, cancel_column = st.columns(2)
    with confirm_column:
        confirmed = st.button(
            "Xác nhận",
            key="confirm_change_table",
            type="primary",
            disabled=not available_tables,
        )
    with cancel_column:
        cancelled = st.button("Hủy", key="cancel_change_table")

    if cancelled:
        st.session_state.pop("changing_table", None)
        st.rerun()
    if not confirmed or target_table is None:
        return

    try:
        order = st.session_state.order_service.change_table(
            source_table,
            target_table,
        )
    except (ValueError, RuntimeError, OSError) as error:
        st.error(str(error))
        return

    st.session_state.last_table_change_success = (
        f"Đã chuyển đơn {order.order_id} từ {source_table} sang {target_table}"
    )
    st.session_state.pop("changing_table", None)
    refresh_order_table_state(
        st.session_state.order_service,
        st.session_state.table_service,
    )
    st.rerun()


def _render_table_management():
    manager = can_manage_tables(st.session_state.get("authenticated_user"))
    if not manager:
        return

    st.subheader("Quản lý bàn")
    with st.form("add_table_form"):
        table_name = st.text_input("Tên bàn", key="new_table_name")
        submitted = st.form_submit_button("＋ Thêm bàn", key="add_table_submit")
    if submitted:
        try:
            st.session_state.table_service.add_table(table_name)
        except ValueError as error:
            st.error(str(error))
        else:
            st.session_state.tables = st.session_state.table_service.list_tables()
            st.success(f"Đã thêm bàn '{table_name.strip()}'")

    pending_table = st.session_state.get("pending_table_delete")
    if pending_table:
        st.warning(f"Bạn có chắc muốn xoá bàn '{pending_table}' không?")
        confirm_column, cancel_column = st.columns(2)
        with confirm_column:
            confirmed = st.button(
                "Xác nhận xoá bàn",
                key="confirm_delete_table",
                type="primary",
            )
        with cancel_column:
            cancelled = st.button("Huỷ", key="cancel_delete_table")
        if confirmed:
            try:
                st.session_state.table_service.delete_table(pending_table)
            except ValueError as error:
                st.error(str(error))
            else:
                st.session_state.tables = st.session_state.table_service.list_tables()
                if st.session_state.get("selected_table") == pending_table:
                    st.session_state.selected_table = None
                st.success(f"Đã xoá bàn '{pending_table}'")
            st.session_state.pending_table_delete = None
        elif cancelled:
            st.session_state.pending_table_delete = None
            st.rerun()


ORDER_STATUS = {
    "NEW": ("Mới", "new"),
    "COOKING": ("Đang nấu", "cooking"),
    "READY": ("Đã phục vụ", "ready"),
    "PAID": ("Đã thanh toán", "paid"),
    "CANCELLED": ("Đã huỷ", "cancelled"),
}


def _order_time(order):
    if not order.get("created_at"):
        return "—"
    return datetime.fromisoformat(order["created_at"]).strftime("%H:%M")


def _render_recent_order(order):
    status, style = ORDER_STATUS.get(order["status"], (order["status"], "new"))
    items_count = st.session_state.reporting_service.order_item_count(order)
    details = [
        ("Mã đơn", order["id"]),
        ("Bàn", order["table"]),
        ("Số món", items_count),
        (
            "Tổng tiền",
            currency(st.session_state.billing_service.calculate_total(order)),
        ),
        ("Thời gian", _order_time(order)),
    ]
    fields = "".join(
        f'<div><div class="order-card__label">{label}</div><div class="order-card__value">{escape(str(value))}</div></div>'
        for label, value in details
    )
    st.markdown(
        f'{"<div class=\"order-card\">"}{fields}<span class="status-badge status-badge--{style}">{status}</span></div>',
        unsafe_allow_html=True,
    )


def _render_best_sellers(orders):
    best_sellers = st.session_state.reporting_service.best_sellers(orders)
    if not best_sellers:
        st.caption("Chưa có dữ liệu món bán.")
        return
    maximum = max(quantity for _, quantity in best_sellers)
    for rank, (name, quantity) in enumerate(best_sellers, start=1):
        width = max(8, round(quantity / maximum * 100))
        st.markdown(
            f'''<div class="best-seller">
                <div class="best-seller__line"><span>{rank}. {escape(name)}</span><span>{quantity} món</span></div>
                <div class="best-seller__bar"><div class="best-seller__fill" style="width:{width}%"></div></div>
            </div>''',
            unsafe_allow_html=True,
        )


def _render_hourly_revenue(orders):
    revenue_by_hour = st.session_state.reporting_service.hourly_revenue(orders)
    st.bar_chart(
        {"Giờ": list(revenue_by_hour), "Doanh thu": list(revenue_by_hour.values())},
        x="Giờ",
        y="Doanh thu",
        color="#E8590C",
        height=210,
    )


def _format_dashboard_datetime(now):
    weekdays = ["Thứ Hai", "Thứ Ba", "Thứ Tư", "Thứ Năm", "Thứ Sáu", "Thứ Bảy", "Chủ Nhật"]
    shift = "Ca sáng" if 6 <= now.hour < 14 else "Ca chiều" if now.hour < 18 else "Ca tối"
    return f"{weekdays[now.weekday()]}, {now:%d/%m/%Y} • {shift}"


def _dashboard_alerts(orders):
    return st.session_state.reporting_service.dashboard_alerts(
        orders,
        st.session_state.kitchen_service.list_requests(),
    )


def render():
    inject_css()
    st_autorefresh(interval=30_000, key="dashboard_refresh")
    success_message = st.session_state.pop("last_table_change_success", None)
    if success_message:
        st.success(success_message)
    manager = can_manage_tables(st.session_state.get("authenticated_user"))

    title_column, create_column, refresh_column = st.columns([4, 1.25, 1])
    with title_column:
        st.title("Quản lý bàn")
        st.markdown(f'<div class="dashboard-date">{_format_dashboard_datetime(datetime.now())}</div>', unsafe_allow_html=True)
    with create_column:
        st.write("")
        if st.button("＋ Tạo đơn", type="primary", use_container_width=True):
            st.session_state.current_page = "Tạo đơn hàng"
            st.rerun()
    with refresh_column:
        st.write("")
        if st.button("🔄 Làm mới", use_container_width=True):
            st.rerun()

    _render_table_management()

    orders = st.session_state.orders
    for alert in _dashboard_alerts(orders):
        st.markdown(f'<div class="alert-banner">⚠️ {escape(alert)}</div>', unsafe_allow_html=True)

    st.subheader("Sơ đồ bàn")
    legend = "".join(
        f'<span class="table-legend__item"><span class="table-legend__dot" style="background:{color}"></span>{status}</span>'
        for status, (_, color) in STATUS_STYLE.items()
    )
    st.markdown(f'<div class="table-legend">{legend}</div>', unsafe_allow_html=True)
    table_data = get_tables_status()
    if not table_data:
        st.info("Chưa có bàn. Quản lý có thể thêm bàn trong khu vực quản lý bàn.")
    for offset in range(0, len(table_data), 5):
        columns = st.columns(5)
        for column, table in zip(columns, table_data[offset : offset + 5]):
            with column:
                _render_table_card(
                    table,
                    can_delete=manager,
                    can_change=can_change_table(
                        st.session_state.get("authenticated_user")
                    ),
                )
    _render_change_table()
