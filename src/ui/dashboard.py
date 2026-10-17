import streamlit as st
from datetime import datetime
from html import escape
from collections import Counter

from ui.components import kpi_card
from ui.state import currency, order_total
from ui.styles import inject_css

from streamlit_autorefresh import st_autorefresh


STATUS_STYLE = {
    "Trống": ("available", "#51CF66"),
    "Đang phục vụ": ("serving", "#FF922B"),
    "Chờ thanh toán": ("payment", "#FCC419"),
    "Cần dọn": ("cleaning", "#ADB5BD"),
}


def get_tables_status():
    """Chuẩn bị dữ liệu sơ đồ bàn từ trạng thái phiên hiện có.

    Dữ liệu mẫu được trả về khi ứng dụng chưa khởi tạo danh sách bàn.
    """
    tables = st.session_state.get("tables") or {f"Bàn {index}": "Trống" for index in range(1, 11)}
    active_orders = {
        order["table"]: order
        for order in st.session_state.get("orders", [])
        if order["status"] != "PAID"
    }
    result = []
    for index, (name, source_status) in enumerate(tables.items(), start=1):
        order = active_orders.get(name)
        status = source_status
        if order and order["status"] == "READY":
            status = "Chờ thanh toán"
        total = order_total(order) if order else None
        seated_time = "—"
        if order and order.get("created_at"):
            started_at = datetime.fromisoformat(order["created_at"])
            minutes = max(0, int((datetime.now() - started_at).total_seconds() // 60))
            seated_time = f"{minutes} phút"
        result.append(
            {
                "name": name,
                "seats": 4 if index % 3 else 6,
                "status": status,
                "seated_time": seated_time,
                "total": total,
            }
        )
    return result


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
    items_count = sum(item["quantity"] for item in order["items"])
    details = [
        ("Mã đơn", order["id"]),
        ("Bàn", order["table"]),
        ("Số món", items_count),
        ("Tổng tiền", currency(order_total(order))),
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
    counts = Counter(
        item["name"]
        for order in orders
        for item in order["items"]
        for _ in range(item["quantity"])
    )
    if not counts:
        st.caption("Chưa có dữ liệu món bán.")
        return
    maximum = max(counts.values())
    for rank, (name, quantity) in enumerate(counts.most_common(5), start=1):
        width = max(8, round(quantity / maximum * 100))
        st.markdown(
            f'''<div class="best-seller">
                <div class="best-seller__line"><span>{rank}. {escape(name)}</span><span>{quantity} món</span></div>
                <div class="best-seller__bar"><div class="best-seller__fill" style="width:{width}%"></div></div>
            </div>''',
            unsafe_allow_html=True,
        )


def _render_hourly_revenue(orders):
    revenue_by_hour = {f"{hour:02d}:00": 0 for hour in range(9, 19)}
    for order in orders:
        if not order.get("created_at"):
            continue
        hour = datetime.fromisoformat(order["created_at"]).hour
        key = f"{hour:02d}:00"
        if key in revenue_by_hour:
            revenue_by_hour[key] += order_total(order)
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
    now = datetime.now()
    waiting_order_ids = {
        request.order_id
        for request in st.session_state.kitchen_service.list_requests()
        if request.status in {"NEW", "COOKING"}
    }
    delayed_items = 0
    long_seated_tables = 0
    for order in orders:
        if not order.get("created_at"):
            continue
        elapsed_minutes = (now - datetime.fromisoformat(order["created_at"])).total_seconds() / 60
        if order["id"] in waiting_order_ids and elapsed_minutes > 15:
            delayed_items += sum(item["quantity"] for item in order["items"])
        if order["status"] != "PAID" and elapsed_minutes > 120:
            long_seated_tables += 1
    alerts = []
    if delayed_items:
        alerts.append(f"{delayed_items} món đang chờ bếp quá 15 phút.")
    if long_seated_tables:
        alerts.append(f"{long_seated_tables} bàn đã ngồi quá 2 giờ.")
    return alerts


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
    free_tables = sum(status == "Trống" for status in st.session_state.tables.values())

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
