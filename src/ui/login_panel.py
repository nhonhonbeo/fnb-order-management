"""Form đăng nhập và đăng nhập nhanh."""
import streamlit as st

from ui.state import login_user


def render_login_panel() -> None:
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