"""Persistence cho các đơn hàng."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable, List, Optional

from src.core.storage import JsonStorage
from src.models.order import Order


class OrderRepository:
    """Đọc và ghi đơn hàng qua storage JSON."""

    def __init__(self, storage_or_path: Optional[Any] = None):
        if storage_or_path is None:
            default_path = Path(__file__).resolve().parents[3] / "data" / "orders.json"
            self.storage: Optional[JsonStorage] = JsonStorage(default_path)
        elif isinstance(storage_or_path, (str, Path)):
            self.storage = JsonStorage(storage_or_path)
        elif hasattr(storage_or_path, "load") and hasattr(storage_or_path, "save"):
            self.storage = storage_or_path
        else:
            self.storage = None

    def load(self) -> List[Order]:
        if self.storage is None:
            return []

        raw_orders = self.storage.load(default=[])
        orders = []
        for item in raw_orders:
            if isinstance(item, Order):
                orders.append(item)
            elif isinstance(item, dict):
                orders.append(Order.from_dict(item))
        return orders

    def save(self, orders: Iterable[Order]) -> None:
        if self.storage is not None:
            self.storage.save([order.to_dict() for order in orders])