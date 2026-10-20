import streamlit as st

from src.ui.state import currency
from src.ui.styles import inject_css
from src.ui.presenters import order_views


def render():
    inject_css()
    st.title("Tạo đơn hàng")
    st.caption("Chọn bàn, thêm món và gửi đơn vào bếp (liên kết OrderService & FIFO Queue)")
    st.session_state.setdefault("cart", [])
    cart = st.session_state.cart

    order_service = st.session_state.order_service
    table_service = st.session_state.table_service
    available_tables = table_service.available_tables()
    if not available_tables:
        st.warning("Tất cả bàn đang phục vụ. Hãy thanh toán một đơn để mở lại bàn trống.")
        return

    active_menu = st.session_state.menu_service.list_items(only_active=True)
    if not active_menu:
        st.warning("Thực đơn đang trống hoặc chưa có món mở bán. Hãy thêm món trước.")
        return

    col1, col2 = st.columns([1, 1])
    with col1:
        selected_table = st.session_state.get("selected_table")
        selected_index = available_tables.index(selected_table) if selected_table in available_tables else 0
        table = st.selectbox("Bàn phục vụ", available_tables, index=selected_index)
    with col2:
        menu_options = {
            f"{item.code} — {item.name} ({currency(item.price)})": item
            for item in active_menu
        }
        selected_label = st.selectbox("Món ăn", list(menu_options.keys()))
        quantity = st.number_input("Số lượng", min_value=1, value=1, step=1)
        if st.button("＋ Thêm món vào giỏ", type="primary", use_container_width=True):
            item = menu_options[selected_label]
            try:
                order_service.add_to_cart(cart, item.code, quantity)
            except ValueError as error:
                st.error(str(error))
                return
            st.rerun()

    st.subheader("Giỏ món đã chọn")
    if not cart:
        st.info("Chưa có món nào trong giỏ. Chọn món và số lượng ở trên rồi bấm 'Thêm món'.")
        return

    for index, item in enumerate(cart):
        row, remove_col = st.columns([6, 1])
        subtotal = order_service.calculate_cart_total([item])
        row.write(
            f"**{item['name']}** — {item['quantity']} × "
            f"{currency(item['price'])} = **{currency(subtotal)}**"
        )
        if remove_col.button("Xóa", key=f"remove_{index}"):
            cart.pop(index)
            st.rerun()

    try:
        total_amount = order_service.calculate_cart_total(cart)
    except ValueError as error:
        st.error(f"Không thể tính giỏ hàng: {error}")
        return
    st.markdown(f"### Tạm tính: {currency(total_amount)}")

    if st.button("🚀 Xác nhận & Gửi đơn xuống bếp", type="primary"):
        try:
            order = order_service.create_order_from_cart(table, cart)
            st.session_state.tables = table_service.list_tables()
            st.session_state.orders = order_views(order_service.list_orders())
            st.session_state.cart = []
            st.session_state.pop("selected_table", None)
            st.success(
                f"Đã tạo thành công đơn hàng {order.order_id} cho {table} "
                f"với tổng tiền {currency(order.total())}."
            )
            st.rerun()
        except ValueError as error:
            st.error(f"Không thể tạo đơn hàng: {error}")
        except Exception as error:
            st.error(f"Đã xảy ra lỗi khi xử lý đơn hàng: {error}")