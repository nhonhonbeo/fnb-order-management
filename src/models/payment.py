from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum

#Trạng thái thanh toán, đang xử lý hoặc thành công(chưa có thất bại)
class PaymentStatus(Enum):

    PENDING = "PENDING"
    SUCCESS = "SUCCESS"


@dataclass(frozen=True)
class Payment:
    """
        payment_id: Mã thanh toán duy nhất, do PaymentService sinh.
        order_id:   Mã đơn hàng được thanh toán.
        amount:     Số tiền đã thu, kiểu Decimal.
        status:     Trạng thái thanh toán, mặc định là PENDING.
    """

    payment_id: str
    order_id: str
    amount: Decimal
    status: PaymentStatus = PaymentStatus.PENDING

    def is_successful(self) -> bool:
        #Trả về True nếu bản ghi này đã thanh toán thành công
        return self.status is PaymentStatus.SUCCESS

    def __str__(self) -> str:
        #Biểu diễn chuỗi dễ đọc, dùng khi print hoặc string
        return (
            f"Payment({self.payment_id} | đơn {self.order_id} | "
            f"{self.amount} | {self.status.value})"
        )