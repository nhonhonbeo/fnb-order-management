"""Persistence for payment records."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from src.shared.repository import JsonListRepository, RepositoryDataError
from src.storage.json_storage import JsonStorage
from src.payments.payment import Payment


class PaymentRepository(JsonListRepository[Payment]):
    entity_name = "Payment"
    identifier_fields = ("payment_id",)
    required_fields = ("payment_id", "order_id", "amount")

    def __init__(self, storage_or_path: Any = None):
        default_path = Path(__file__).resolve().parents[2] / "data" / "payments.json"
        storage = (
            JsonStorage(default_path)
            if storage_or_path is None
            else storage_or_path
            if isinstance(storage_or_path, JsonStorage)
            else JsonStorage(storage_or_path)
            if isinstance(storage_or_path, (str, Path))
            else None
        )
        if storage is None:
            raise TypeError("PaymentRepository requires a path or JSON storage object")
        super().__init__(storage)

    def deserialize(self, record: dict[str, Any]) -> Payment:
        try:
            return Payment.from_dict(record)
        except (TypeError, ValueError) as error:
            raise RepositoryDataError(
                f"Invalid payment in '{self.storage.file_path}': {error}"
            ) from error
