"""Business operations for dining-table availability and status."""
from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from threading import RLock
from typing import Any, Callable, Dict, Iterable, List

from src.tables.repository import TableRepository


_LOCKS_GUARD = RLock()
_TABLE_LOCKS: dict[str, RLock] = {}


class TableService:
    def __init__(self, repository: TableRepository | None = None):
        self.repository = (
            repository
            if isinstance(repository, TableRepository)
            else TableRepository(repository)
        )
        self._orders_provider: Callable[[], Iterable[Any]] = lambda: ()
        self._tables: Dict[str, str] = self.repository.list_all()

    @contextmanager
    def transaction(self) -> Iterator[None]:
        """Serialize table changes sharing one storage file and refresh its state."""
        storage = self.repository.storage
        storage_path = getattr(storage, "file_path", None)
        lock_key = (
            str(storage_path.resolve())
            if storage_path is not None
            else str(id(storage))
        )
        with _LOCKS_GUARD:
            lock = _TABLE_LOCKS.setdefault(lock_key, RLock())
        with lock:
            self._tables = self.repository.list_all()
            yield

    def set_orders_provider(
        self,
        orders_provider: Callable[[], Iterable[Any]],
    ) -> None:
        if not callable(orders_provider):
            raise TypeError("Orders provider must be callable")
        self._orders_provider = orders_provider

    def add_table(self, name: str) -> None:
        if not isinstance(name, str) or not name.strip():
            raise ValueError("Tên bàn không được để trống")

        table_name = name.strip()
        with self.transaction():
            if any(
                existing_name.strip().casefold() == table_name.casefold()
                for existing_name in self._tables
            ):
                raise ValueError(f"Bàn '{table_name}' đã tồn tại")

            self.repository.add(table_name)
            self._tables = self.repository.list_all()

    def delete_table(self, table_id: str) -> None:
        with self.transaction():
            if table_id not in self._tables:
                raise ValueError(f"Không tìm thấy bàn '{table_id}'")
            if self._tables[table_id] != "Trống":
                raise ValueError("Chỉ có thể xoá bàn đang Trống")
            if self._has_active_order(table_id):
                raise ValueError("Không thể xoá bàn đang có đơn chưa thanh toán")
            if not self.repository.delete(table_id):
                raise ValueError(f"Không tìm thấy bàn '{table_id}'")
            self._tables = self.repository.list_all()

    def _has_active_order(self, table_id: str) -> bool:
        for order in self._orders_provider():
            if isinstance(order, dict):
                order_table = order.get("table_id", order.get("table"))
                status = order.get("status")
            else:
                order_table = getattr(order, "table_id", getattr(order, "table", None))
                status = getattr(order, "status", None)
            if order_table == table_id and status not in {"PAID", "CANCELLED"}:
                return True
        return False

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
        with self.transaction():
            if table_id not in self._tables or not self.is_available(table_id):
                raise ValueError("Bàn không tồn tại hoặc đang được phục vụ")
            self._set_status(table_id, "Đang phục vụ")

    def release(self, table_id: str) -> None:
        with self.transaction():
            if table_id not in self._tables:
                raise ValueError(f"Không tìm thấy bàn '{table_id}'")
            self._set_status(table_id, "Trống")

    def restore_status(self, table_id: str, status: str) -> None:
        with self.transaction():
            if table_id not in self._tables:
                raise ValueError(f"Không tìm thấy bàn '{table_id}'")
            self._set_status(table_id, status)

    def move_reservation(self, old_table_id: str | None, new_table_id: str) -> None:
        with self.transaction():
            if new_table_id not in self._tables or (
                new_table_id != old_table_id and not self.is_available(new_table_id)
            ):
                raise ValueError("Bàn mới không tồn tại hoặc đang được phục vụ")
            if old_table_id == new_table_id:
                return
            if old_table_id is not None and old_table_id not in self._tables:
                raise ValueError(f"Không tìm thấy bàn '{old_table_id}'")

            updated_tables = dict(self._tables)
            if old_table_id is not None:
                updated_tables[old_table_id] = "Trống"
            updated_tables[new_table_id] = "Đang phục vụ"
            self.repository.save_all(updated_tables)
            self._tables = updated_tables

    def restore_statuses(self, statuses: Dict[str, str]) -> None:
        with self.transaction():
            updated_tables = dict(self._tables)
            for table_id, status in statuses.items():
                if table_id not in updated_tables:
                    raise ValueError(f"Không tìm thấy bàn '{table_id}'")
                updated_tables[table_id] = status
            self.repository.save_all(updated_tables)
            self._tables = updated_tables

    def _set_status(self, table_id: str, status: str) -> None:
        updated_tables = dict(self._tables)
        updated_tables[table_id] = status
        self.repository.save_all(updated_tables)
        self._tables = updated_tables
