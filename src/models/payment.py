"""Mô hình dữ liệu THANH TOÁN """
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict

from src.money import to_vnd

# Định nghĩa các trạng thái thanh toán
class PaymentStatus(Enum):
    PENDING = "PENDING"  # Đang chờ xử lý
    SUCCESS = "SUCCESS"  # Đã thanh toán thành công

# @dataclass(frozen=True) giúp tạo một dữ liệu bất biến.
# Ý nghĩa: Một khi hóa đơn đã được tạo thành công, không ai có thể sửa đổi hay gán đè lại giá trị bên trong nữa (giúp bảo mật tài chính).
@dataclass(frozen=True)
class Payment:
    payment_id: str         # Mã thanh toán
    order_id: str           # Mã đơn hàng tương ứng
    amount: int             # Tổng số tiền thanh toán theo đồng nguyên
    status: PaymentStatus   # Trạng thái thanh toán (PENDING hoặc SUCCESS)

    def __post_init__(self) -> None:
        object.__setattr__(self, "amount", to_vnd(self.amount))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "payment_id": self.payment_id,
            "order_id": self.order_id,
            "amount": self.amount,
            "status": self.status.value if isinstance(self.status, PaymentStatus) else str(self.status),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Payment:
        raw_status = data.get("status", PaymentStatus.SUCCESS)
        if isinstance(raw_status, str):
            try:
                status = PaymentStatus(raw_status)
            except ValueError:
                status = PaymentStatus.SUCCESS
        elif isinstance(raw_status, PaymentStatus):
            status = raw_status
        else:
            status = PaymentStatus.SUCCESS

        return cls(
            payment_id=str(data.get("payment_id", "")),
            order_id=str(data.get("order_id", "")),
            amount=data.get("amount", 0),
            status=status,
        )