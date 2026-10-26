"""Form quản lý thêm và chỉnh sửa món ăn trong thực đơn."""
import streamlit as st

from src.features.menu.service import DuplicateCodeError
from src.ui.state import get_current_user, sync_menu_state
from src.users.permissions import can_manage_menu


def render_menu_editor(menu_service) -> None:
    current_user = get_current_user()
    if not can_manage_menu(current_user):
        st.caption("🔒 Quyền quản lý và cấu hình thực đơn/thời gian bếp chỉ dành cho **Quản lý**.")
        return

    st.subheader("➕ Thêm món mới vào thực đơn")
    with st.form("add_menu_item", clear_on_submit=True):
        col1, col2, col3, col4 = st.columns([1, 2, 1, 1])
        item_id = col1.text_input("Mã món (VD: F006)", key="new_menu_code").strip().upper()
        name = col2.text_input("Tên món", key="new_menu_name").strip()
        price = col3.number_input("Giá (đ)", min_value=0, step=1000, key="new_menu_price")
        # Cho phép định nghĩa thời gian chế biến ban đầu (phục vụ thuật toán SPTF)
        processing_time = col4.number_input("TG nấu (phút)", min_value=1, value=5, key="new_menu_time")
        
        submitted = st.form_submit_button(
            "Thêm vào thực đơn",
            type="primary",
            key="add_menu_submit",
        )

    if submitted:
        try:
            new_item = menu_service.add_item(
                item_id, 
                name=name, 
                price=int(price), 
                processing_time=int(processing_time)
            )
            sync_menu_state()
            st.success(f"Đã lưu thành công món '{new_item.name}' vào hệ thống!")
            st.rerun()
        except DuplicateCodeError:
            st.error(f"Mã món '{item_id}' đã tồn tại trong thực đơn.")
        except ValueError as error:
            st.error(str(error))

    st.divider()
    st.subheader("✏️ Cập nhật thời gian chế biến & thông tin món hiện có")
    items = menu_service.list_items()
    if not items:
        st.info("Chưa có món ăn nào trong thực đơn.")
        return

    for idx, item in enumerate(items):
        expander_label = f"[{item.code}] {item.name} — {item.price:,}đ (TG nấu: {item.processing_time} phút)"
        with st.expander(expander_label):
            with st.form(key=f"edit_form_{item.code}_{idx}"):
                e_col1, e_col2, e_col3 = st.columns([2, 1, 1])
                new_name = e_col1.text_input("Tên món", value=item.name, key=f"name_{item.code}_{idx}")
                new_price = e_col2.number_input("Giá (đ)", value=item.price, step=1000, key=f"price_{item.code}_{idx}")
                
                # Cho phép điều chỉnh linh hoạt thời gian hoàn thành (SPTF)
                new_time = e_col3.number_input(
                    "TG nấu (phút)", 
                    min_value=1, 
                    value=item.processing_time, 
                    key=f"time_{item.code}_{idx}"
                )

                update_submitted = st.form_submit_button("Lưu thay đổi", key=f"btn_edit_{item.code}_{idx}")
                if update_submitted:
                    try:
                        menu_service.update_item(
                            item_code=item.code,
                            name=new_name,
                            price=int(new_price),
                            processing_time=int(new_time)
                        )
                        sync_menu_state()
                        st.success(f"Đã cập nhật thông tin món '{item.code}' thành công!")
                        st.rerun()
                    except ValueError as err:
                        st.error(str(err))