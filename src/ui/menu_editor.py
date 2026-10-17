"""Form quản lý thêm món vào thực đơn."""
import streamlit as st

from src.core.services.menu_service import DuplicateCodeError
from ui.state import get_current_user, sync_menu_state


def render_menu_editor(menu_service) -> None:
    current_user = get_current_user()
    if not current_user or current_user.role != "Quản lý":
        st.caption("🔒 Quyền thêm món mới và sửa thực đơn chỉ dành cho **Quản lý**.")
        return

    st.subheader("Thêm món mới (Dành cho Quản lý)")
    with st.form("add_menu_item", clear_on_submit=True):
        col1, col2, col3 = st.columns([1, 2, 1])
        item_id = col1.text_input("Mã món (VD: F006)").strip().upper()
        name = col2.text_input("Tên món").strip()
        price = col3.number_input("Giá (đ)", min_value=0, step=1000)
        submitted = st.form_submit_button("Thêm vào thực đơn", type="primary")

    if not submitted:
        return

    if not item_id or not name or price <= 0:
        st.error("Vui lòng nhập mã, tên và giá hợp lệ.")
        return

    try:
        new_item = menu_service.add_item(code=item_id, name=name, price=int(price))
        sync_menu_state()
        st.success(f"Đã lưu thành công món '{new_item.name}' vào hệ thống và cơ sở dữ liệu.")
        st.rerun()
    except DuplicateCodeError:
        st.error(f"Mã món '{item_id}' đã tồn tại trong thực đơn.")
    except ValueError as error:
        st.error(str(error))