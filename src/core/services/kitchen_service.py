"""Nghiệp vụ điều phối hàng đợi bếp (Kitchen Service).

Quản lý luồng chế biến món ăn theo nguyên tắc FIFO (vào trước ra trước).
"""
from __future__ import annotations

from typing import Any, List, Optional

from src.core.order_queue import KitchenRequest, OrderQueue


class KitchenService:
    """Điều phối và theo dõi các yêu cầu chế biến trong bếp ăn."""

    def __init__(self, kitchen_queue: Optional[Any] = None):
        self.kitchen_queue = kitchen_queue if kitchen_queue is not None else OrderQueue()

    def send_to_kitchen(self, request_or_item: Any) -> None:
        """Đưa món ăn vào hàng đợi chờ bếp nấu."""
        if hasattr(self.kitchen_queue, "enqueue"):
            self.kitchen_queue.enqueue(request_or_item)

    def next_item(self) -> Any:
        """Lấy món tiếp theo theo thứ tự FIFO để đầu bếp nấu."""
        if hasattr(self.kitchen_queue, "dequeue"):
            return self.kitchen_queue.dequeue()
        return None

    def peek_next(self) -> Any:
        """Xem trước món tiếp theo mà không lấy ra khỏi hàng đợi."""
        if hasattr(self.kitchen_queue, "peek"):
            return self.kitchen_queue.peek()
        return None

    def list_requests(self) -> List[Any]:
        """Trả về toàn bộ danh sách món đang chờ trong hàng đợi."""
        if hasattr(self.kitchen_queue, "list_requests"):
            return self.kitchen_queue.list_requests()
        return []

    def remove_by_order(self, order_id: str) -> None:
        """Gỡ toàn bộ các món của đơn hàng bị hủy ra khỏi hàng đợi."""
        if hasattr(self.kitchen_queue, "remove_by_order"):
            self.kitchen_queue.remove_by_order(order_id)

    def update_status(self, order_id: str, item_code: str, status: str) -> None:
        """Cập nhật tiến độ chế biến của một yêu cầu trong hàng đợi."""
        if status not in {"NEW", "COOKING", "READY", "DONE"}:
            raise ValueError(f"Trạng thái món không hợp lệ: {status}")

        for request in self.list_requests():
            if request.order_id == order_id and request.item_code == item_code:
                request.status = status
                return

        raise ValueError("Không tìm thấy món trong hàng đợi bếp")

    def is_empty(self) -> bool:
        """Kiểm tra bếp có đang rảnh (hàng đợi trống) hay không."""
        if hasattr(self.kitchen_queue, "is_empty"):
            return self.kitchen_queue.is_empty()
        return True

    def size(self) -> int:
        """Số lượng món hiện đang chờ trong bếp."""
        if hasattr(self.kitchen_queue, "size"):
            return self.kitchen_queue.size()
        return 0
