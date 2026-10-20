"""Trang theo dõi doanh thu và đơn hàng gần đây."""
from datetime import datetime
from html import escape

import streamlit as st

from src.ui.state import currency, get_current_user
from src.ui.styles import inject_css
from src.users.permissions import can_view_revenue


STATUS = {
    "NEW": ("Mới", "new"),
    "COOKING": ("Đang nấu", "cooking"),
    "READY": ("Đã phục vụ", "ready"),
    "PAID": ("Đã thanh toán", "paid"),
}


def _order_time(order):
    return datetime.fromisoformat(order["created_at"]).strftime("%H:%M") if order.get("created_at") else "—"


def _render_order_card(order):
    status, style = STATUS.get(order["status"], (order["status"], "new"))
    values = [
        ("Mã đơn", order["id"]),
        ("Bàn", order["table"]),
        (
            "Số món",
            st.session_state.reporting_service.order_item_count(order),
        ),
        (
            "Tổng tiền",
            currency(st.session_state.billing_service.calculate_total(order)),
        ),
        ("Thời gian", _order_time(order)),
    ]
    fields = "".join(
        f'<div><div class="order-card__label">{label}</div><div class="order-card__value">{escape(str(value))}</div></div>'
        for label, value in values
    )
    st.markdown(
        f'<div class="order-card">{fields}<span class="status-badge status-badge--{style}">{status}</span></div>',
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
            f'''<div class="best-seller"><div class="best-seller__line"><span>{rank}. {escape(name)}</span><span>{quantity} món</span></div>
            <div class="best-seller__bar"><div class="best-seller__fill" style="width:{width}%"></div></div></div>''',
            unsafe_allow_html=True,
        )


def _render_hourly_revenue(orders):
    revenue_by_hour = st.session_state.reporting_service.hourly_revenue(orders)
    st.bar_chart({"Giờ": list(revenue_by_hour), "Doanh thu": list(revenue_by_hour.values())}, x="Giờ", y="Doanh thu", color="#E8590C", height=210)


def render():
    inject_css()
    current_user = get_current_user()
    if not can_view_revenue(current_user):
        st.title("Báo cáo doanh thu")
        st.warning("🔒 Bạn không có quyền truy cập trang này. Báo cáo tài chính & doanh thu chỉ dành cho **Quản lý** và **Thu ngân**.")
        return

    st.title("Báo cáo doanh thu")
    st.caption("Theo dõi doanh thu, đơn hàng và món bán chạy trong phiên hiện tại")
    orders = st.session_state.orders
    revenue = st.session_state.billing_service.get_total_revenue()
    col1, col2 = st.columns(2)
    col1.metric("Doanh thu", currency(revenue))
    col2.metric("Tổng đơn hàng", len(orders))

    st.subheader("Đơn hàng gần đây")
    if not orders:
        st.info("Chưa có đơn hàng để báo cáo.")
        return
    recent_column, insights_column = st.columns([2, 1], gap="large")
    with recent_column:
        for order in reversed(orders[-5:]):
            _render_order_card(order)
    with insights_column:
        st.markdown("#### Món bán chạy hôm nay")
        _render_best_sellers(orders)
        st.markdown("#### Doanh thu theo giờ")
        _render_hourly_revenue(orders)
