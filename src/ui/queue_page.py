import streamlit as st

from ui.state import currency, get_current_user, new_id, order_total, save_tables_state, status_label
from ui.styles import inject_css
from src.core.payment_service import PaymentError


def _refresh_order_status(order_id):
    items = [item for item in st.session_state.kitchen_queue if item["order_id"] == order_id]
    order = next((o for o in st.session_state.orders if o["id"] == order_id), None)
    if not order:
        return
    if items and all(item["status"] == "READY" for item in items):
        order["status"] = "READY"
    elif any(item["status"] == "COOKING" for item in items):
        order["status"] = "COOKING"

    # Lưu lại trạng thái đơn hàng vào storage
    if hasattr(st.session_state.order_service, "save"):
        st.session_state.order_service.save()


def _render_kitchen_queue():
    queue = st.session_state.kitchen_queue
    active_queue = [item for item in queue if item["status"] != "DONE"]
    if not active_queue:
        st.info("Chưa có món nào chờ chế biến trong hàng đợi bếp.")
        return

    for index, item in enumerate(queue):
        if item["status"] == "DONE":
            continue
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
    selected = st.selectbox("Chọn đơn cần thanh toán", list(choices.keys()))
    order = choices[selected]

    st.dataframe(
        [
            {
                "Món": item["name"],
                "SL": item["quantity"],
                "Đơn giá": currency(item["price"]),
                "Thành tiền": currency(item["price"] * item["quantity"]),
            }
            for item in order["items"]
        ],
        hide_index=True,
        use_container_width=True,
    )

    total_amount = order_total(order)
    st.markdown(f"### Tổng thanh toán: {currency(total_amount)}")

    if st.button("💵 Xác nhận thanh toán & In hóa đơn", type="primary"):
        try:
            # 1. Gọi PaymentService xử lý giao dịch tài chính
            payment = st.session_state.payment_service.pay(order["id"], total_amount)

            # 2. Gọi BillingService xuất hóa đơn và lưu trữ
            invoice = st.session_state.billing_service.create_invoice(
                order=order,
                payment_id=payment.payment_id,
                invoice_id=new_id("HD"),
            )

            # 3. Mở lại bàn trống và lưu trạng thái bàn
            table_name = order["table"]
            st.session_state.tables[table_name] = "Trống"
            save_tables_state()

            # 4. Đánh dấu các món trong kitchen_queue là DONE
            for item in st.session_state.kitchen_queue:
                if item["order_id"] == order["id"]:
                    item["status"] = "DONE"

            # 5. Đồng bộ lại danh sách đơn hàng và hóa đơn
            st.session_state.orders = st.session_state.order_service.list_orders()
            st.session_state.invoices = st.session_state.billing_service.list_invoices()

            st.success(f"Đã thanh toán thành công {currency(total_amount)} (Mã GD: {payment.payment_id}, Hóa đơn: {invoice.id}) và mở lại {table_name}!")
            st.rerun()
        except PaymentError as err:
            st.error(f"Lỗi thanh toán: {str(err)}")
        except Exception as e:
            st.error(f"Lỗi: {str(e)}")


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
