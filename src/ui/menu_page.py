import streamlit as st

from ui.state import currency
from ui.styles import inject_css
from ui.menu_editor import render_menu_editor


def render():
    inject_css()
    st.title("Thực đơn")
    st.caption("Tra cứu món theo mã và quản lý danh mục thực đơn (đồng bộ Backend & Storage)")

    menu_service = st.session_state.get("menu_service")
    if not menu_service:
        st.warning("Chưa khởi tạo MenuService trong hệ thống.")
        return

    search = st.text_input("Tìm theo mã hoặc tên món", placeholder="Ví dụ: F001 hoặc phở")
    keyword = search.strip()
    
    try:
        visible_items = menu_service.search(keyword) if keyword else menu_service.list_items(only_active=False)
    except Exception as e:
        st.error(f"Lỗi khi tìm kiếm thực đơn: {e}")
        visible_items = []

    st.divider()
    st.subheader("📋 Danh sách món ăn & Thao tác quản lý")

    if not visible_items:
        st.info("Không tìm thấy món ăn nào trong thực đơn.")
    else:
        for item in visible_items:
            with st.container():
                col1, col2, col3, col4, col5 = st.columns([1.5, 2.5, 1.5, 1.5, 1.5])
                with col1:
                    st.text(f"Mã: {item.code}")
                with col2:
                    st.write(f"**{item.name}**")
                    st.caption(f"Giá: {currency(item.price)}")
                with col3:
                    status_text = "🟢 Đang bán" if item.is_active else "🔴 Tạm ngừng"
                    st.write(status_text)
                with col4:
                    # Nút Ngừng bán / Bật bán lại
                    toggle_label = "Ngừng bán" if item.is_active else "Bật bán lại"
                    if st.button(toggle_label, key=f"toggle_{item.code}"):
                        try:
                            if hasattr(menu_service, "toggle_status"):
                                menu_service.toggle_status(item.code)
                            elif hasattr(menu_service, "update_item"):
                                item.is_active = not item.is_active
                                menu_service.update_item(item.code, is_active=item.is_active)
                            else:
                                item.is_active = not item.is_active
                            st.success(f"Đã cập nhật trạng thái món {item.name}")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Lỗi cập nhật trạng thái: {e}")
                with col5:
                    # Nút Xóa món
                    if st.button("🗑️ Xóa", key=f"delete_{item.code}"):
                        try:
                            if hasattr(menu_service, "remove_item"):
                                menu_service.remove_item(item.code)
                            elif hasattr(menu_service, "delete_item"):
                                menu_service.delete_item(item.code)
                            st.success(f"Đã xóa món {item.name}")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Lỗi khi xóa món: {e}")

                # Khu vực chỉnh sửa thông tin món nhanh (Sửa tên, giá)
                with st.expander(f"✏️ Sửa thông tin: {item.name}"):
                    with st.form(key=f"edit_form_{item.code}"):
                        new_name = st.text_input("Tên món mới", value=item.name, key=f"edit_name_{item.code}")
                        new_price = st.number_input("Giá mới", value=float(item.price), min_value=0.0, step=1000.0, key=f"edit_price_{item.code}")
                        submit_edit = st.form_submit_button("Lưu thay đổi")
                        if submit_edit:
                            try:
                                if hasattr(menu_service, "update_item"):
                                    menu_service.update_item(item.code, name=new_name, price=new_price)
                                else:
                                    item.name = new_name
                                    item.price = new_price
                                st.success(f"Đã cập nhật thông tin món {item.code} thành công!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Lỗi khi sửa món: {e}")
                st.divider()

    # Giữ lại module quản lý/thêm mới món sẵn có của nhóm
    render_menu_editor(menu_service)