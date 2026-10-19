import streamlit as st
from datetime import datetime

from ui.state import currency, new_id, order_total, save_tables_state
from ui.styles import inject_css
from ui.presenters import order_views


def _cart_total(cart):
    return sum(item["price"] * item["quantity"] for item in cart)


def render():
    inject_css()
    st.title("Tạo đơn hàng")
    st.caption("Chọn bàn, thêm món và gửi đơn vào bếp (liên kết OrderService & FIFO Queue)")
    st.session_state.setdefault("cart", [])
    cart = st.session_state.cart

    available_tables = [table for table, status in st.session_state.tables.items() if status == "Trống"]
    if not available_tables:
        st.warning("Tất cả bàn đang phục vụ. Hãy thanh toán một đơn để mở lại bàn trống.")
        return

    active_menu = [item for item in st.session_state.menu if item.get("is_active", True)]
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
            f'{item["item_id"]} — {item["name"]} ({currency(item["price"])})': item
            for item in active_menu
        }
        selected_label = st.selectbox("Món ăn", list(menu_options.keys()))
        quantity = st.number_input("Số lượng", min_value=1, value=1, step=1)
        if st.button("＋ Thêm món vào giỏ", type="primary", use_container_width=True):
            item = menu_options[selected_label]
            existing = next((line for line in cart if line["item_id"] == item["item_id"]), None)
            if existing:
                existing["quantity"] += quantity
            else:
                cart.append({
                    "item_id": item["item_id"],
                    "code": item["code"],
                    "name": item["name"],
                    "price": item["price"],
                    "quantity": quantity,
                })
            st.rerun()

    st.subheader("Giỏ món đã chọn")
    if not cart:
        st.info("Chưa có món nào trong giỏ. Chọn món và số lượng ở trên rồi bấm 'Thêm món'.")
        return

    for index, item in enumerate(cart):
        row, remove_col = st.columns([6, 1])
        row.write(f"**{item['name']}** — {item['quantity']} × {currency(item['price'])} = **{currency(item['quantity'] * item['price'])}**")
        if remove_col.button("Xóa", key=f"remove_{index}"):
            cart.pop(index)
            st.rerun()

    total_amount = _cart_total(cart)
    st.markdown(f"### Tạm tính: {currency(total_amount)}")

    # Gửi đơn xuống bếp và bọc try...except bắt lỗi an toàn
    if st.button("🚀 Xác nhận & Gửi đơn xuống bếp", type="primary"):
        order_service = st.session_state.get("order_service")
        if not order_service:
            st.error("Chưa khởi tạo OrderService trong hệ thống.")
            return

        order_id = new_id("OD")

        try:
            # 1. Gọi OrderService tạo đơn (linh hoạt theo cách viết của backend)
            try:
                order = order_service.create_order(table_id=table, order_id=order_id)
            except TypeError:
                # Trường hợp backend không nhận order_id hoặc dùng tham số khác
                order = order_service.create_order(table_id=table)

            actual_order_id = getattr(order, "order_id", getattr(order, "id", order_id))

            # 2. Thêm các món vào OrderService
            for line in cart:
                order_service.add_item(actual_order_id, line["code"], line["quantity"])

            # 3. Đưa vào hàng đợi bếp FIFO
            order_service.send_to_kitchen(actual_order_id)

            # 4. Cập nhật trạng thái bàn và lưu trữ
            st.session_state.tables[table] = "Đang phục vụ"
            save_tables_state()

            # 5. Cập nhật dữ liệu trình bày từ service
            st.session_state.orders = order_views(order_service.list_orders())

            st.session_state.cart = []
            st.session_state.pop("selected_table", None)
            
            total_val = order.total() if hasattr(order, "total") else total_amount
            st.success(f"Đã tạo thành công đơn hàng {actual_order_id} cho {table} với tổng tiền {currency(total_val)}.")
            st.rerun()

        except Exception as e:
            st.error(f"Đã xảy ra lỗi khi xử lý đơn hàng: {e}")