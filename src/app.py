import sys
from html import escape
from pathlib import Path
import streamlit as st

ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = Path(__file__).resolve().parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from ui import auth_page, dashboard, menu_page, order_page, queue_page, revenue_page
from ui.bootstrap import initialise_state
from ui.state import get_current_user, logout_user
from ui.styles import inject_css


ALL_PAGES = ["Quản lý bàn", "Thực đơn", "Tạo đơn hàng", "Bếp & thanh toán", "Báo cáo doanh thu"]

ROLE_PERMISSIONS = {
    "Quản lý": [
        "Quản lý bàn",
        "Thực đơn",
        "Tạo đơn hàng",
        "Bếp & thanh toán",
        "Báo cáo doanh thu",
    ],
    "Thu ngân": [
        "Quản lý bàn",
        "Bếp & thanh toán",
        "Báo cáo doanh thu",
    ],
    "Nhân viên": [
        "Quản lý bàn",
        "Tạo đơn hàng",
        "Thực đơn",
        "Bếp & thanh toán",
    ],
    "Đầu bếp": [
        "Bếp & thanh toán",
    ],
}

st.set_page_config(page_title="F&B Manager", page_icon="🍜", layout="wide")
inject_css()
initialise_state()

current_user = get_current_user()


def render_sidebar_user_profile(user):
    name_parts = user.full_name.strip().split()
    if len(name_parts) >= 2:
        initials = (name_parts[0][0] + name_parts[-1][0]).upper()
    elif name_parts:
        initials = name_parts[0][:2].upper()
    else:
        initials = user.username[:2].upper()

    role_class = {
        "Quản lý": "role--manager",
        "Nhân viên": "role--staff",
        "Thu ngân": "role--cashier",
        "Đầu bếp": "role--chef",
    }.get(user.role, "role--default")

    role_icon = {
        "Quản lý": "👑",
        "Nhân viên": "👤",
        "Thu ngân": "💵",
        "Đầu bếp": "🍳",
    }.get(user.role, "👤")

    st.markdown(
        f"""
        <div class="sidebar-user-card">
            <div class="sidebar-avatar">{escape(initials)}</div>
            <div class="sidebar-user-info">
                <div class="sidebar-user-name" title="{escape(user.full_name)}">{escape(user.full_name)}</div>
                <span class="sidebar-role-badge {role_class}">{role_icon} {escape(user.role)}</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def select_page_from_sidebar():
    st.session_state.current_page = st.session_state.navigation_widget


# Phân nhánh theo trạng thái đăng nhập
if current_user is None:
    with st.sidebar:
        st.title("🍜 F&B Manager")
        st.caption("Hệ thống quản lý bán hàng & đặt món")
        st.info("👋 Vui lòng **Đăng nhập** hoặc **Đăng ký** tài khoản để bắt đầu ca làm việc.")
        st.divider()
        st.caption("Phiên bản v1.0 • F&B Cloud POS")

    auth_page.render()
else:
    allowed_pages = ROLE_PERMISSIONS.get(current_user.role, ALL_PAGES)

    st.session_state.setdefault("current_page", allowed_pages[0])
    if st.session_state.current_page not in allowed_pages:
        st.session_state.current_page = allowed_pages[0]

    if st.session_state.get("navigation_widget") not in allowed_pages:
        st.session_state.navigation_widget = st.session_state.current_page
    elif st.session_state.get("navigation_widget") != st.session_state.current_page:
        st.session_state.navigation_widget = st.session_state.current_page

    with st.sidebar:
        st.title("🍜 F&B Manager")
        render_sidebar_user_profile(current_user)

        st.radio(
            "Điều hướng",
            allowed_pages,
            key="navigation_widget",
            on_change=select_page_from_sidebar,
        )
        st.divider()
        if "Quản lý bàn" in allowed_pages:
            st.caption(f"🟢 {len(st.session_state.tables)} bàn đang được theo dõi")
        st.caption(f"🛡️ Quyền truy cập: **{current_user.role}**")

        st.write("")
        if st.button("🚪 Đăng xuất", use_container_width=True):
            logout_user()
            st.toast("Đã đăng xuất khỏi hệ thống. Hẹn gặp lại!", icon="👋")
            st.rerun()

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
