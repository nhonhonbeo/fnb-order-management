"""Persistence and queries for orders."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from src.shared.repository import JsonListRepository, RepositoryDataError
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
        if not isinstance(record["order_id"], str):
            raise RepositoryDataError(
                f"Order data in '{self.storage.file_path}' requires a string order_id"
            )
        if "status" in record and not isinstance(record["status"], str):
            raise RepositoryDataError(
                f"Order data in '{self.storage.file_path}' requires a string status"
            )
        if record.get("table_id") is not None and not isinstance(record["table_id"], str):
            raise RepositoryDataError(
                f"Order data in '{self.storage.file_path}' requires a string table_id"
            )
        raw_items = record.get("items", [])
        if not isinstance(raw_items, list):
            raise RepositoryDataError(
                f"Order items in '{self.storage.file_path}' must be a JSON array"
            )
        for index, item in enumerate(raw_items):
            if not isinstance(item, dict):
                raise RepositoryDataError(
                    f"Order item {index} in '{self.storage.file_path}' must be an object"
                )
            missing = [
                field for field in ("item_code", "item_name", "quantity")
                if field not in item
            ]
            if "unit_price" not in item and "price" not in item:
                missing.append("unit_price")
            if missing:
                raise RepositoryDataError(
                    f"Order item {index} in '{self.storage.file_path}' is missing "
                    f"required field(s): {', '.join(missing)}"
                )
            if (
                not isinstance(item["item_code"], str)
                or not isinstance(item["item_name"], str)
                or not item["item_code"]
                or not item["item_name"]
            ):
                raise RepositoryDataError(
                    f"Order item {index} in '{self.storage.file_path}' requires "
                    "string item_code and item_name fields"
                )
            quantity = item["quantity"]
            if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity <= 0:
                raise RepositoryDataError(
                    f"Order item {index} in '{self.storage.file_path}' requires "
                    "a positive integer quantity"
                )
            unit_price = item.get("unit_price", item.get("price"))
            if isinstance(unit_price, bool) or not isinstance(unit_price, (int, float)):
                raise RepositoryDataError(
                    f"Order item {index} in '{self.storage.file_path}' requires "
                    "a numeric unit_price"
                )
        try:
            return Order.from_dict(record)
        except (TypeError, ValueError) as error:
            raise RepositoryDataError(
                f"Invalid order in '{self.storage.file_path}': {error}"
            ) from error

    def load(self) -> list[Order]:
        return self.list_all()

    def save(self, orders) -> None:
        self.save_all(orders)
