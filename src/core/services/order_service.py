"""Nghiệp vụ đơn hàng."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from src.core.storage import JsonStorage
from src.models.order import Order


class OrderService:
    def __init__(
        self,
        menu: Any = None,
        queue: Any = None,
        storage_or_path: Optional[Any] = None,
    ):
        self.menu = menu
        self.queue = queue

        if storage_or_path is None:
            default_path = Path(__file__).resolve().parents[3] / "data" / "orders.json"
            self.storage: Optional[JsonStorage] = JsonStorage(default_path)
        elif isinstance(storage_or_path, (str, Path)):
            self.storage = JsonStorage(storage_or_path)
        elif hasattr(storage_or_path, "load") and hasattr(storage_or_path, "save"):
            self.storage = storage_or_path
        else:
            self.storage = None

        # Lưu tất cả đơn hàng vào dictionary
        self.orders: Dict[str, Order] = {}
        self.next_no = 1
        self.load()

    def load(self) -> None:
        """Đọc danh sách đơn hàng từ storage vào bộ nhớ."""
        if self.storage is None:
            return

        raw_orders = self.storage.load(default=[])
        self.orders = {}
        for item in raw_orders:
            if isinstance(item, Order):
                self.orders[item.order_id] = item
            elif isinstance(item, dict):
                order = Order.from_dict(item)
                self.orders[order.order_id] = order

        max_no = 0
        for oid in self.orders.keys():
            if str(oid).startswith("DH") and str(oid)[2:].isdigit():
                max_no = max(max_no, int(str(oid)[2:]))
        self.next_no = max(self.next_no, max_no + 1)

    def save(self) -> None:
        """Lưu toàn bộ danh sách đơn hàng ra storage."""
        if self.storage is not None:
            serialized = [order.to_dict() for order in self.orders.values()]
            self.storage.save(serialized)

    def create_order(self, table_id: Any = None, order_id: Optional[str] = None) -> Order:
        if isinstance(table_id, Order):
            order = table_id
            self.orders[order.order_id] = order
            self.save()
            return order

        if order_id is None:
            order_id = "DH" + str(self.next_no).zfill(3)
            self.next_no += 1
        order = Order(order_id, table_id)
        self.orders[order_id] = order
        self.save()
        return order

    def get_order(self, order_id: str) -> Order:
        if order_id not in self.orders:
            raise ValueError("Không tìm thấy đơn hàng")
        return self.orders[order_id]

    def list_orders(self) -> List[Order]:
        return list(self.orders.values())

    def add_item(self, order_id: str, code: str, quantity: int) -> Order:
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

        order.add_line(item.code, item.name, quantity, item.price)
        self.save()
        return order

    def send_to_kitchen(self, order_id: str) -> Order:
        order = self.get_order(order_id)

        if order.status != "NEW" or len(order.items) == 0:
            raise ValueError("Đơn phải có món và đang ở trạng thái NEW")

        if self.queue is None:
            raise ValueError("Chưa kết nối hàng đợi bếp")

        from src.core.order_queue import KitchenRequest

        for item in order.items:
            request = KitchenRequest(
                order_id=order.order_id,
                item_code=item.item_code,
                item_name=item.item_name,
                quantity=item.quantity,
            )
            self.queue.enqueue(request)

        order.status = "IN_PROGRESS"
        self.save()
        return order

    def mark_completed(self, order_id: str) -> Order:
        order = self.get_order(order_id)

        if order.status != "IN_PROGRESS":
            raise ValueError("Đơn chưa được gửi bếp")
        order.status = "COMPLETED"
        self.save()
        return order

    def cancel_order(self, order_id: str) -> Order:
        order = self.get_order(order_id)
        if order.status == "PAID":
            raise ValueError("Không thể hủy đơn đã thanh toán")

        if self.queue is not None:
            self.queue.remove_by_order(order_id)

        order.status = "CANCELLED"
        self.save()
        return order

    def used_codes(self) -> Set[str]:
        codes = set()
        for order in self.orders.values():
            for item in order.items:
                codes.add(item.item_code)
        return codes




