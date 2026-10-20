"""Dịch vụ xử lý thanh toán."""
from __future__ import annotations

from typing import Any, List, Optional
from uuid import uuid4

from src.payments.payment_repository import PaymentRepository
from src.payments.payment import Payment, PaymentStatus
from src.shared.money import to_whole_vnd


class PaymentError(ValueError):
    """Lỗi thanh toán khi quá trình thanh toán không hợp lệ."""


class PaymentService:
    def __init__(
        self,
        order_service: Any = None,
        storage_or_path: Optional[Any] = None,
        billing_service: Any = None,
        table_service: Any = None,
        kitchen_service: Any = None,
    ):
        self._order_service = order_service
        self._billing_service = billing_service
        self._table_service = table_service
        self._kitchen_service = kitchen_service

        self.repository = (
            storage_or_path
            if isinstance(storage_or_path, PaymentRepository)
            else PaymentRepository(storage_or_path)
        )

        self._payments: List[Payment] = []
        self._next_no = 1
        self.load()

    def load(self) -> None:
        self._payments = self.repository.list_all()

        max_no = 0
        for payment in self._payments:
            payment_id = getattr(payment, "payment_id", "")
            if payment_id.startswith("TT") and payment_id[2:].isdigit():
                max_no = max(max_no, int(payment_id[2:]))
        self._next_no = max(self._next_no, max_no + 1)

    def save(self) -> None:
        self.repository.save_all(self._payments)

    def calculate_amount(self, order) -> int:
        return order.total()

    def pay(self, order_id: str, amount: int) -> Payment:
        try:
            order = self._order_service.get_order(order_id)
        except Exception as error:
            raise PaymentError("Không tìm thấy đơn hàng") from error

        if order.status == "PAID":
            raise PaymentError("Đơn đã thanh toán")
        if order.status == "CANCELLED":
            raise PaymentError("Đơn đã hủy")
        if not order.items:
            raise PaymentError("Đơn chưa có món")
        if order.status != "COMPLETED":
            raise PaymentError("Đơn chưa chế biến xong, không thể thanh toán")

        actual_amount = self.calculate_amount(order)
        try:
            amount = to_whole_vnd(amount)
        except ValueError as error:
            raise PaymentError("Số tiền thanh toán không hợp lệ") from error

        if amount != actual_amount:
            raise PaymentError("Số tiền phải đúng bằng tổng hóa đơn")

        payment = Payment(
            payment_id=f"TT{self._next_no:03d}",
            order_id=order_id,
            amount=amount,
            status=PaymentStatus.SUCCESS,
        )
        self.repository.add(payment)
        self._payments.append(payment)
        self._next_no += 1

        order.status = "PAID"
        if hasattr(self._order_service, "save"):
            self._order_service.save()

        return payment

    def checkout(self, order_id: str) -> tuple[Payment, Any]:
        """Complete payment and coordinate its invoice, table, and kitchen updates."""
        if any(
            service is None
            for service in (
                self._billing_service,
                self._table_service,
                self._kitchen_service,
            )
        ):
            raise PaymentError("Chưa cấu hình đầy đủ dịch vụ thanh toán")

        order = self._order_service.get_order(order_id)
        payment = self.pay(order_id, self.calculate_amount(order))
        invoice = self._billing_service.create_invoice(
            order=order,
            payment_id=payment.payment_id,
            invoice_id=f"HD-{uuid4().hex[:6].upper()}",
        )
        self._table_service.release(order.table_id)
        self._kitchen_service.mark_order_done(order_id)
        return payment, invoice

    def list_payments(self) -> List[Payment]:
        return list(self._payments)