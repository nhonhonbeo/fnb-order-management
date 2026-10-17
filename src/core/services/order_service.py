"""Nghiệp vụ đơn hàng."""
class OrderService:
    def __init__(self):
        self.orders = {}
    def create_order(self, order):
        self.orders[order.order_id] = order
        return order
"""Xử lý các thao tác cơ bản với đơn hàng."""

from src.models.order import Order

class OrderService:
    def __init__(self, menu=None, queue=None):
         # Lưu tất cả đơn hàng vào dictionary
        self.orders = {}
        self.next_no = 1
        self.menu = menu
        self.queue = queue

    def create_order(self, table_id=None):
        # Tạo mã đơn hàng
        order_id = "DH" + str(self.next_no).zfill(3)
        order = Order(order_id, table_id)
        self.orders[order_id] = order
        self.next_no += 1
        return order

    def get_order(self, order_id):
         # Kiểm tra mã đơn hàng có tồn tại hay không
        if order_id not in self.orders:
            raise ValueError("Không tìm thấy đơn hàng")
        return self.orders[order_id]

    def add_item(self, order_id, code, quantity):
         # Lấy đơn hàng cần thêm món
        order = self.get_order(order_id)

        if order.status != "NEW":
            raise ValueError("Không thể sửa đơn hàng này")

        if not isinstance(quantity, int) or isinstance(quantity, bool) or quantity <= 0:
            raise ValueError("Số lượng phải là số nguyên lớn hơn 0")

        if self.menu is None:
            raise ValueError("Chưa kết nối thực đơn")

        item = self.menu.get_item(code)
        if item is None:
            raise ValueError("Không tìm thấy món ăn")
        if not item.is_active:
            raise ValueError("Món ăn đã ngừng kinh doanh")

        # Lưu giá tại thời điểm khách gọi món
        order.add_line(item.code, item.name, quantity, item.price)
        return order

    def send_to_kitchen(self, order_id):
                # Lấy đơn hàng cần gửi xuống bếp
        order = self.get_order(order_id)

        # Chỉ gửi khi đơn đang NEW và đã có ít nhất một món
        if order.status != "NEW" or len(order.items) == 0:     
            raise ValueError("Đơn phải có món và đang ở trạng thái NEW")
       
        # Kiểm tra đã kết nối hàng đợi bếp chưa
        if self.queue is None:
            raise ValueError("Chưa kết nối hàng đợi bếp")

        # Tạo yêu cầu bếp theo cấu trúc KitchenRequest của nhóm
        from src.core.order_queue import KitchenRequest

                # Duyệt qua từng món trong đơn hàng
        for item in order.items:
            request = KitchenRequest(
                order_id=order.order_id,
                item_code=item.item_code,
                item_name=item.item_name,
                quantity=item.quantity
            )
            self.queue.enqueue(request)

        order.status = "IN_PROGRESS"
        return order

    def mark_completed(self, order_id):
                # Lấy đơn hàng cần cập nhật
        order = self.get_order(order_id)

         # Chỉ đơn đã gửi bếp mới được chuyển sang hoàn thành
        if order.status != "IN_PROGRESS":
            raise ValueError("Đơn chưa được gửi bếp")
        order.status = "COMPLETED"
        return order

    def cancel_order(self, order_id):
                # Lấy đơn hàng cần hủy
        order = self.get_order(order_id)
        if order.status == "PAID":
            raise ValueError("Không thể hủy đơn đã thanh toán")
        
        # Nếu có hàng đợi bếp thì xóa các yêu cầu của đơn này
        if self.queue is not None:
            self.queue.remove_by_order(order_id)

        order.status = "CANCELLED"
        return order

    def used_codes(self):
          # Tạo tập hợp rỗng để lưu các mã món đã được sử dụng
        # set tự động loại bỏ các mã trùng nhau
        codes = set()
        for order in self.orders.values():
            for item in order.items:
                codes.add(item.item_code)
                
                # Trả về tập hợp các mã món đã xuất hiện trong đơn hàng
        return codes




