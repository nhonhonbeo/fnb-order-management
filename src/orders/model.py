"""Các lớp dùng để lưu thông tin đơn hàng."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from src.shared.money import to_whole_vnd


# Lớp lưu thông tin của một món ăn trong đơn hàng
class OrderItem:
    # Hàm khởi tạo, chạy khi tạo một đối tượng OrderItem
    def __init__(
        self, 
        item_code: str, 
        item_name: str, 
        quantity: int, 
        unit_price: int,
        processing_time: int = 5,
        status: str = "PENDING"  # Trạng thái: PENDING (chờ), COOKING (đang nấu), DONE (xong), CANCELLED (hủy)
    ):
        if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity <= 0:
            raise ValueError("Số lượng phải là số nguyên lớn hơn 0")
        normalized_price = to_whole_vnd(unit_price)
        if normalized_price <= 0:
            raise ValueError("Đơn giá phải là số nguyên lớn hơn 0")
        if processing_time < 0:
            raise ValueError("Thời gian hoàn thành không được âm")

        self.item_code = str(item_code)
        self.item_name = str(item_name)
        self.quantity = quantity
        self.unit_price = normalized_price
        self.processing_time = int(processing_time)
        self.status = str(status)

    def can_modify_or_cancel(self) -> bool:
        """Chỉ cho phép đổi hoặc hủy món khi bếp chưa xác nhận nấu (vẫn ở trạng thái PENDING hoặc NEW)."""
        return self.status in ("PENDING", "NEW")

    def update_item_info(self, new_quantity: int, new_unit_price: int, new_processing_time: int, new_item_name: Optional[str] = None):
        """Cho phép đổi món/số lượng/thời gian nếu bếp chưa bắt đầu nấu."""
        if not self.can_modify_or_cancel():
            raise ValueError("Không thể đổi món vì bếp đã xác nhận nấu hoặc hoàn thành!")
        
        if isinstance(new_quantity, bool) or not isinstance(new_quantity, int) or new_quantity <= 0:
            raise ValueError("Số lượng phải là số nguyên lớn hơn 0")
        normalized_price = to_whole_vnd(new_unit_price)
        if normalized_price <= 0:
            raise ValueError("Đơn giá phải là số nguyên lớn hơn 0")
        if new_processing_time < 0:
            raise ValueError("Thời gian hoàn thành không được âm")

        self.quantity = new_quantity
        self.unit_price = normalized_price
        self.processing_time = int(new_processing_time)
        if new_item_name:
            self.item_name = str(new_item_name)

    # Hàm tính thành tiền của món ăn
    def subtotal(self) -> int:
        return self.quantity * self.unit_price

    def to_dict(self) -> Dict[str, Any]:
        return {
            "item_code": self.item_code,
            "item_name": self.item_name,
            "quantity": self.quantity,
            "unit_price": self.unit_price,
            "processing_time": self.processing_time,
            "status": self.status,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> OrderItem:
        return cls(
            item_code=data.get("item_code", ""),
            item_name=data.get("item_name", ""),
            quantity=data.get("quantity", 1),
            unit_price=data.get("unit_price", 0),
            processing_time=data.get("processing_time", 5),
            status=data.get("status", "PENDING"),
        )


# Lớp lưu thông tin của một đơn hàng (Hóa đơn)
class Order:
    # Hàm khởi tạo đơn hàng
    def __init__(
        self,
        order_id: str,
        table_id: Optional[str] = None,
        status: str = "NEW",
        items: Optional[List[OrderItem]] = None,
        created_at: Optional[str] = None,
        note: str = "",
        cancelled_at: Optional[str] = None,
        cancel_reason: Optional[str] = None,
    ):
        self.order_id = str(order_id)
        self.table_id = table_id
        self.status = status
        self.items: List[OrderItem] = items if items is not None else []
        self.created_at: Optional[str] = (
            created_at if created_at is not None else datetime.now().isoformat()
        )
        self.note = note
        self.cancelled_at = cancelled_at
        self.cancel_reason = cancel_reason

    # Hàm thêm một món ăn vào đơn hàng
    def add_line(self, item_code: str, item_name: str, quantity: int, unit_price: int, processing_time: int = 5):
        # Duyệt qua từng món đã có trong đơn hàng. Nếu món đã có thì cộng thêm số lượng
        for item in self.items:
            if item.item_code == item_code:
                # Nếu món đã tồn tại nhưng chưa nấu, có thể cộng dồn số lượng
                if item.can_modify_or_cancel():
                    item.quantity += quantity
                    return
                else:
                    # Nếu món cũ đã nấu rồi mà gọi thêm, tạo dòng mới hoặc xử lý tùy nghiệp vụ
                    break

        # Nếu chưa có món này thì tạo đối tượng OrderItem mới kèm thời gian chế biến
        self.items.append(
            OrderItem(item_code, item_name, quantity, unit_price, processing_time)
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
            "created_at": self.created_at,
            "note": self.note,
            "cancelled_at": self.cancelled_at,
            "cancel_reason": self.cancel_reason,
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
        order = cls(
            order_id=data.get("order_id", ""),
            table_id=data.get("table_id"),
            status=data.get("status", "NEW"),
            items=items,
            created_at=data.get("created_at"),
            note=data.get("note", ""),
            cancelled_at=data.get("cancelled_at"),
            cancel_reason=data.get("cancel_reason"),
        )
        if data.get("created_at") is None:
            order.created_at = None
        return order