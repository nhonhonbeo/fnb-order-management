import streamlit as st

from ui.state import currency, get_current_user
from ui.styles import inject_css


def render():
    inject_css()
    st.title("Thực đơn")
    st.caption("Tra cứu món theo mã và quản lý danh mục thực đơn")

    search = st.text_input("Tìm theo mã hoặc tên món", placeholder="Ví dụ: F001 hoặc phở")
    menu = st.session_state.menu
    keyword = search.strip().casefold()
    visible_items = [
        item for item in menu if not keyword or keyword in item["item_id"].casefold() or keyword in item["name"].casefold()
    ]
    st.dataframe(
        [{"Mã món": item["item_id"], "Tên món": item["name"], "Giá": currency(item["price"])} for item in visible_items],
        hide_index=True,
        use_container_width=True,
    )

    current_user = get_current_user()
    is_manager = current_user and current_user.role == "Quản lý"

    if is_manager:
        st.subheader("Thêm món mới (Dành cho Quản lý)")
        with st.form("add_menu_item", clear_on_submit=True):
            col1, col2, col3 = st.columns([1, 2, 1])
            item_id = col1.text_input("Mã món").strip().upper()
            name = col2.text_input("Tên món").strip()
            price = col3.number_input("Giá (đ)", min_value=0, step=1000)
            submitted = st.form_submit_button("Thêm vào thực đơn", type="primary")

        if submitted:
            if not item_id or not name or price <= 0:
                st.error("Vui lòng nhập mã, tên và giá hợp lệ.")
            elif any(item["item_id"] == item_id for item in menu):
                st.error("Mã món đã tồn tại.")
            else:
                menu.append({"item_id": item_id, "name": name, "price": int(price)})
                st.success(f"Đã thêm {name} vào thực đơn.")
    else:
        st.caption("🔒 Quyền thêm món mới và sửa thực đơn chỉ dành cho **Quản lý**.")
