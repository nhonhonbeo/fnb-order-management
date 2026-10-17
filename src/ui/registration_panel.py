"""Form đăng ký tài khoản nhân viên hoặc quản lý."""
import streamlit as st

from ui.state import login_user


def render_registration_panel() -> None:
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

    if not submit_register:
        return
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