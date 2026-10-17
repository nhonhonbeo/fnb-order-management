""" Dịch vụ xử lý thanh toán """
from __future__ import annotations

from pathlib import Path
from typing import Any, List, Optional

from src.core.storage import JsonStorage
from src.models.payment import Payment, PaymentStatus
from src.money import to_whole_vnd


class PaymentError(Exception):
    """Lỗi thanh toán khi quá trình thanh toán không hợp lệ."""
    pass


class PaymentService:
    def __init__(self, order_service: Any = None, storage_or_path: Optional[Any] = None):
        self._order_service = order_service  # Đối tượng OrderService truyền vào từ ngoài

        if storage_or_path is None:
            default_path = Path(__file__).resolve().parents[2] / "data" / "payments.json"
            self.storage: Optional[JsonStorage] = JsonStorage(default_path)
        elif isinstance(storage_or_path, (str, Path)):
            self.storage = JsonStorage(storage_or_path)
        elif hasattr(storage_or_path, "load") and hasattr(storage_or_path, "save"):
            self.storage = storage_or_path
        else:
            self.storage = None

        self._payments: List[Payment] = []  # Danh sách lưu trữ tất cả các hóa đơn đã thanh toán
        self._next_no = 1  # Biến đếm tự động tăng để sinh mã thanh toán (bắt đầu từ 1)
        self.load()

    def load(self) -> None:
        """Đọc danh sách thanh toán từ storage vào bộ nhớ."""
        if self.storage is None:
            return

        raw_payments = self.storage.load(default=[])
        self._payments = []
        for item in raw_payments:
            if isinstance(item, Payment):
                self._payments.append(item)
            elif isinstance(item, dict):
                self._payments.append(Payment.from_dict(item))

        # Cập nhật _next_no tự động theo mã lớn nhất đã có (ví dụ: TT001 -> _next_no = 2)
        max_no = 0
        for p in self._payments:
            pid = getattr(p, "payment_id", "")
            if pid.startswith("TT") and pid[2:].isdigit():
                max_no = max(max_no, int(pid[2:]))
        self._next_no = max(self._next_no, max_no + 1)

    def save(self) -> None:
        """Lưu toàn bộ danh sách thanh toán ra storage."""
        if self.storage is not None:
            serialized = []
            for p in self._payments:
                if hasattr(p, "to_dict"):
                    serialized.append(p.to_dict())
                elif isinstance(p, dict):
                    serialized.append(p)
                else:
                    status_val = p.status.value if isinstance(p.status, PaymentStatus) else str(p.status)
                    serialized.append({
                        "payment_id": p.payment_id,
                        "order_id": p.order_id,
                        "amount": p.amount,
                        "status": status_val,
                    })
            self.storage.save(serialized)

    # Hàm tính tổng tiền cần thu
    def calculate_amount(self, order) -> int:
        return order.total()

    # Hàm thực hiện thanh toán cho một đơn hàng
    def pay(self, order_id: str, amount: int) -> Payment:
        # 1. Tìm đơn hàng qua order_service
        try:
            order = self._order_service.get_order(order_id)
        except Exception:
            raise PaymentError("Không tìm thấy đơn hàng")

        # 2. Kiểm tra các điều kiện để xét đơn hàng không phù hợp
        if order.status == "PAID":
            raise PaymentError("Đơn đã thanh toán")
        
        if order.status == "CANCELLED":
            raise PaymentError("Đơn đã hủy")
        
        if not order.items:
            raise PaymentError("Đơn chưa có món")
        
        # Kiểm tra tiền khách đưa có bằng đúng tổng hóa đơn không
        ac_amount = self.calculate_amount(order)
        try:
            amount = to_whole_vnd(amount)
        except ValueError as error:
            raise PaymentError("Số tiền thanh toán không hợp lệ") from error

        if amount != ac_amount:
            raise PaymentError("Số tiền phải đúng bằng tổng hóa đơn")

        # 3. Tạo mã thanh toán tự động (định dạng TT001, TT002,...)
        payment_code = f"TT{self._next_no:03d}" #_next_no bắt đầu từ 1
        
        # Tạo bản ghi thanh toán thành công (Bất biến)
        payment = Payment(
            payment_id=payment_code,
            order_id=order_id,
            amount=amount,
            status=PaymentStatus.SUCCESS
        )

        # Lưu bản ghi và tăng biến đếm
        self._payments.append(payment)
        self._next_no += 1

        # Lưu vào storage
        self.save()

        # Chuyển trạng thái đơn hàng sang đã thanh toán (PAID)
        order.status = "PAID"
        if hasattr(self._order_service, "save"):
            self._order_service.save()

        return payment

    # Trả về bản sao danh sách thanh toán
    def list_payments(self) -> List[Payment]:
        return list(self._payments)

