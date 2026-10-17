"""Nghiệp vụ quản lý thực đơn (Menu Service / Menu Manager).

Kết hợp cấu trúc dữ liệu HashMap để tra cứu O(1) và JsonStorage để lưu trữ bền vững.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Container, Dict, List, Optional

from src.core.data_structures.hash_map import HashMap
from src.core.storage import JsonStorage
from src.models.menu_item import MenuItem


class DuplicateCodeError(Exception):
    """Ngoại lệ khi mã món ăn bị trùng lặp."""
    pass


class ItemNotFoundError(Exception):
    """Ngoại lệ khi không tìm thấy món ăn trong thực đơn."""
    pass


class MenuService:
    """Quản lý danh mục món ăn, tìm kiếm, cập nhật và lưu trữ thực đơn."""

    def __init__(self, storage_or_path: Optional[Any] = None):
        if storage_or_path is None:
            default_path = Path(__file__).resolve().parents[3] / "data" / "menu_sample.json"
            self.storage: Optional[JsonStorage] = JsonStorage(default_path)
        elif isinstance(storage_or_path, (str, Path)):
            self.storage = JsonStorage(storage_or_path)
        elif hasattr(storage_or_path, "load") and hasattr(storage_or_path, "save"):
            self.storage = storage_or_path
        else:
            self.storage = None

        self._map = HashMap(initial_capacity=16)
        self._items: Dict[str, MenuItem] = {}
        self.load()

    @staticmethod
    def _normalize_code(code: str) -> str:
        if not isinstance(code, str):
            raise ValueError("Mã món phải là chuỗi ký tự")
        return code.strip().upper()

    def load(self) -> None:
        """Đọc toàn bộ thực đơn từ file lưu trữ vào bộ nhớ."""
        if self.storage is None:
            return

        data = self.storage.load(default=[])
        if not data:
            return

        for item_data in data:
            if isinstance(item_data, dict):
                item = MenuItem.from_dict(item_data)
                self._items[item.code] = item
                self._map.put(item.code, item)

    def save(self) -> None:
        """Lưu toàn bộ thực đơn trong bộ nhớ vào storage."""
        if self.storage is not None:
            serialized = [item.to_dict() for item in self.list_items(only_active=False)]
            self.storage.save(serialized)

    def add_item(
        self,
        code_or_item: Any,
        name: Optional[str] = None,
        price: Optional[int] = None,
    ) -> MenuItem:
        """Thêm món ăn mới vào thực đơn. Chấp nhận đối tượng MenuItem hoặc (code, name, price)."""
        if isinstance(code_or_item, MenuItem):
            item = code_or_item
        else:
            if name is None or price is None:
                raise ValueError("Vui lòng cung cấp đầy đủ mã, tên và giá món")
            item = MenuItem(code=str(code_or_item), name=name, price=price)

        if item.code in self._items:
            raise DuplicateCodeError(f"Mã món '{item.code}' đã tồn tại trong thực đơn.")

        self._items[item.code] = item
        self._map.put(item.code, item)
        self.save()
        return item

    def get_item(self, code: str) -> Optional[MenuItem]:
        """Tra cứu món theo mã (O(1))."""
        normalized = self._normalize_code(code)
        # Tra cứu qua HashMap
        found = self._map.get(normalized)
        if found is not None:
            return found
        return self._items.get(normalized)

    def find_item(self, item_id: str) -> Optional[MenuItem]:
        """Bí danh tra cứu theo item_id."""
        return self.get_item(item_id)

    def update_item(
        self, code: str, name: Optional[str] = None, price: Optional[int] = None
    ) -> MenuItem:
        """Cập nhật thông tin (tên/giá) của món ăn."""
        item = self.get_item(code)
        if item is None:
            raise ItemNotFoundError(f"Không tìm thấy món ăn với mã '{code}'.")

        item.update(name=name, price=price)
        self._map.put(item.code, item)
        self.save()
        return item

    def remove_item(self, code: str, used_codes: Container[str] = ()) -> bool:
        """Xóa món khỏi thực đơn; nếu đã phát sinh trong đơn hàng thì chuyển sang tạm ngừng (deactivate)."""
        item = self.get_item(code)
        if item is None:
            return False

        normalized_used = {self._normalize_code(c) for c in used_codes}
        if item.code in normalized_used:
            item.deactivate()
        else:
            self._items.pop(item.code, None)
            self._map.remove(item.code)

        self.save()
        return True

    def list_items(self, only_active: bool = False) -> List[MenuItem]:
        """Trả về danh sách tất cả các món ăn, sắp xếp theo mã."""
        items = list(self._items.values())
        if only_active:
            items = [item for item in items if item.is_active]
        return sorted(items, key=lambda x: x.code)

    def search(self, keyword: str) -> List[MenuItem]:
        """Tìm kiếm món ăn theo mã hoặc tên món."""
        kw = keyword.strip().casefold()
        if not kw:
            return self.list_items(only_active=False)
        return [
            item for item in self.list_items(only_active=False)
            if kw in item.code.casefold() or kw in item.name.casefold()
        ]

    def __iter__(self):
        return iter(self.list_items())

    def __len__(self):
        return len(self._items)


# Định nghĩa alias MenuManager tương thích hoàn toàn với bài tập của nhóm
MenuManager = MenuService
