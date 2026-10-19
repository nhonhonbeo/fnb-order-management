"""Nghiệp vụ điều phối hàng đợi bếp theo nguyên tắc FIFO."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from src.core.queues.order_queue import KitchenRequest, OrderQueue
from src.core.storage import JsonStorage


class KitchenService:
    """Điều phối và lưu tiến độ chế biến từng món."""

    def __init__(
        self,
        kitchen_queue: Optional[Any] = None,
        storage_or_path: Optional[Any] = None,
        order_service: Optional[Any] = None,
    ):
        self.kitchen_queue = kitchen_queue if kitchen_queue is not None else OrderQueue()
        if storage_or_path is None:
            default_path = Path(__file__).resolve().parents[3] / "data" / "kitchen.json"
            self.storage: Optional[JsonStorage] = JsonStorage(default_path)
        elif isinstance(storage_or_path, (str, Path)):
            self.storage = JsonStorage(storage_or_path)
        elif hasattr(storage_or_path, "load") and hasattr(storage_or_path, "save"):
            self.storage = storage_or_path
        else:
            self.storage = None

        self.order_service = order_service
        self._requests: Dict[Tuple[str, str], KitchenRequest] = {}
        self._loading = False

        if self.storage is not None and self.storage.exists():
            self.load()
        else:
            for request in self.list_requests():
                self._requests[self._request_key(request)] = request

        if hasattr(self.kitchen_queue, "set_change_listener"):
            self.kitchen_queue.set_change_listener(self._on_queue_change)
        if self.storage is not None and self._requests and not self.storage.exists():
            self.save()

    @staticmethod
    def _request_key(request: KitchenRequest) -> Tuple[str, str]:
        return request.order_id, request.item_code

    def _on_queue_change(self, action: str, value: Any) -> None:
        if self._loading:
            return
        if action in {"enqueue", "dequeue"}:
            self._requests[self._request_key(value)] = value
        elif action == "remove_by_order":
            self._requests = {
                key: request
                for key, request in self._requests.items()
                if request.order_id != value
            }
        self.save()

    def set_order_service(self, order_service: Any) -> None:
        self.order_service = order_service

    def save(self) -> None:
        """Lưu trạng thái món và thứ tự hàng đợi."""
        if self.storage is None:
            return
        self.storage.save({
            "requests": [
                {
                    "order_id": request.order_id,
                    "item_code": request.item_code,
                    "item_name": request.item_name,
                    "quantity": request.quantity,
                    "status": request.status,
                }
                for request in self._requests.values()
            ],
            "queue": [
                {"order_id": request.order_id, "item_code": request.item_code}
                for request in self.list_requests()
            ],
        })

    def load(self) -> None:
        """Nạp trạng thái món và thứ tự hàng đợi từ JSON."""
        if self.storage is None:
            return

        data = self.storage.load(default={})
        if isinstance(data, list):
            raw_requests = data
            raw_queue = None
        elif isinstance(data, dict):
            raw_requests = data.get("requests", [])
            raw_queue = data.get("queue")
        else:
            raw_requests = []
            raw_queue = None

        self._loading = True
        try:
            while not self.kitchen_queue.is_empty():
                self.kitchen_queue.dequeue()

            self._requests = {}
            for item in raw_requests:
                if not isinstance(item, dict):
                    continue
                request = KitchenRequest(
                    order_id=str(item.get("order_id", "")),
                    item_code=str(item.get("item_code", "")),
                    item_name=str(item.get("item_name", "")),
                    quantity=int(item.get("quantity", 0)),
                    status=str(item.get("status", "NEW")),
                )
                self._requests[self._request_key(request)] = request

            if not isinstance(raw_queue, list):
                raw_queue = [
                    {"order_id": request.order_id, "item_code": request.item_code}
                    for request in self._requests.values()
                    if request.status not in {"READY", "DONE"}
                ]

            for item in raw_queue:
                if not isinstance(item, dict):
                    continue
                key = (str(item.get("order_id", "")), str(item.get("item_code", "")))
                request = self._requests.get(key)
                if request is not None:
                    self.kitchen_queue.enqueue(request)
        finally:
            self._loading = False

    def send_to_kitchen(self, request_or_item: Any) -> None:
        """Đưa món ăn vào hàng đợi chờ bếp nấu."""
        if not hasattr(self.kitchen_queue, "enqueue"):
            return
        self.kitchen_queue.enqueue(request_or_item)
        if not hasattr(self.kitchen_queue, "set_change_listener"):
            self._requests[self._request_key(request_or_item)] = request_or_item
            self.save()

    def current(self) -> Optional[KitchenRequest]:
        """Trả về món ở đầu hàng đợi, hoặc None nếu hàng đợi trống."""
        if self.is_empty():
            return None
        return self.kitchen_queue.peek()

    def start(self, order_id: str, item_code: str) -> KitchenRequest:
        request = self.current()
        if request is None or (request.order_id, request.item_code) != (order_id, item_code):
            raise ValueError("Chỉ được bắt đầu món ở đầu hàng đợi bếp")
        if request.status != "NEW":
            raise ValueError("Món không ở trạng thái chờ nấu")

        request.status = "COOKING"
        self._requests[self._request_key(request)] = request
        self.save()
        return request

    def complete(self, order_id: str, item_code: str) -> KitchenRequest:
        request = self.current()
        if request is None or (request.order_id, request.item_code) != (order_id, item_code):
            raise ValueError("Chỉ được hoàn thành món ở đầu hàng đợi bếp")
        if request.status != "COOKING":
            raise ValueError("Món chưa được bắt đầu chế biến")

        request.status = "READY"
        self._requests[self._request_key(request)] = request
        self.kitchen_queue.dequeue()

        if self.order_service is not None:
            order = self.order_service.get_order(order_id)
            all_ready = bool(order.items) and all(
                (self._requests.get((order_id, item.item_code)) is not None)
                and self._requests[(order_id, item.item_code)].status == "READY"
                for item in order.items
            )
            if all_ready:
                self.order_service.mark_completed(order_id)

        self.save()
        return request

    def next_item(self) -> Any:
        """Lấy món tiếp theo theo thứ tự FIFO."""
        if hasattr(self.kitchen_queue, "dequeue"):
            return self.kitchen_queue.dequeue()
        return None

    def peek_next(self) -> Any:
        """Xem trước món tiếp theo mà không xóa khỏi hàng đợi."""
        if hasattr(self.kitchen_queue, "peek"):
            return self.kitchen_queue.peek()
        return None

    def list_requests(self) -> List[Any]:
        """Trả về toàn bộ danh sách món đang chờ trong hàng đợi."""
        if hasattr(self.kitchen_queue, "list_requests"):
            return self.kitchen_queue.list_requests()
        return []

    def remove_by_order(self, order_id: str) -> None:
        """Gỡ toàn bộ món của đơn hàng bị hủy ra khỏi hàng đợi."""
        if not hasattr(self.kitchen_queue, "remove_by_order"):
            return
        self.kitchen_queue.remove_by_order(order_id)
        if not hasattr(self.kitchen_queue, "set_change_listener"):
            self._requests = {
                key: request
                for key, request in self._requests.items()
                if request.order_id != order_id
            }
            self.save()

    def update_status(self, order_id: str, item_code: str, status: str) -> None:
        """Cập nhật tiến độ chế biến của một yêu cầu trong hàng đợi."""
        if status not in {"NEW", "COOKING", "READY", "DONE"}:
            raise ValueError(f"Trạng thái món không hợp lệ: {status}")
        if status == "COOKING":
            self.start(order_id, item_code)
            return
        if status == "READY":
            self.complete(order_id, item_code)
            return

        for request in self.list_requests():
            if request.order_id == order_id and request.item_code == item_code:
                if self.current() != request:
                    raise ValueError("Chỉ được cập nhật món ở đầu hàng đợi bếp")
                request.status = status
                self._requests[self._request_key(request)] = request
                self.save()
                return
        raise ValueError("Không tìm thấy món trong hàng đợi bếp")

    def is_empty(self) -> bool:
        """Kiểm tra hàng đợi có trống không."""
        if hasattr(self.kitchen_queue, "is_empty"):
            return self.kitchen_queue.is_empty()
        return True

    def size(self) -> int:
        """Trả về số món đang chờ chế biến."""
        if hasattr(self.kitchen_queue, "size"):
            return self.kitchen_queue.size()
        return 0