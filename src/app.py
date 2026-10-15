
import streamlit as st

from UI import dashboard, menu_page, order_page, queue_page

st.set_page_config(
    page_title="F&B Manager",
    page_icon="🍜",
    layout="wide",
)

with st.sidebar:
    st.title("🍜 F&B Manager")
    st.caption("Quản lý đơn hàng F&B")

    page = st.radio(
        "Điều hướng",
        [
            "Tổng quan",
            "Quản lý thực đơn",
            "Tạo đơn hàng",
            "Hàng đợi chế biến",
        ],
    )

if page == "Tổng quan":
    dashboard.render()
elif page == "Quản lý thực đơn":
    menu_page.render()
elif page == "Tạo đơn hàng":
    order_page.render()
elif page == "Hàng đợi chế biến":
    queue_page.render()
