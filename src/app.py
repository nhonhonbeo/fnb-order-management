import streamlit as st

from ui import dashboard, menu_page, order_page, queue_page, revenue_page
from ui.state import initialise_state
from ui.styles import inject_css


PAGES = ["Quản lý bàn", "Thực đơn", "Tạo đơn hàng", "Bếp & thanh toán", "Báo cáo doanh thu"]

st.set_page_config(page_title="F&B Manager", page_icon="🍜", layout="wide")
inject_css()
initialise_state()

st.session_state.setdefault("current_page", PAGES[0])
if st.session_state.current_page not in PAGES:
    st.session_state.current_page = PAGES[0]
# Đồng bộ trước khi tạo radio: các nút ở trang con chỉ cập nhật current_page,
# không trực tiếp thay đổi session state đã được widget sử dụng.
if st.session_state.get("navigation_widget") != st.session_state.current_page:
    st.session_state.navigation_widget = st.session_state.current_page


def select_page_from_sidebar():
    st.session_state.current_page = st.session_state.navigation_widget


with st.sidebar:
    st.title("🍜 F&B Manager")
    st.caption("Quản lý đơn hàng nhà hàng")
    st.radio(
        "Điều hướng",
        PAGES,
        key="navigation_widget",
        on_change=select_page_from_sidebar,
    )
    st.divider()
    st.caption(f"🟢 {len(st.session_state.tables)} bàn đang được theo dõi")

page = st.session_state.current_page
if page == "Quản lý bàn":
    dashboard.render()
elif page == "Thực đơn":
    menu_page.render()
elif page == "Tạo đơn hàng":
    order_page.render()
elif page == "Bếp & thanh toán":
    queue_page.render()
else:
    revenue_page.render()
