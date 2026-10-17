import streamlit as st

from ui.state import currency
from ui.styles import inject_css
from ui.menu_editor import render_menu_editor


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

    render_menu_editor(menu_service)
