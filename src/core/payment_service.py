""" Dịch vụ xử lý thanh toán """
from typing import List
from src.models.payment import Payment, PaymentStatus

class PaymentError(Exception):
    """Lỗi thanh toán khi quá trình thanh toán không hợp lệ."""
    pass

class PaymentService:
    def __init__(self, order_service):
        self._payments: List[Payment] = []  # Danh sách lưu trữ tất cả các hóa đơn đã thanh toán
        self._order_service = order_service  # Đối tượng OrderService truyền vào từ ngoài
        self._next_no = 1  # Biến đếm tự động tăng để sinh mã thanh toán (bắt đầu từ 1)

    # Hàm tính tổng tiền cần thu
    def calculate_amount(self, order) -> float:
        return order.total()

    # Hàm thực hiện thanh toán cho một đơn hàng
    def pay(self, order_id: str, amount: float) -> Payment:
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
        if amount != ac_amount:
            raise PaymentError("Số tiền phải đúng bằng tổng hóa đơn")

        # 3. Tạo mã thanh toán tự động (định dạng TT001, TT002,...)
        payment_code = f"TT{self._next_no:03d}" #_next_no bắt đầu từ 1
        
        # Tạo bản ghi thanh toán thành công (Bất biến)
        payment = Payment(
            payment_id = payment_code,
            order_id = order_id,
            amount = amount,
            status = PaymentStatus.SUCCESS
        )

        # Lưu bản ghi và tăng biến đếm
        self._payments.append(payment)
        self._next_no += 1

        # Chuyển trạng thái đơn hàng sang đã thanh toán (PAID)
        order.status = "PAID"

        return payment

    # Trả về bản sao danh sách thanh toán
    def list_payments(self) -> List[Payment]:
        return list(self._payments)

