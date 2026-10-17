"""Mô hình bàn ăn."""
from __future__ import annotations

from typing import Any, Dict


class DiningTable:
    """Mô hình quản lý bàn ăn trong nhà hàng."""

    def __init__(
        self,
        table_id: str,
        seats: int = 4,
        status: str = "Trống",
    ):
        self.table_id = str(table_id)
        self.seats = int(seats)
        self.status = str(status)

    @property
    def name(self) -> str:
        return self.table_id

    def to_dict(self) -> Dict[str, Any]:
        return {
            "table_id": self.table_id,
            "name": self.table_id,
            "seats": self.seats,
            "status": self.status,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DiningTable":
        table_id = data.get("table_id") or data.get("name", "")
        return cls(
            table_id=table_id,
            seats=int(data.get("seats", 4)),
            status=str(data.get("status", "Trống")),
        )

    def __getitem__(self, key: str) -> Any:
        mapping = {
            "table_id": self.table_id,
            "name": self.table_id,
            "seats": self.seats,
            "status": self.status,
        }
        if key in mapping:
            return mapping[key]
        raise KeyError(key)

    def __setitem__(self, key: str, value: Any) -> None:
        if key in ("table_id", "name"):
            self.table_id = str(value)
        elif key == "seats":
            self.seats = int(value)
        elif key == "status":
            self.status = str(value)
        else:
            setattr(self, key, value)

    def get(self, key: str, default: Any = None) -> Any:
        try:
            return self[key]
        except KeyError:
            return default

    def __repr__(self) -> str:
        return f"DiningTable(id='{self.table_id}', seats={self.seats}, status='{self.status}')"
