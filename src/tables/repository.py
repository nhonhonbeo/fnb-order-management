"""Persistence and status queries for dining tables."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from src.shared.repository import RepositoryDataError
from src.storage.json_storage import JsonStorage, StorageManager


class TableRepository:
    """Read and update tables while preserving the legacy JSON mapping format."""

    def __init__(self, storage_or_path: Any = None):
        default_path = Path(__file__).resolve().parents[2] / "data" / "tables.json"
        if storage_or_path is None:
            self.storage = JsonStorage(default_path)
        elif isinstance(storage_or_path, JsonStorage):
            self.storage = storage_or_path
        elif isinstance(storage_or_path, (str, Path)):
            self.storage = JsonStorage(storage_or_path)
        else:
            raise TypeError("TableRepository requires a path or JSON storage object")

    def list_all(self) -> dict[str, str]:
        if not self.storage.exists():
            tables = dict(StorageManager.DEFAULT_TABLES)
            self.save_all(tables)
            return tables
        raw_tables = self.storage.load()
        if not isinstance(raw_tables, dict):
            raise RepositoryDataError(
                f"Table data in '{self.storage.file_path}' must be a JSON object"
            )
        for table_id, status in raw_tables.items():
            if not isinstance(table_id, str) or not table_id:
                raise RepositoryDataError(
                    f"Invalid table identifier in '{self.storage.file_path}'"
                )
            if not isinstance(status, str) or not status:
                raise RepositoryDataError(
                    f"Invalid status for table '{table_id}' in '{self.storage.file_path}'"
                )
        return dict(raw_tables)

    def save_all(self, tables: dict[str, str]) -> None:
        self.storage.save(tables)

    def find_by_id(self, table_id: str) -> str | None:
        return self.list_all().get(table_id)

    def add(self, table_id: str, status: str = "Trống") -> None:
        tables = self.list_all()
        if table_id in tables:
            raise RepositoryDataError(f"Table '{table_id}' already exists")
        tables[table_id] = status
        self.save_all(tables)

    def update(self, table_id: str, status: str) -> None:
        tables = self.list_all()
        if table_id not in tables:
            raise RepositoryDataError(f"Table '{table_id}' was not found")
        tables[table_id] = status
        self.save_all(tables)

    def delete(self, table_id: str) -> bool:
        tables = self.list_all()
        if table_id not in tables:
            return False
        del tables[table_id]
        self.save_all(tables)
        return True

    def search(self, keyword: str) -> dict[str, str]:
        normalized = keyword.casefold()
        return {
            table_id: status for table_id, status in self.list_all().items()
            if normalized in table_id.casefold()
        }
