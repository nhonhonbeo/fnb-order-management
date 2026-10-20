"""Persistence and queries for orders."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from src.shared.repository import JsonListRepository
from src.storage.json_storage import JsonStorage
from src.orders.model import Order


class OrderRepository(JsonListRepository[Order]):
    entity_name = "Order"
    identifier_fields = ("order_id",)
    required_fields = ("order_id",)

    def __init__(self, storage_or_path: Any = None):
        default_path = Path(__file__).resolve().parents[2] / "data" / "orders.json"
        if storage_or_path is None:
            storage = JsonStorage(default_path)
        elif isinstance(storage_or_path, JsonStorage):
            storage = storage_or_path
        elif isinstance(storage_or_path, (str, Path)):
            storage = JsonStorage(storage_or_path)
        elif hasattr(storage_or_path, "load") and hasattr(storage_or_path, "save"):
            storage = storage_or_path
        else:
            raise TypeError("OrderRepository requires a path or JSON storage object")
        super().__init__(storage)

    def deserialize(self, record: dict[str, Any]) -> Order:
        for index, item in enumerate(record.get("items", [])):
            if not isinstance(item, dict):
                raise ValueError(
                    f"Order item {index} in '{self.storage.file_path}' must be an object"
                )
            missing = [
                field for field in ("item_code", "item_name", "quantity")
                if field not in item
            ]
            if "unit_price" not in item and "price" not in item:
                missing.append("unit_price")
            if missing:
                raise ValueError(
                    f"Order item {index} in '{self.storage.file_path}' is missing "
                    f"required field(s): {', '.join(missing)}"
                )
        return Order.from_dict(record)

    def load(self) -> list[Order]:
        return self.list_all()

    def save(self, orders) -> None:
        self.save_all(orders)
