"""Đọc và ghi dữ liệu JSON cho ứng dụng F&B.

Hỗ trợ lưu trữ bền vững (persistence) cho thực đơn, người dùng, bàn ăn,
đơn hàng, hàng đợi bếp và hóa đơn/thanh toán.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional


class JsonStorage:
    """Lớp lưu trữ JSON cơ bản hỗ trợ đọc/ghi UTF-8 và tự động tạo thư mục cha."""

    def __init__(self, file_path: str | Path):
        self.file_path = Path(file_path)

    def exists(self) -> bool:
        """Kiểm tra tệp tin có tồn tại hay không."""
        return self.file_path.is_file()

    def load(self, default: Any = None) -> Any:
        """Đọc dữ liệu từ file JSON, trả về default nếu file không tồn tại hoặc lỗi định dạng."""
        try:
            with self.file_path.open("r", encoding="utf-8") as json_file:
                return json.load(json_file)
        except (FileNotFoundError, json.JSONDecodeError):
            return default

    def save(self, data: Any) -> None:
        """Ghi dữ liệu ra file JSON theo chuẩn UTF-8 kèm định dạng dễ đọc (indent=2)."""
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        with self.file_path.open("w", encoding="utf-8") as json_file:
            json.dump(data, json_file, ensure_ascii=False, indent=2)
            json_file.write("\n")

    def delete(self) -> bool:
        """Xóa tệp nếu tồn tại. Trả về True nếu đã xóa thành công."""
        if self.file_path.exists():
            self.file_path.unlink()
            return True
        return False


class StorageManager:
    """Quản lý lưu trữ tập trung cho toàn bộ dữ liệu ứng dụng F&B."""

    DEFAULT_TABLES = {f"Bàn {i}": "Trống" for i in range(1, 11)}

    def __init__(self, data_dir: str | Path | None = None):
        if data_dir is None:
            self.data_dir = Path(__file__).resolve().parents[2] / "data"
        else:
            self.data_dir = Path(data_dir)

        self.data_dir.mkdir(parents=True, exist_ok=True)

        seed_path = Path(__file__).resolve().parents[2] / "data" / "menu_seed.json"
        self.menu_seed_storage = JsonStorage(seed_path)
        self.menu_storage = JsonStorage(self.data_dir / "menu.json")
        if not self.menu_storage.exists():
            legacy_menu_storage = JsonStorage(self.data_dir / "menu_sample.json")
            menu_data = legacy_menu_storage.load(default=None)
            if menu_data is None:
                menu_data = self.menu_seed_storage.load(default=[])
            self.menu_storage.save(menu_data)
        self.users_storage = JsonStorage(self.data_dir / "users.json")
        self.orders_storage = JsonStorage(self.data_dir / "orders.json")
        self.tables_storage = JsonStorage(self.data_dir / "tables.json")
        self.invoices_storage = JsonStorage(self.data_dir / "invoices.json")
        self.payments_storage = JsonStorage(self.data_dir / "payments.json")
        self.kitchen_storage = JsonStorage(self.data_dir / "kitchen.json")

    # ------------------ Menu ------------------
    def load_menu(self) -> List[Dict[str, Any]]:
        """Đọc danh sách món ăn từ storage, tự động seed dữ liệu mẫu nếu chưa có."""
        data = self.menu_storage.load(default=None)
        if data is None:
            data = self.menu_seed_storage.load(default=[])
            self.menu_storage.save(data)
        return data

    def save_menu(self, menu_items: List[Any]) -> None:
        """Lưu danh sách món ăn vào storage."""
        serialized = []
        for item in menu_items:
            if hasattr(item, "to_dict"):
                serialized.append(item.to_dict())
            elif isinstance(item, dict):
                serialized.append(item)
            else:
                serialized.append({
                    "item_id": getattr(item, "item_id", getattr(item, "code", "")),
                    "code": getattr(item, "code", getattr(item, "item_id", "")),
                    "name": getattr(item, "name", ""),
                    "price": getattr(item, "price", 0),
                    "is_active": getattr(item, "is_active", True),
                })
        self.menu_storage.save(serialized)

    # ------------------ Tables ------------------
    def load_tables(self) -> Dict[str, str]:
        """Đọc trạng thái các bàn từ storage."""
        data = self.tables_storage.load(default=None)
        if data is None:
            self.tables_storage.save(self.DEFAULT_TABLES)
            return dict(self.DEFAULT_TABLES)
        return data

    def save_tables(self, tables: Dict[str, str] | List[Any]) -> None:
        """Lưu trạng thái các bàn vào storage."""
        if isinstance(tables, dict):
            self.tables_storage.save(tables)
        elif isinstance(tables, list):
            data = {}
            for t in tables:
                if hasattr(t, "table_id") and hasattr(t, "status"):
                    data[t.table_id] = t.status
                elif isinstance(t, dict):
                    data[t.get("table_id") or t.get("name")] = t.get("status", "Trống")
            self.tables_storage.save(data)

    # ------------------ Orders ------------------
    def load_orders(self) -> List[Dict[str, Any]]:
        """Đọc danh sách đơn hàng từ storage."""
        return self.orders_storage.load(default=[])

    def save_orders(self, orders: List[Any]) -> None:
        """Lưu danh sách đơn hàng vào storage."""
        serialized = []
        for o in orders:
            if hasattr(o, "to_dict"):
                serialized.append(o.to_dict())
            elif isinstance(o, dict):
                serialized.append(o)
        self.orders_storage.save(serialized)

    # ------------------ Invoices ------------------
    def load_invoices(self) -> List[Dict[str, Any]]:
        """Đọc danh sách hóa đơn từ storage."""
        return self.invoices_storage.load(default=[])

    def save_invoices(self, invoices: List[Any]) -> None:
        """Lưu danh sách hóa đơn vào storage."""
        serialized = []
        for inv in invoices:
            if hasattr(inv, "to_dict"):
                serialized.append(inv.to_dict())
            elif isinstance(inv, dict):
                serialized.append(inv)
        self.invoices_storage.save(serialized)

    # ------------------ Payments ------------------
    def load_payments(self) -> List[Dict[str, Any]]:
        """Đọc danh sách thanh toán từ storage."""
        return self.payments_storage.load(default=[])

    def save_payments(self, payments: List[Any]) -> None:
        """Lưu danh sách thanh toán vào storage."""
        serialized = []
        for p in payments:
            if hasattr(p, "to_dict"):
                serialized.append(p.to_dict())
            elif isinstance(p, dict):
                serialized.append(p)
            else:
                serialized.append({
                    "payment_id": getattr(p, "payment_id", ""),
                    "order_id": getattr(p, "order_id", ""),
                    "amount": getattr(p, "amount", 0),
                    "status": getattr(p.status, "value", str(getattr(p, "status", "SUCCESS"))),
                })
        self.payments_storage.save(serialized)
