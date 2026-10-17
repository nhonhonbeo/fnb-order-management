"""Giao diện thu ngân và xác nhận thanh toán."""
import streamlit as st

from src.core.payment_service import PaymentError
from ui.presenters import order_views
from ui.state import currency, new_id, order_total, save_tables_state


def render_payment() -> None:
    payable = [order for order in st.session_state.orders if order["status"] == "READY"]
    if not payable:
        st.info(
            "Hiện không có đơn hàng nào chờ thanh toán "
            "(chỉ các đơn đã chế biến xong toàn bộ món mới có thể thanh toán)."
        )
        return

    choices = {
        f"{order['id']} · {order['table']} · {currency(order_total(order))}": order
        for order in payable
    }
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
            payment = st.session_state.payment_service.pay(order["id"], total_amount)
            invoice = st.session_state.billing_service.create_invoice(
                order=order,
                payment_id=payment.payment_id,
                invoice_id=new_id("HD"),
            )

            table_name = order["table"]
            st.session_state.tables[table_name] = "Trống"
            save_tables_state()

            for request in st.session_state.kitchen_service.list_requests():
                if request.order_id == order["id"]:
                    st.session_state.kitchen_service.update_status(
                        request.order_id, request.item_code, "DONE"
                    )

            st.session_state.orders = order_views(st.session_state.order_service.list_orders())
            st.session_state.invoices = st.session_state.billing_service.list_invoices()

            st.success(
                f"Đã thanh toán thành công {currency(total_amount)} "
                f"(Mã GD: {payment.payment_id}, Hóa đơn: {invoice.id}) "
                f"và mở lại {table_name}!"
            )
            st.rerun()
        except PaymentError as error:
            st.error(f"Lỗi thanh toán: {error}")
        except Exception as error:
            st.error(f"Lỗi: {error}")