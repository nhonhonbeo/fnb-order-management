"""Giao diện thu ngân và xác nhận thanh toán."""
import streamlit as st

from src.payments.service import PaymentError
from src.ui.presenters import order_views
from src.ui.state import currency


def render_payment() -> None:
    payable = [order for order in st.session_state.orders if order["status"] == "READY"]
    if not payable:
        st.info(
            "Hiện không có đơn hàng nào chờ thanh toán "
            "(chỉ các đơn đã chế biến xong toàn bộ món mới có thể thanh toán)."
        )
        return

    choices = {
        f"{order['id']} · {order['table']} · "
        f"{currency(st.session_state.billing_service.calculate_total(order))}": order
        for order in payable
    }
    selected = st.selectbox(
        "Chọn đơn cần thanh toán",
        list(choices.keys()),
        key="payment_order",
    )
    order = choices[selected]

    st.dataframe(
        [
            {
                "Món": item["name"],
                "SL": item["quantity"],
                "Đơn giá": currency(item["price"]),
                "Thành tiền": currency(
                    st.session_state.billing_service.calculate_total([item])
                ),
            }
            for item in order["items"]
        ],
        hide_index=True,
        use_container_width=True,
    )

    total_amount = st.session_state.billing_service.calculate_total(order)
    st.markdown(f"### Tổng thanh toán: {currency(total_amount)}")

    if st.button(
        "💵 Xác nhận thanh toán & In hóa đơn",
        type="primary",
        key="confirm_payment",
    ):
        try:
            payment, invoice = st.session_state.payment_service.checkout(order["id"])
            st.session_state.tables = st.session_state.table_service.list_tables()
            st.session_state.orders = order_views(st.session_state.order_service.list_orders())
            st.session_state.invoices = st.session_state.billing_service.list_invoices()

            st.success(
                f"Đã thanh toán thành công {currency(total_amount)} "
                f"(Mã GD: {payment.payment_id}, Hóa đơn: {invoice.id}) "
                f"và mở lại {order['table']}!"
            )
            st.rerun()
        except PaymentError as error:
            st.error(f"Lỗi thanh toán: {error}")
        except Exception as error:
            st.error(f"Lỗi: {error}")