
import streamlit as st


def render():
    st.title("Tổng quan")
    st.caption("Theo dõi hoạt động cửa hàng")

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Tổng số món", 12)
    col2.metric("Đơn chờ chế biến", 5)
    col3.metric("Đang chế biến", 2)
    col4.metric("Đã hoàn thành", 18)

    st.subheader("Hoạt động gần đây")
    st.info(
        "Dữ liệu hiện là dữ liệu minh họa. "
        "Sẽ kết nối với Core Logic sau."
    )
