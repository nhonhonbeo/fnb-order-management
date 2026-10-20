"""Persistence for invoice records."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from src.shared.repository import JsonListRepository, RepositoryDataError
from src.storage.json_storage import JsonStorage
from src.payments.invoice import Invoice


class InvoiceRepository(JsonListRepository[Invoice]):
    entity_name = "Invoice"
    identifier_fields = ("invoice_id",)
    required_fields = ("order_id", "total")

    def __init__(self, storage_or_path: Any = None):
        default_path = Path(__file__).resolve().parents[2] / "data" / "invoices.json"
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
            raise TypeError("InvoiceRepository requires a path or JSON storage object")
        super().__init__(storage)

    def identifier(self, entity: Invoice) -> str:
        return str(entity.invoice_id)

    def validate_record(self, record: Any, index: int) -> dict[str, Any]:
        validated = super().validate_record(record, index)
        if not (validated.get("invoice_id") or validated.get("id")):
            raise RepositoryDataError(
                f"Invoice {index} in '{self.storage.file_path}' is missing "
                "required field(s): invoice_id or id"
            )
        return validated

    def deserialize(self, record: dict[str, Any]) -> Invoice:
        try:
            return Invoice.from_dict(record)
        except (TypeError, ValueError) as error:
            raise RepositoryDataError(
                f"Invalid invoice in '{self.storage.file_path}': {error}"
            ) from error
