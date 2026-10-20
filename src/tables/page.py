import streamlit as st
from datetime import datetime
from html import escape

from src.ui.state import currency
from src.ui.styles import inject_css

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


def _render_table_card(table):
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


ORDER_STATUS = {
    "NEW": ("Mới", "new"),
    "COOKING": ("Đang nấu", "cooking"),
    "READY": ("Đã phục vụ", "ready"),
    "PAID": ("Đã thanh toán", "paid"),
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
    for offset in range(0, len(table_data), 5):
        columns = st.columns(5)
        for column, table in zip(columns, table_data[offset : offset + 5]):
            with column:
                _render_table_card(table)
