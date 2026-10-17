"""Nghiệp vụ tính tiền, xuất hóa đơn và thống kê doanh thu (Billing Service)."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from src.core.storage import JsonStorage
from src.models.invoice import Invoice


class BillingService:
    """Quản lý tính toán hóa đơn, xuất biên lai và lưu trữ doanh thu."""

    def __init__(self, storage_or_path: Optional[Any] = None):
        if storage_or_path is None:
            default_path = Path(__file__).resolve().parents[3] / "data" / "invoices.json"
            self.storage: Optional[JsonStorage] = JsonStorage(default_path)
        elif isinstance(storage_or_path, (str, Path)):
            self.storage = JsonStorage(storage_or_path)
        elif hasattr(storage_or_path, "load") and hasattr(storage_or_path, "save"):
            self.storage = storage_or_path
        else:
            self.storage = None

        self._invoices: List[Invoice] = []
        self.load()

    def load(self) -> None:
        """Đọc danh sách hóa đơn từ storage vào bộ nhớ."""
        if self.storage is None:
            return

        raw_invoices = self.storage.load(default=[])
        self._invoices = [
            inv if isinstance(inv, Invoice) else Invoice.from_dict(inv)
            for inv in raw_invoices
            if isinstance(inv, (dict, Invoice))
        ]

    def save(self) -> None:
        """Lưu toàn bộ hóa đơn ra storage."""
        if self.storage is not None:
            serialized = [inv.to_dict() for inv in self._invoices]
            self.storage.save(serialized)

    def calculate_total(self, order_or_items: Any) -> float:
        """Tính tổng số tiền của đơn hàng hoặc danh sách món ăn."""
        if hasattr(order_or_items, "total"):
            return float(order_or_items.total())

        if isinstance(order_or_items, dict):
            if "total" in order_or_items:
                return float(order_or_items["total"])
            if "items" in order_or_items:
                return self.calculate_total(order_or_items["items"])

        total = 0.0
        if isinstance(order_or_items, list):
            for item in order_or_items:
                if hasattr(item, "subtotal"):
                    total += float(item.subtotal())
                elif isinstance(item, dict):
                    price = item.get("unit_price") or item.get("price", 0)
                    qty = item.get("quantity", 1)
                    total += float(price * qty)
        return total

    def create_invoice(
        self,
        order: Any,
        payment_id: str = "",
        invoice_id: Optional[str] = None,
    ) -> Invoice:
        """Tạo hóa đơn từ đơn hàng và lưu vào storage."""
        if isinstance(order, dict):
            order_id = str(order.get("order_id") or order.get("id", ""))
            table_id = str(order.get("table_id") or order.get("table", ""))
        else:
            order_id = str(getattr(order, "order_id", getattr(order, "id", "")))
            table_id = str(getattr(order, "table_id", getattr(order, "table", "")))

        total = self.calculate_total(order)

        invoice = Invoice(
            order_id=order_id,
            total=total,
            invoice_id=invoice_id,
            table_id=table_id,
            payment_id=payment_id,
        )
        self._invoices.append(invoice)
        self.save()
        return invoice

    def list_invoices(self) -> List[Invoice]:
        """Trả về toàn bộ danh sách hóa đơn đã lập."""
        return list(self._invoices)

    def get_total_revenue(self) -> float:
        """Tính tổng doanh thu thực tế từ tất cả các hóa đơn."""
        return sum(inv.total for inv in self._invoices)
