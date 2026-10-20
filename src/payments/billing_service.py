"""Nghiệp vụ tính tiền, xuất hóa đơn và thống kê doanh thu (Billing Service)."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from src.payments.invoice_repository import InvoiceRepository
from src.payments.invoice import Invoice
from src.shared.money import to_vnd


class BillingService:
    """Quản lý tính toán hóa đơn, xuất biên lai và lưu trữ doanh thu."""

    def __init__(self, storage_or_path: Optional[Any] = None):
        self.repository = (
            storage_or_path
            if isinstance(storage_or_path, InvoiceRepository)
            else InvoiceRepository(storage_or_path)
        )
        self._invoices: List[Invoice] = []
        self.load()

    def load(self) -> None:
        """Đọc danh sách hóa đơn từ storage vào bộ nhớ."""
        self._invoices = self.repository.list_all()

    def save(self) -> None:
        """Lưu toàn bộ hóa đơn ra storage."""
        self.repository.save_all(self._invoices)

    @staticmethod
    def calculate_total(order_or_items: Any) -> int:
        """Tính tổng số tiền của đơn hàng hoặc danh sách món ăn."""
        if hasattr(order_or_items, "total"):
            return to_vnd(order_or_items.total())

        if isinstance(order_or_items, dict):
            if order_or_items.get("total") is not None:
                return to_vnd(order_or_items["total"])
            if "items" in order_or_items:
                return BillingService.calculate_total(order_or_items["items"])

        total = 0
        if isinstance(order_or_items, list):
            for item in order_or_items:
                if hasattr(item, "subtotal"):
                    total += to_vnd(item.subtotal())
                elif isinstance(item, dict):
                    price = item.get("unit_price") or item.get("price", 0)
                    qty = item.get("quantity", 1)
                    total += to_vnd(price) * int(qty)
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
        self.repository.add(invoice)
        self._invoices.append(invoice)
        return invoice

    def list_invoices(self) -> List[Invoice]:
        """Trả về toàn bộ danh sách hóa đơn đã lập."""
        return list(self._invoices)

    def get_total_revenue(self) -> int:
        """Tính tổng doanh thu thực tế từ tất cả các hóa đơn."""
        return sum(inv.total for inv in self._invoices)
