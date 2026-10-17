"""Mô hình dữ liệu THANH TOÁN """
from dataclasses import dataclass
from enum import Enum

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
    amount: float           # Tổng số tiền thanh toán
    status: PaymentStatus   # Trạng thái thanh toán (PENDING hoặc SUCCESS)