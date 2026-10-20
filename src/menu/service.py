"""Nghiệp vụ quản lý thực đơn (Menu Service / Menu Manager)."""
from __future__ import annotations

from typing import Any, Container, Dict, List, Optional

from src.shared.data_structures.hash_map import HashMap
from src.menu.repository import MenuRepository
from src.menu.model import MenuItem


class DuplicateCodeError(Exception):
    """Ngoại lệ khi mã món ăn bị trùng lặp."""
    pass


class ItemNotFoundError(Exception):
    """Ngoại lệ khi không tìm thấy món ăn trong thực đơn."""
    pass


class MenuService:
    """Quản lý danh mục món ăn, tìm kiếm, cập nhật và lưu trữ thực đơn."""

    def __init__(self, storage_or_path: Optional[Any] = None):
        self.repository = (
            storage_or_path
            if isinstance(storage_or_path, MenuRepository)
            else MenuRepository(storage_or_path)
        )
        self._map = HashMap(initial_capacity=16)
        self._items: Dict[str, MenuItem] = {}
        self._order_service: Any = None
        self.load()

    def set_order_service(self, order_service: Any) -> None:
        self._order_service = order_service

    @staticmethod
    def _normalize_code(code: str) -> str:
        if not isinstance(code, str):
            raise ValueError("Mã món phải là chuỗi ký tự")
        return code.strip().upper()

    def load(self) -> None:
        """Load menu entities from their repository."""
        self._items.clear()
        self._map = HashMap(initial_capacity=16)
        for item in self.repository.list_all():
            self._items[item.code] = item
            self._map.put(item.code, item)

    def save(self) -> None:
        """Persist the current menu through its repository."""
        self.repository.save_all(self.list_items(only_active=False))

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

        self.repository.add(item)
        self._items[item.code] = item
        self._map.put(item.code, item)
        return item

    def get_item(self, code: str) -> Optional[MenuItem]:
        """Tra cứu món theo mã (O(1))."""
        normalized = self._normalize_code(code)
        return self._map.get(normalized)

    def find_item(self, item_id: str) -> Optional[MenuItem]:
        """Bí danh tra cứu theo item_id."""
        return self.get_item(item_id)

    def update_item(
        self,
        code: str,
        name: Optional[str] = None,
        price: Optional[int] = None,
        is_active: Optional[bool] = None,
    ) -> MenuItem:
        """Cập nhật thông tin (tên/giá) của món ăn."""
        if is_active is not None and not isinstance(is_active, bool):
            raise ValueError("Trạng thái món phải là boolean")
        item = self.get_item(code)
        if item is None:
            raise ItemNotFoundError(f"Không tìm thấy món ăn với mã '{code}'.")

        updated_item = MenuItem(
            code=item.code,
            name=item.name if name is None else name,
            price=item.price if price is None else price,
            is_active=item.is_active,
        )
        if is_active is not None:
            updated_item.is_active = is_active
        self.repository.update(updated_item)
        item.name = updated_item.name
        item.price = updated_item.price
        item.is_active = updated_item.is_active
        self._map.put(item.code, item)
        return item

    def toggle_status(self, code: str) -> MenuItem:
        """Đảo trạng thái kinh doanh của món và lưu thay đổi."""
        item = self.get_item(code)
        if item is None:
            raise ItemNotFoundError(f"Không tìm thấy món ăn với mã '{code}'.")
        return self.update_item(code, is_active=not item.is_active)

    def remove_item(
        self,
        code: str,
        used_codes: Optional[Container[str]] = None,
    ) -> bool:
        """Xóa món khỏi thực đơn; nếu đã phát sinh trong đơn hàng thì chuyển sang tạm ngừng (deactivate)."""
        item = self.get_item(code)
        if item is None:
            return False

        if used_codes is None:
            used_codes = (
                self._order_service.used_codes()
                if self._order_service is not None
                else ()
            )
        normalized_used = {self._normalize_code(c) for c in used_codes}
        if item.code in normalized_used:
            item.deactivate()
            self.repository.update(item)
        else:
            self.repository.delete(item.code)
            self._items.pop(item.code, None)
            self._map.remove(item.code)

        return True

    def list_items(self, only_active: bool = False) -> List[MenuItem]:
        """Trả về danh sách tất cả các món ăn, sắp xếp theo mã."""
        items = list(self._items.values())
        if only_active:
            items = [item for item in items if item.is_active]
        return sorted(items, key=lambda x: x.code)

    def search(self, keyword: str) -> List[MenuItem]:
        """Tìm kiếm món ăn theo mã hoặc tên món."""
        return sorted(self.repository.search_items(keyword), key=lambda item: item.code)

    def __iter__(self):
        return iter(self.list_items())

    def __len__(self):
        return len(self._items)


# Định nghĩa alias MenuManager tương thích hoàn toàn với bài tập của nhóm
MenuManager = MenuService
