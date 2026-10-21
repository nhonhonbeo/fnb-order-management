import streamlit as st

from src.ui.state import (
    currency,
    get_current_user,
    refresh_order_table_state,
)
from src.ui.styles import inject_css
from src.users.permissions import can_cancel_order, can_edit_order


STATUS_LABELS = {
    "NEW": "Mới",
    "IN_PROGRESS": "Đang chế biến",
    "COMPLETED": "Hoàn tất",
    "PAID": "Đã thanh toán",
    "CANCELLED": "Đã huỷ",
}


def _render_create_order():
    st.title("Tạo đơn hàng")
    st.caption("Chọn bàn, thêm món và gửi đơn vào bếp")
    st.session_state.setdefault("cart", [])
    cart = st.session_state.cart

    order_service = st.session_state.order_service
    table_service = st.session_state.table_service
    available_tables = table_service.available_tables()
    active_menu = st.session_state.menu_service.list_items(only_active=True)
    if not table_service.list_tables():
        st.warning("Chưa có bàn. Hãy nhờ Quản lý thêm bàn trước khi tạo đơn hàng.")
        return
    if not available_tables:
        st.warning("Tất cả bàn đang phục vụ. Hãy thanh toán hoặc huỷ đơn để mở lại bàn trống.")
        return
    if not active_menu:
        st.warning("Thực đơn đang trống hoặc chưa có món mở bán. Hãy thêm món trước.")
        return

    col1, col2 = st.columns([1, 1])
    with col1:
        selected_table = st.session_state.get("selected_table")
        selected_index = (
            available_tables.index(selected_table)
            if selected_table in available_tables
            else 0
        )
        table = st.selectbox(
            "Bàn phục vụ",
            available_tables,
            index=selected_index,
            key="new_order_table",
        )
    with col2:
        menu_options = {
            f"{item.code} — {item.name} ({currency(item.price)})": item
            for item in active_menu
        }
        selected_label = st.selectbox(
            "Món ăn",
            list(menu_options.keys()),
            key="new_order_menu_item",
        )
        quantity = st.number_input(
            "Số lượng",
            min_value=1,
            value=1,
            step=1,
            key="new_order_quantity",
        )
        if st.button(
            "＋ Thêm món vào giỏ",
            type="primary",
            use_container_width=True,
            key="add_to_cart",
        ):
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

    if st.button(
        "🚀 Xác nhận & Gửi đơn xuống bếp",
        type="primary",
        key="create_order_submit",
    ):
        try:
            order = order_service.create_order_from_cart(table, cart)
            refresh_order_table_state(order_service, table_service)
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


def _render_edit_form(order, user, order_service, table_service):
    menu_service = st.session_state.menu_service
    available_menu = menu_service.list_items(only_active=True)
    tables = table_service.list_tables()
    table_options = list(tables)
    if order.table_id and order.table_id not in table_options:
        table_options.append(order.table_id)
    current_table = order.table_id if order.table_id in table_options else table_options[0]

    with st.form(f"edit_order_{order.order_id}"):
        st.markdown("**Sửa thông tin đơn**")
        selected_table = st.selectbox(
            "Bàn",
            table_options,
            index=table_options.index(current_table),
            key=f"edit_table_{order.order_id}",
        )
        note = st.text_area(
            "Ghi chú",
            value=order.note,
            key=f"edit_note_{order.order_id}",
        )
        desired_items = []
        for item in order.items:
            quantity = st.number_input(
                f"{item.item_name} ({item.item_code}) — số lượng, nhập 0 để xoá",
                min_value=0,
                value=item.quantity,
                step=1,
                key=f"edit_quantity_{order.order_id}_{item.item_code}",
            )
            if quantity:
                desired_items.append({
                    "code": item.item_code,
                    "quantity": quantity,
                })

        menu_options = {
            f"{item.code} — {item.name}": item.code
            for item in available_menu
        }
        add_label = st.selectbox(
            "Thêm món",
            ["Không thêm món"] + list(menu_options),
            key=f"edit_add_menu_{order.order_id}",
        )
        add_quantity = st.number_input(
            "Số lượng món thêm",
            min_value=1,
            value=1,
            step=1,
            key=f"edit_add_quantity_{order.order_id}",
        )
        submitted = st.form_submit_button(
            "Lưu thay đổi",
            key=f"save_order_{order.order_id}",
        )

    if not submitted:
        return
    if add_label != "Không thêm món":
        add_code = menu_options[add_label]
        existing_line = next(
            (line for line in desired_items if line["code"] == add_code),
            None,
        )
        if existing_line is None:
            desired_items.append({"code": add_code, "quantity": add_quantity})
        else:
            existing_line["quantity"] += add_quantity
    try:
        order_service.edit_order(
            order.order_id,
            desired_items,
            user=user,
            note=note,
            table_id=selected_table,
        )
        refresh_order_table_state(order_service, table_service)
        st.success(f"Đã cập nhật đơn {order.order_id}.")
        st.rerun()
    except (ValueError, RuntimeError, OSError) as error:
        st.error(f"Không thể sửa đơn {order.order_id}: {error}")


def _render_cancel_form(order, user, order_service, table_service):
    cancel_key = "cancel_order_id"
    if st.button("Huỷ đơn", key=f"show_cancel_{order.order_id}"):
        st.session_state[cancel_key] = order.order_id
    if st.session_state.get(cancel_key) != order.order_id:
        return

    st.warning(f"Xác nhận huỷ đơn {order.order_id}. Thao tác này không thể hoàn tác.")
    with st.form(f"cancel_order_{order.order_id}"):
        reason = st.text_input(
            "Lý do huỷ",
            key=f"cancel_reason_{order.order_id}",
        )
        confirmed = st.form_submit_button(
            "Xác nhận huỷ đơn",
            key=f"confirm_cancel_{order.order_id}",
        )
    if not confirmed:
        if st.button("Không huỷ", key=f"dismiss_cancel_{order.order_id}"):
            st.session_state.pop(cancel_key, None)
            st.rerun()
        return
    try:
        order_service.cancel_order(order.order_id, reason, user)
        refresh_order_table_state(order_service, table_service)
        st.session_state.pop(cancel_key, None)
        st.success(f"Đơn {order.order_id} đã được huỷ.")
    except (ValueError, RuntimeError, OSError) as error:
        st.error(f"Không thể huỷ đơn {order.order_id}: {error}")


def _render_order_list():
    order_service = st.session_state.order_service
    table_service = st.session_state.table_service
    user = get_current_user()
    st.divider()
    st.subheader("Đơn hàng")
    orders = list(reversed(order_service.list_orders()))
    if not orders:
        st.info("Chưa có đơn hàng.")
        return

    for order in orders:
        status = STATUS_LABELS.get(order.status, order.status)
        with st.expander(
            f"{order.order_id} · {order.table_id or 'Chưa chọn bàn'} · {status} · "
            f"{currency(order.total())}"
        ):
            st.write(f"**Ghi chú:** {order.note or '—'}")
            for item in order.items:
                st.write(
                    f"- {item.item_name}: {item.quantity} × "
                    f"{currency(item.unit_price)}"
                )
            if order.cancel_reason:
                st.caption(f"Lý do huỷ: {order.cancel_reason}")

            if can_edit_order(user, order):
                _render_edit_form(order, user, order_service, table_service)
            if can_cancel_order(user, order):
                _render_cancel_form(order, user, order_service, table_service)


def render():
    inject_css()
    _render_create_order()
    _render_order_list()
