import streamlit as st

from ui.state import currency, new_id, order_total, status_label
from ui.styles import inject_css


def _refresh_order_status(order_id):
    items = [item for item in st.session_state.kitchen_queue if item["order_id"] == order_id]
    order = next(order for order in st.session_state.orders if order["id"] == order_id)
    if items and all(item["status"] == "READY" for item in items):
        order["status"] = "READY"
    elif any(item["status"] == "COOKING" for item in items):
        order["status"] = "COOKING"


def render():
    inject_css()
    st.title("Bếp & thanh toán")
    kitchen_tab, payment_tab = st.tabs(["Hàng đợi bếp", "Thanh toán"])

    with kitchen_tab:
        queue = st.session_state.kitchen_queue
        if not queue:
            st.info("Chưa có món nào chờ chế biến.")
        for index, item in enumerate(queue):
            cols = st.columns([3, 2, 2])
            cols[0].write(f"**{item['name']} × {item['quantity']}**  \n{item['order_id']} · {item['table']}")
            cols[1].write(status_label(item["status"]))
            if item["status"] == "NEW" and cols[2].button("Bắt đầu nấu", key=f"cook_{index}"):
                item["status"] = "COOKING"
                _refresh_order_status(item["order_id"])
                st.rerun()
            elif item["status"] == "COOKING" and cols[2].button("Đánh dấu đã phục vụ", key=f"ready_{index}"):
                item["status"] = "READY"
                _refresh_order_status(item["order_id"])
                st.rerun()
            elif item["status"] == "READY":
                cols[2].success("Sẵn sàng phục vụ")

    with payment_tab:
        payable = [order for order in st.session_state.orders if order["status"] == "READY"]
        if not payable:
            st.info("Chỉ các đơn đã hoàn thành toàn bộ món mới có thể thanh toán.")
            return
        choices = {f"{order['id']} · {order['table']} · {currency(order_total(order))}": order for order in payable}
        selected = st.selectbox("Chọn đơn cần thanh toán", choices)
        order = choices[selected]
        st.dataframe(
            [{"Món": item["name"], "SL": item["quantity"], "Thành tiền": currency(item["price"] * item["quantity"])} for item in order["items"]],
            hide_index=True,
            use_container_width=True,
        )
        st.markdown(f"### Tổng thanh toán: {currency(order_total(order))}")
        if st.button("Xác nhận thanh toán", type="primary"):
            total = order_total(order)
            order["status"] = "PAID"
            st.session_state.tables[order["table"]] = "Trống"
            st.session_state.invoices.append({"id": new_id("HD"), "order_id": order["id"], "total": total})
            st.success(f"Đã thanh toán {currency(total)} và mở {order['table']}.")
