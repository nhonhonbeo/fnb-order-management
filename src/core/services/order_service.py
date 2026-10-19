"""Nghiệp vụ đơn hàng."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set

from src.core.repositories.order_repository import OrderRepository
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
        self.repository = OrderRepository(storage_or_path)

        # Lưu tất cả đơn hàng vào dictionary
        self.orders: Dict[str, Order] = {}
        self.next_no = 1
        self.load()

    def load(self) -> None:
        """Đọc danh sách đơn hàng từ storage vào bộ nhớ."""
        self.orders = {order.order_id: order for order in self.repository.load()}

        max_no = 0
        for oid in self.orders.keys():
            if str(oid).startswith("DH") and str(oid)[2:].isdigit():
                max_no = max(max_no, int(str(oid)[2:]))
        self.next_no = max(self.next_no, max_no + 1)

    def save(self) -> None:
        """Lưu toàn bộ danh sách đơn hàng ra storage."""
        self.repository.save(self.orders.values())

    def create_order(self, table_id: Any = None) -> Order:
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

    def search_orders(
        self,
        keyword: str | None = None,
        status: str | None = None,
    ) -> List[Order]:
        """Tìm đơn theo một phần mã đơn và/hoặc trạng thái."""
        orders = self.list_orders()
        if keyword is not None:
            normalized_keyword = keyword.casefold()
            orders = [
                order for order in orders
                if normalized_keyword in order.order_id.casefold()
            ]
        if status is not None:
            orders = [order for order in orders if order.status == status]
        return orders

    def list_history(self) -> List[Order]:
        """Liệt kê đơn đã thanh toán hoặc hủy, mới nhất trước."""
        history = [
            order for order in self.orders.values()
            if order.status in {"PAID", "CANCELLED"}
        ]

        def sort_key(order: Order) -> tuple[int, float]:
            if not isinstance(order.created_at, str) or not order.created_at:
                return 1, 0
            try:
                created_at = datetime.fromisoformat(order.created_at)
            except ValueError:
                return 1, 0
            if created_at.tzinfo is None:
                created_at = created_at.replace(tzinfo=timezone.utc)
            return 0, -created_at.timestamp()

        return sorted(history, key=sort_key)

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

        from src.core.queues.order_queue import KitchenRequest

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




