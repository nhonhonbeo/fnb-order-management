"""FIFO queue và yêu cầu chế biến trong bếp."""
from dataclasses import dataclass
from typing import Any, Callable, List, Optional

from src.core.data_structures.queue import Queue


class EmptyQueueError(Exception):
    pass


@dataclass
class KitchenRequest:
    order_id: str
    item_code: str
    item_name: str
    quantity: int
    status: str = "NEW"


class OrderQueue:
    def __init__(self):
        self._items = Queue()
        self._change_listener: Optional[Callable[[str, Any], None]] = None

    def set_change_listener(self, listener: Optional[Callable[[str, Any], None]]) -> None:
        self._change_listener = listener

    def _notify_change(self, action: str, value: Any) -> None:
        if self._change_listener is not None:
            self._change_listener(action, value)

    def enqueue(self, request: KitchenRequest) -> None:
        self._items.enqueue(request)
        self._notify_change("enqueue", request)

    def dequeue(self) -> KitchenRequest:
        if self.is_empty():
            raise EmptyQueueError("Hàng đợi trống")
        request = self._items.dequeue()
        self._notify_change("dequeue", request)
        return request

    def peek(self) -> KitchenRequest:
        if self.is_empty():
            raise EmptyQueueError("Hàng đợi trống")
        return self._items.peek()

    def is_empty(self) -> bool:
        return self._items.is_empty()

    def size(self) -> int:
        return self._items.size()

    def list_requests(self) -> List[KitchenRequest]:
        return list(self._items)

    def remove_by_order(self, order_id: str) -> None:
        new_items = Queue()
        for request in self._items:
            if request.order_id != order_id:
                new_items.enqueue(request)
        self._items = new_items
        self._notify_change("remove_by_order", order_id)