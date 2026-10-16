import streamlit as st
from datetime import datetime

from ui.state import currency, new_id, order_total
from ui.styles import inject_css


def _cart_total(cart):
    return sum(item["price"] * item["quantity"] for item in cart)


def render():
    inject_css()
    st.title("Tạo đơn hàng")
    st.caption("Chọn bàn, thêm món và gửi đơn vào bếp")
    st.session_state.setdefault("cart", [])
    cart = st.session_state.cart

    available_tables = [table for table, status in st.session_state.tables.items() if status == "Trống"]
    if not available_tables:
        st.warning("Tất cả bàn đang phục vụ. Hãy thanh toán một đơn để mở bàn.")
        return
    if not st.session_state.menu:
        st.warning("Thực đơn đang trống. Hãy thêm món trước.")
        return

    col1, col2 = st.columns([1, 1])
    with col1:
        selected_table = st.session_state.get("selected_table")
        selected_index = available_tables.index(selected_table) if selected_table in available_tables else 0
        table = st.selectbox("Bàn phục vụ", available_tables, index=selected_index)
    with col2:
        menu_options = {f'{item["item_id"]} — {item["name"]} ({currency(item["price"])})': item for item in st.session_state.menu}
        selected_label = st.selectbox("Món", menu_options)
        quantity = st.number_input("Số lượng", min_value=1, value=1, step=1)
        if st.button("Thêm món", type="primary", use_container_width=True):
            item = menu_options[selected_label]
            existing = next((line for line in cart if line["item_id"] == item["item_id"]), None)
            if existing:
                existing["quantity"] += quantity
            else:
                cart.append({**item, "quantity": quantity})
            st.rerun()

    st.subheader("Giỏ món")
    if not cart:
        st.info("Chưa có món nào trong đơn.")
        return
    for index, item in enumerate(cart):
        row, remove_col = st.columns([6, 1])
        row.write(f"**{item['name']}** — {item['quantity']} × {currency(item['price'])} = {currency(item['quantity'] * item['price'])}")
        if remove_col.button("Xóa", key=f"remove_{index}"):
            cart.pop(index)
            st.rerun()
    st.markdown(f"### Tạm tính: {currency(_cart_total(cart))}")
    if st.button("Xác nhận & gửi bếp", type="primary"):
        order = {"id": new_id("OD"), "table": table, "items": [item.copy() for item in cart], "status": "NEW", "created_at": datetime.now().isoformat()}
        st.session_state.orders.append(order)
        for item in order["items"]:
            st.session_state.kitchen_queue.append({"order_id": order["id"], "table": table, **item, "status": "NEW"})
        st.session_state.tables[table] = "Đang phục vụ"
        st.session_state.cart = []
        st.success(f"Đã tạo {order['id']} với tổng tiền {currency(order_total(order))}.")
