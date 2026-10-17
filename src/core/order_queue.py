"""Queue FIFO khởi đầu; có thể tối ưu thêm khi học cấu trúc dữ liệu."""
from dataclasses import dataclass
from typing import List

from src.core.data_structures.queue import Queue

class EmptyQueueError(Exception):
    pass

@dataclass
class KitchenRequest:
    order_id: str      # Mã của đơn hàng chứa món này
    item_code: str     # Mã món ăn
    item_name: str     # Tên món ăn
    quantity: int      # Số lượng món cần nấu
    status: str = "NEW"

    #Kiểm tra với số 0
    def __pos_int__(self):
        if self.quantity <= 0:
            raise ValueError("Số lượng món ăn (quantity) phải lớn hơn 0.") 
class OrderQueue:
    def __init__(self):
        self._items = Queue()

    # Thêm yêu cầu chế biến vào cuối 
    def enqueue(self, request: KitchenRequest) -> None:
        self._items.enqueue(request)

    # Lấy món cần chế biến ở đầu hàng
    def dequeue(self) -> KitchenRequest:
        if self.is_empty():
            raise EmptyQueueError("Hàng đợi trống")
        return self._items.dequeue()

    # Xem phần tử đầu & Ko lấy ra
    def peek(self) -> KitchenRequest:
        if self.is_empty():
            raise EmptyQueueError("Hàng đợi trống")
        return self._items.peek()

    # Kiểm tra độ dài
    def is_empty(self) -> bool:
        return self._items.is_empty()

    # Trả về độ dài
    def size(self) -> int:
        return self._items.size()

    # Trả về một BẢN SAO dạng danh sách (list) 
    def list_requests(self) -> List[KitchenRequest]:
        return list(self._items)

    #Gỡ các yêu cầu chưa xử lý thuộc đơn hàng bị hủy mà vẫn giữ nguyên tuyệt đối thứ tự FIFO của các đơn hàng khác.
    def remove_by_order(self, order_id: str) -> None:
        new_items = Queue()
        for request in self._items:
            # Chỉ giữ lại những yêu cầu KHÔNG KHỚP với order_id bị hủy
            if request.order_id != order_id:
                new_items.enqueue(request)
        # Gán lại hàng đợi mới sau khi đã lọc bỏ đơn bị hủy
        self._items = new_items