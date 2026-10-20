"""Business operations for dining-table availability and status."""
from __future__ import annotations

from typing import Dict, List

from src.tables.repository import TableRepository


class TableService:
    def __init__(self, repository: TableRepository | None = None):
        self.repository = (
            repository
            if isinstance(repository, TableRepository)
            else TableRepository(repository)
        )
        self._tables: Dict[str, str] = self.repository.list_all()

    def list_tables(self) -> Dict[str, str]:
        return dict(self._tables)

    def available_tables(self) -> List[str]:
        return [
            table_id
            for table_id, status in self._tables.items()
            if status == "Trống"
        ]

    def is_available(self, table_id: str) -> bool:
        return self._tables.get(table_id) == "Trống"

    def reserve(self, table_id: str) -> None:
        if table_id not in self._tables or not self.is_available(table_id):
            raise ValueError("Bàn không tồn tại hoặc đang được phục vụ")
        self._set_status(table_id, "Đang phục vụ")

    def release(self, table_id: str) -> None:
        if table_id not in self._tables:
            raise ValueError(f"Không tìm thấy bàn '{table_id}'")
        self._set_status(table_id, "Trống")

    def restore_status(self, table_id: str, status: str) -> None:
        if table_id not in self._tables:
            raise ValueError(f"Không tìm thấy bàn '{table_id}'")
        self._set_status(table_id, status)

    def _set_status(self, table_id: str, status: str) -> None:
        updated_tables = dict(self._tables)
        updated_tables[table_id] = status
        self.repository.save_all(updated_tables)
        self._tables = updated_tables
