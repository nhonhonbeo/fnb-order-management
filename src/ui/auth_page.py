"""Giao diện đăng nhập và đăng ký tài khoản cho ứng dụng F&B Manager."""
from html import escape
import streamlit as st

from ui.state import login_user
from ui.styles import inject_css


def render():
    inject_css()

    st.markdown(
        """
        <div class="auth-brand">
            <div class="auth-brand__logo">🍜</div>
            <h1 class="auth-brand__title">F&B Order Manager</h1>
            <div class="auth-brand__subtitle">Hệ thống Quản lý Bán hàng & Bếp thông minh</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col_left, col_center, col_right = st.columns([1, 2.2, 1])
    with col_center:
        login_tab, register_tab = st.tabs(["🔐 Đăng nhập", "📝 Đăng ký tài khoản"])

        with login_tab:
            st.markdown("##### Chào mừng quay trở lại!")
            st.caption("Nhập thông tin tài khoản để truy cập hệ thống quản lý")

            with st.form("login_form", clear_on_submit=False):
                username = st.text_input("Tên đăng nhập", placeholder="Ví dụ: admin hoặc nhanvien").strip()
                password = st.text_input("Mật khẩu", type="password", placeholder="Nhập mật khẩu của bạn")
                submit_login = st.form_submit_button("🚀 Đăng nhập", type="primary", use_container_width=True)

            if submit_login:
                if not username or not password:
                    st.error("Vui lòng điền đầy đủ tên đăng nhập và mật khẩu.")
                else:
                    user = st.session_state.auth_service.authenticate(username, password)
                    if user:
                        login_user(user)
                        st.toast(f"Xin chào, {user.full_name}!", icon="👋")
                        st.rerun()
                    else:
                        st.error("Tên đăng nhập hoặc mật khẩu không chính xác.")

            st.markdown(
                """
                <div class="auth-demo-section">
                    <div class="auth-demo-title">💡 Tài khoản mẫu để kiểm thử nhanh</div>
                    <div class="auth-demo-grid">
                        <div class="demo-chip">
                            <strong>👑 Quản lý</strong>
                            TK: <code>admin</code><br>MK: <code>admin123</code>
                        </div>
                        <div class="demo-chip">
                            <strong>👤 Nhân viên</strong>
                            TK: <code>nhanvien</code><br>MK: <code>123456</code>
                        </div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            st.markdown("<div style='height: 10px'></div>", unsafe_allow_html=True)
            col_admin, col_staff = st.columns(2)
            with col_admin:
                if st.button("⚡ Vào Admin", use_container_width=True):
                    admin_user = st.session_state.auth_service.authenticate("admin", "admin123")
                    if admin_user:
                        login_user(admin_user)
                        st.toast("Đăng nhập nhanh với quyền Quản lý!", icon="👑")
                        st.rerun()
            with col_staff:
                if st.button("⚡ Vào Nhân viên", use_container_width=True):
                    staff_user = st.session_state.auth_service.authenticate("nhanvien", "123456")
                    if staff_user:
                        login_user(staff_user)
                        st.toast("Đăng nhập nhanh với quyền Nhân viên!", icon="👤")
                        st.rerun()

        with register_tab:
            st.markdown("##### Tạo tài khoản thành viên mới")
            st.caption("Điền thông tin bên dưới để đăng ký nhân viên hoặc quản lý mới")

            with st.form("register_form", clear_on_submit=False):
                reg_name = st.text_input("Họ và tên", placeholder="Ví dụ: Nguyễn Văn An").strip()
                reg_username = st.text_input(
                    "Tên đăng nhập",
                    placeholder="Chỉ gồm chữ cái, số (tối thiểu 3 ký tự)",
                ).strip()
                reg_role = st.selectbox(
                    "Vai trò / Vị trí",
                    options=["Nhân viên", "Thu ngân", "Đầu bếp", "Quản lý"],
                    index=0,
                )
                reg_password = st.text_input(
                    "Mật khẩu",
                    type="password",
                    placeholder="Tối thiểu 6 ký tự",
                )
                reg_confirm = st.text_input(
                    "Xác nhận mật khẩu",
                    type="password",
                    placeholder="Nhập lại mật khẩu phía trên",
                )
                submit_register = st.form_submit_button(
                    "✨ Hoàn tất đăng ký & Đăng nhập",
                    type="primary",
                    use_container_width=True,
                )

            if submit_register:
                if not reg_name or not reg_username or not reg_password:
                    st.error("Vui lòng điền đầy đủ tất cả các trường.")
                elif reg_password != reg_confirm:
                    st.error("Mật khẩu xác nhận không khớp.")
                elif len(reg_password) < 6:
                    st.error("Mật khẩu phải có tối thiểu 6 ký tự.")
                else:
                    success, message, new_user = st.session_state.auth_service.register(
                        username=reg_username,
                        password=reg_password,
                        full_name=reg_name,
                        role=reg_role,
                    )
                    if success and new_user:
                        login_user(new_user)
                        st.success(f"{message} Đang tự động đăng nhập...")
                        st.toast(f"Chào mừng {new_user.full_name} tham gia hệ thống!", icon="🎉")
                        st.rerun()
                    else:
                        st.error(message)
