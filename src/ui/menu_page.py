import streamlit as st

from ui.state import currency, get_current_user, sync_menu_state
from ui.styles import inject_css
from src.core.services.menu_service import DuplicateCodeError


def render():
    inject_css()
    st.title("Thực đơn")
    st.caption("Tra cứu món theo mã và quản lý danh mục thực đơn (đồng bộ Backend & Storage)")

    menu_service = st.session_state.menu_service

    search = st.text_input("Tìm theo mã hoặc tên món", placeholder="Ví dụ: F001 hoặc phở")
    keyword = search.strip()
    visible_items = menu_service.search(keyword) if keyword else menu_service.list_items(only_active=False)

    table_rows = []
    for item in visible_items:
        status_text = "🟢 Đang bán" if item.is_active else "🔴 Tạm ngừng"
        table_rows.append({
            "Mã món": item.code,
            "Tên món": item.name,
            "Giá": currency(item.price),
            "Trạng thái": status_text,
        })

    st.dataframe(
        table_rows,
        hide_index=True,
        use_container_width=True,
    )

    current_user = get_current_user()
    is_manager = current_user and current_user.role == "Quản lý"

    if is_manager:
        st.subheader("Thêm món mới (Dành cho Quản lý)")
        with st.form("add_menu_item", clear_on_submit=True):
            col1, col2, col3 = st.columns([1, 2, 1])
            item_id = col1.text_input("Mã món (VD: F006)").strip().upper()
            name = col2.text_input("Tên món").strip()
            price = col3.number_input("Giá (đ)", min_value=0, step=1000)
            submitted = st.form_submit_button("Thêm vào thực đơn", type="primary")

        if submitted:
            if not item_id or not name or price <= 0:
                st.error("Vui lòng nhập mã, tên và giá hợp lệ.")
            else:
                try:
                    new_item = menu_service.add_item(code=item_id, name=name, price=int(price))
                    sync_menu_state()
                    st.success(f"Đã lưu thành công món '{new_item.name}' vào hệ thống và cơ sở dữ liệu.")
                    st.rerun()
                except DuplicateCodeError:
                    st.error(f"Mã món '{item_id}' đã tồn tại trong thực đơn.")
                except ValueError as err:
                    st.error(str(err))
    else:
        st.caption("🔒 Quyền thêm món mới và sửa thực đơn chỉ dành cho **Quản lý**.")
