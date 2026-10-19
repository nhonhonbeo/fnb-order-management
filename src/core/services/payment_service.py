"""Dịch vụ xử lý thanh toán."""
from __future__ import annotations

from pathlib import Path
from typing import Any, List, Optional

from src.core.storage import JsonStorage
from src.models.payment import Payment, PaymentStatus
from src.money import to_whole_vnd


class PaymentError(Exception):
    """Lỗi thanh toán khi quá trình thanh toán không hợp lệ."""


class PaymentService:
    def __init__(self, order_service: Any = None, storage_or_path: Optional[Any] = None):
        self._order_service = order_service

        if storage_or_path is None:
            default_path = Path(__file__).resolve().parents[3] / "data" / "payments.json"
            self.storage: Optional[JsonStorage] = JsonStorage(default_path)
        elif isinstance(storage_or_path, (str, Path)):
            self.storage = JsonStorage(storage_or_path)
        elif hasattr(storage_or_path, "load") and hasattr(storage_or_path, "save"):
            self.storage = storage_or_path
        else:
            self.storage = None

        self._payments: List[Payment] = []
        self._next_no = 1
        self.load()

    def load(self) -> None:
        if self.storage is None:
            return

        raw_payments = self.storage.load(default=[])
        self._payments = []
        for item in raw_payments:
            if isinstance(item, Payment):
                self._payments.append(item)
            elif isinstance(item, dict):
                self._payments.append(Payment.from_dict(item))

        max_no = 0
        for payment in self._payments:
            payment_id = getattr(payment, "payment_id", "")
            if payment_id.startswith("TT") and payment_id[2:].isdigit():
                max_no = max(max_no, int(payment_id[2:]))
        self._next_no = max(self._next_no, max_no + 1)

    def save(self) -> None:
        if self.storage is not None:
            serialized = []
            for payment in self._payments:
                if hasattr(payment, "to_dict"):
                    serialized.append(payment.to_dict())
                elif isinstance(payment, dict):
                    serialized.append(payment)
                else:
                    status = (
                        payment.status.value
                        if isinstance(payment.status, PaymentStatus)
                        else str(payment.status)
                    )
                    serialized.append({
                        "payment_id": payment.payment_id,
                        "order_id": payment.order_id,
                        "amount": payment.amount,
                        "status": status,
                    })
            self.storage.save(serialized)

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
        self._payments.append(payment)
        self._next_no += 1
        self.save()

        order.status = "PAID"
        if hasattr(self._order_service, "save"):
            self._order_service.save()

        return payment

    def list_payments(self) -> List[Payment]:
        return list(self._payments)