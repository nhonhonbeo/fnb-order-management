"""FIFO queue và yêu cầu chế biến trong bếp kết hợp SPTF cho món ăn."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, List, Optional

from src.shared.data_structures.queue import Queue


class EmptyQueueError(Exception):
    pass


@dataclass
class KitchenRequest:
    order_id: str
    item_code: str
    item_name: str
    quantity: int
    processing_time: int = 5  # Thời gian hoàn thành (phút) phục vụ thuật toán SPTF
    created_at: str = ""      # Thời gian tạo hóa đơn (dùng cho quy tắc FIFO hóa đơn)
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
        request_key = (request.order_id, request.item_code)
        if any(
            (queued.order_id, queued.item_code) == request_key
            for queued in self.list_requests()
        ):
            raise ValueError(
                f"Món '{request.item_code}' của đơn '{request.order_id}' "
                "đã có trong hàng đợi"
            )
        self._items.enqueue(request)
        self._sort_queue()  # Tự động sắp xếp lại theo FIFO (hóa đơn) + SPTF (món) sau khi thêm
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
        """
        Trả về danh sách yêu cầu đã được sắp xếp theo chuẩn:
        1. FIFO đối với hóa đơn (created_at từ cũ đến mới).
        2. SPTF đối với món trong cùng hóa đơn (processing_time từ ngắn đến dài).
        """
        items_list = list(self._items)
        
        # Bước 1: Lấy danh sách các hóa đơn theo thời gian tạo (giữ chuẩn FIFO hóa đơn)
        order_creation_map = {}
        for req in items_list:
            if req.order_id not in order_creation_map:
                order_creation_map[req.order_id] = req.created_at or ""
                
        sorted_orders = sorted(order_creation_map.keys(), key=lambda oid: order_creation_map[oid])
        
        # Bước 2: Với từng hóa đơn, sắp xếp các món bên trong theo thời gian chế biến (SPTF)
        grouped_requests = {oid: [] for oid in sorted_orders}
        for req in items_list:
            if req.order_id in grouped_requests:
                grouped_requests[req.order_id].append(req)
                
        sorted_items = []
        for oid in sorted_orders:
            order_items = sorted(grouped_requests[oid], key=lambda r: r.processing_time)
            sorted_items.extend(order_items)
            
        return sorted_items

    def _sort_queue(self) -> None:
        """Sắp xếp lại cấu trúc Queue bên trong."""
        sorted_list = self.list_requests()
        self._items = Queue()
        for req in sorted_list:
            self._items.enqueue(req)

    def remove_by_order(self, order_id: str) -> None:
        new_items = Queue()
        for request in self._items:
            if request.order_id != order_id:
                new_items.enqueue(request)
        self._items = new_items
        self._notify_change("remove_by_order", order_id)

    def replace_all(self, requests: List[KitchenRequest]) -> None:
        keys = [(request.order_id, request.item_code) for request in requests]
        if len(keys) != len(set(keys)):
            raise ValueError("Hàng đợi không thể chứa yêu cầu trùng")
        
        self._items = Queue()
        for request in requests:
            self._items.enqueue(request)
        
        self._sort_queue()  # Sắp xếp lại ngay sau khi thay thế toàn bộ
        self._notify_change("replace_all", self.list_requests())