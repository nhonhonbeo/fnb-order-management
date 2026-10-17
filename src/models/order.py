"""Các lớp dùng để lưu thông tin đơn hàng."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from src.money import to_vnd


# Lớp lưu thông tin của một món ăn trong đơn hàng
class OrderItem:
    # Hàm khởi tạo, chạy khi tạo một đối tượng OrderItem
    def __init__(self, item_code: str, item_name: str, quantity: int, unit_price: int):
        self.item_code = str(item_code)
        self.item_name = str(item_name)
        self.quantity = int(quantity)
        self.unit_price = to_vnd(unit_price)

    # Hàm tính thành tiền của món ăn
    def subtotal(self) -> int:
        return self.quantity * self.unit_price

    def to_dict(self) -> Dict[str, Any]:
        return {
            "item_code": self.item_code,
            "item_name": self.item_name,
            "quantity": self.quantity,
            "unit_price": self.unit_price,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> OrderItem:
        return cls(
            item_code=data.get("item_code", ""),
            item_name=data.get("item_name", ""),
            quantity=data.get("quantity", 1),
            unit_price=data.get("unit_price", 0),
        )


# Lớp lưu thông tin của một đơn hàng
class Order:
    # Hàm khởi tạo đơn hàng
    def __init__(
        self,
        order_id: str,
        table_id: Optional[str] = None,
        status: str = "NEW",
        items: Optional[List[OrderItem]] = None,
    ):
        self.order_id = str(order_id)
        self.table_id = table_id
        self.status = status
        self.items: List[OrderItem] = items if items is not None else []

    # Hàm thêm một món ăn vào đơn hàng
    def add_line(self, item_code: str, item_name: str, quantity: int, unit_price: int):
        # Duyệt qua từng món đã có trong đơn hàng. Nếu món đã có thì cộng thêm số lượng
        for item in self.items:
            if item.item_code == item_code:
                item.quantity += quantity
                return

        # Nếu chưa có món này thì tạo đối tượng OrderItem mới
        self.items.append(
            OrderItem(item_code, item_name, quantity, unit_price)
        )

    # Hàm tính tổng tiền của toàn bộ đơn hàng
    def total(self) -> int:
        total_money = 0
        for item in self.items:
            total_money += item.subtotal()
        return total_money

    def to_dict(self) -> Dict[str, Any]:
        return {
            "order_id": self.order_id,
            "table_id": self.table_id,
            "status": self.status,
            "items": [item.to_dict() for item in self.items],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Order:
        items = []
        for it in data.get("items", []):
            if isinstance(it, OrderItem):
                items.append(it)
            elif isinstance(it, dict):
                items.append(OrderItem.from_dict(it))
        return cls(
            order_id=data.get("order_id", ""),
            table_id=data.get("table_id"),
            status=data.get("status", "NEW"),
            items=items,
        )
