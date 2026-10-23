import streamlit as st

from src.ui.state import get_current_user
from src.ui.styles import inject_css
from src.features.kitchen.panel import render_kitchen_queue
from src.features.payments.panel import render_payment


def render():
    inject_css()
    current_user = get_current_user()
    role = current_user.role if current_user else "Nhân viên"

    if role == "Đầu bếp":
        st.title("🍳 Bếp chế biến")
        st.caption("Theo dõi hàng đợi món ăn theo thứ tự FIFO và cập nhật tiến độ nấu")
        render_kitchen_queue()
    elif role == "Thu ngân":
        st.title("💵 Thu ngân & Thanh toán")
        st.caption("Xử lý hóa đơn bàn ăn và theo dõi tiến độ món")
        payment_tab, kitchen_tab = st.tabs(["Thanh toán hóa đơn", "Theo dõi bếp"])
        with payment_tab:
            render_payment()
        with kitchen_tab:
            render_kitchen_queue()
    else:
        st.title("Bếp & thanh toán")
        kitchen_tab, payment_tab = st.tabs(["Hàng đợi bếp", "Thanh toán"])
        with kitchen_tab:
            render_kitchen_queue()
        with payment_tab:
            render_payment()
