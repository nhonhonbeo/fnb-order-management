import streamlit as st

from ui.state import currency, get_current_user, new_id, order_total, status_label
from ui.styles import inject_css


def _refresh_order_status(order_id):
    items = [item for item in st.session_state.kitchen_queue if item["order_id"] == order_id]
    order = next((order for order in st.session_state.orders if order["id"] == order_id), None)
    if not order:
        return
    if items and all(item["status"] == "READY" for item in items):
        order["status"] = "READY"
    elif any(item["status"] == "COOKING" for item in items):
        order["status"] = "COOKING"


def _render_kitchen_queue():
    queue = st.session_state.kitchen_queue
    if not queue:
        st.info("Chưa có món nào chờ chế biến trong hàng đợi.")
        return

    for index, item in enumerate(queue):
        cols = st.columns([3, 2, 2])
        cols[0].write(f"**{item['name']} × {item['quantity']}**  \n`{item['order_id']}` · **{item['table']}**")
        cols[1].write(status_label(item["status"]))
        if item["status"] == "NEW" and cols[2].button("🔥 Bắt đầu nấu", key=f"cook_{index}"):
            item["status"] = "COOKING"
            _refresh_order_status(item["order_id"])
            st.rerun()
        elif item["status"] == "COOKING" and cols[2].button("✅ Đã hoàn thành", key=f"ready_{index}"):
            item["status"] = "READY"
            _refresh_order_status(item["order_id"])
            st.rerun()
        elif item["status"] == "READY":
            cols[2].success("Sẵn sàng phục vụ")


def _render_payment():
    payable = [order for order in st.session_state.orders if order["status"] == "READY"]
    if not payable:
        st.info("Hiện không có đơn hàng nào chờ thanh toán (chỉ các đơn đã chế biến xong toàn bộ món mới có thể thanh toán).")
        return

    choices = {f"{order['id']} · {order['table']} · {currency(order_total(order))}": order for order in payable}
    selected = st.selectbox("Chọn đơn cần thanh toán", choices)
    order = choices[selected]
    st.dataframe(
        [
            {"Món": item["name"], "SL": item["quantity"], "Thành tiền": currency(item["price"] * item["quantity"])}
            for item in order["items"]
        ],
        hide_index=True,
        use_container_width=True,
    )
    st.markdown(f"### Tổng thanh toán: {currency(order_total(order))}")
    if st.button("💵 Xác nhận thanh toán & In hóa đơn", type="primary"):
        total = order_total(order)
        order["status"] = "PAID"
        st.session_state.tables[order["table"]] = "Trống"
        st.session_state.invoices.append({"id": new_id("HD"), "order_id": order["id"], "total": total})
        st.success(f"Đã thanh toán {currency(total)} và mở lại {order['table']}.")


def render():
    inject_css()
    current_user = get_current_user()
    role = current_user.role if current_user else "Nhân viên"

    if role == "Đầu bếp":
        st.title("🍳 Bếp chế biến")
        st.caption("Theo dõi hàng đợi món ăn theo thứ tự FIFO và cập nhật tiến độ nấu")
        _render_kitchen_queue()
    elif role == "Thu ngân":
        st.title("💵 Thu ngân & Thanh toán")
        st.caption("Xử lý hóa đơn bàn ăn và theo dõi tiến độ món")
        payment_tab, kitchen_tab = st.tabs(["Thanh toán hóa đơn", "Theo dõi bếp"])
        with payment_tab:
            _render_payment()
        with kitchen_tab:
            _render_kitchen_queue()
    else:
        st.title("Bếp & thanh toán")
        kitchen_tab, payment_tab = st.tabs(["Hàng đợi bếp", "Thanh toán"])
        with kitchen_tab:
            _render_kitchen_queue()
        with payment_tab:
            _render_payment()
