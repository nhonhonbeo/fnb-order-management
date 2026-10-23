"""Form quản lý thêm món vào thực đơn."""
import streamlit as st

from src.features.menu.service import DuplicateCodeError
from src.ui.state import get_current_user, sync_menu_state
from src.users.permissions import can_manage_menu


def render_menu_editor(menu_service) -> None:
    current_user = get_current_user()
    if not can_manage_menu(current_user):
        st.caption("🔒 Quyền thêm món mới và sửa thực đơn chỉ dành cho **Quản lý**.")
        return

    st.subheader("Thêm món mới (Dành cho Quản lý)")
    with st.form("add_menu_item", clear_on_submit=True):
        col1, col2, col3 = st.columns([1, 2, 1])
        item_id = col1.text_input("Mã món (VD: F006)", key="new_menu_code").strip().upper()
        name = col2.text_input("Tên món", key="new_menu_name").strip()
        price = col3.number_input("Giá (đ)", min_value=0, step=1000, key="new_menu_price")
        submitted = st.form_submit_button(
            "Thêm vào thực đơn",
            type="primary",
            key="add_menu_submit",
        )

    if not submitted:
        return

    try:
        new_item = menu_service.add_item(item_id, name=name, price=int(price))
        sync_menu_state()
        st.success(f"Đã lưu thành công món '{new_item.name}' vào hệ thống và cơ sở dữ liệu.")
        st.rerun()
    except DuplicateCodeError:
        st.error(f"Mã món '{item_id}' đã tồn tại trong thực đơn.")
    except ValueError as error:
        st.error(str(error))