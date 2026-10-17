"""Mô hình hóa đơn thanh toán."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

from src.money import to_vnd


class Invoice:
    """Đại diện cho hóa đơn thanh toán của một đơn hàng."""

    def __init__(
        self,
        order_id: str,
        total: int,
        invoice_id: Optional[str] = None,
        table_id: str = "",
        created_at: Optional[str] = None,
        payment_id: str = "",
    ):
        self.invoice_id = invoice_id or f"HD-{datetime.now().strftime('%y%m%d%H%M%S')}"
        self.order_id = str(order_id)
        self.total = to_vnd(total)
        self.table_id = str(table_id)
        self.created_at = created_at or datetime.now().isoformat()
        self.payment_id = str(payment_id)

    @property
    def id(self) -> str:
        return self.invoice_id

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.invoice_id,
            "invoice_id": self.invoice_id,
            "order_id": self.order_id,
            "total": self.total,
            "table_id": self.table_id,
            "table": self.table_id,
            "created_at": self.created_at,
            "payment_id": self.payment_id,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Invoice":
        inv_id = data.get("invoice_id") or data.get("id")
        return cls(
            invoice_id=inv_id,
            order_id=data.get("order_id", ""),
            total=data.get("total", 0),
            table_id=data.get("table_id") or data.get("table", ""),
            created_at=data.get("created_at"),
            payment_id=data.get("payment_id", ""),
        )

    def __getitem__(self, key: str) -> Any:
        mapping = {
            "id": self.invoice_id,
            "invoice_id": self.invoice_id,
            "order_id": self.order_id,
            "total": self.total,
            "table_id": self.table_id,
            "table": self.table_id,
            "created_at": self.created_at,
            "payment_id": self.payment_id,
        }
        if key in mapping:
            return mapping[key]
        raise KeyError(key)

    def __setitem__(self, key: str, value: Any) -> None:
        if key in ("id", "invoice_id"):
            self.invoice_id = str(value)
        elif key == "order_id":
            self.order_id = str(value)
        elif key == "total":
            self.total = to_vnd(value)
        elif key in ("table_id", "table"):
            self.table_id = str(value)
        elif key == "created_at":
            self.created_at = str(value)
        elif key == "payment_id":
            self.payment_id = str(value)
        else:
            setattr(self, key, value)

    def get(self, key: str, default: Any = None) -> Any:
        try:
            return self[key]
        except KeyError:
            return default

    def __repr__(self) -> str:
        return f"Invoice(id='{self.invoice_id}', order_id='{self.order_id}', total={self.total})"
