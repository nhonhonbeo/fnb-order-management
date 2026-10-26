"""Dịch vụ quản lý thực đơn (Menu Service) trong hệ thống F&B."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from src.features.menu.model import MenuItem
from src.features.menu.repository import MenuRepository


class DuplicateCodeError(ValueError):
    """Raised when a menu item code already exists."""


class MenuService:
    """Quản lý danh sách món ăn, trạng thái kinh doanh và thời gian chế biến."""

    def __init__(self, storage_or_path: Optional[Any] = None):
        if isinstance(storage_or_path, MenuRepository):
            self.repository = storage_or_path
        else:
            self.repository = MenuRepository(storage_or_path)
            
        self._items: Dict[str, MenuItem] = {}
        self.order_service: Optional[Any] = None
        self.load()

    def set_order_service(self, order_service: Any) -> None:
        """Liên kết dịch vụ đơn hàng với menu service."""
        self.order_service = order_service

    def load(self) -> None:
        """Nạp danh sách món ăn từ cơ sở dữ liệu / file JSON."""
        raw_items = []
        if hasattr(self.repository, "load_items"):
            raw_items = self.repository.load_items()
        elif hasattr(self.repository, "load"):
            raw_items = self.repository.load()
        elif hasattr(self.repository, "get_all"):
            raw_items = self.repository.get_all()

        self._items = {}
        for item in raw_items:
            if isinstance(item, dict):
                menu_item = MenuItem.from_dict(item)
            elif isinstance(item, MenuItem):
                menu_item = item
            else:
                continue
            self._items[menu_item.code] = menu_item

    def save(self) -> None:
        """Lưu trạng thái thực đơn vào cơ sở dữ liệu / file JSON."""
        items_list = list(self._items.values())
        if hasattr(self.repository, "save_items"):
            self.repository.save_items(items_list)
        elif hasattr(self.repository, "save"):
            self.repository.save(items_list)

    def get_item(self, item_code: str) -> Optional[MenuItem]:
        """Lấy thông tin chi tiết một món ăn theo mã (code hoặc item_id)."""
        normalized_code = str(item_code).strip().upper()
        return self._items.get(normalized_code)

    def list_items(self, only_active: bool = False, active_only: Optional[bool] = None) -> List[MenuItem]:
        """Lấy danh sách toàn bộ món ăn trong thực đơn."""
        filter_active = active_only if active_only is not None else only_active
        items = list(self._items.values())
        if filter_active:
            return [item for item in items if item.is_active]
        return items

    def add_item(
        self,
        code: str,
        name: str,
        price: int,
        processing_time: int = 5,
        is_active: bool = True,
    ) -> MenuItem:
        """Thêm một món ăn mới vào thực đơn với thời gian chế biến tùy chỉnh."""
        normalized_code = str(code).strip().upper()
        if normalized_code in self._items:
            raise DuplicateCodeError(f"Món ăn có mã '{normalized_code}' đã tồn tại trong thực đơn")

        new_item = MenuItem(
            code=normalized_code,
            name=name,
            price=price,
            processing_time=processing_time,
            is_active=is_active,
        )
        self._items[normalized_code] = new_item
        self.save()
        return new_item

    def update_item(
        self,
        item_code: str,
        name: Optional[str] = None,
        price: Optional[int] = None,
        processing_time: Optional[int] = None,
    ) -> MenuItem:
        """Cập nhật thông tin món ăn (tên, giá, thời gian chế biến)."""
        item = self.get_item(item_code)
        if item is None:
            raise ValueError(f"Không tìm thấy món ăn có mã '{item_code}'")

        item.update(name=name, price=price, processing_time=processing_time)
        self.save()
        return item

    def update_processing_time(self, item_code: str, new_processing_time: int) -> MenuItem:
        """
        Cho phép quản lý hoặc nhà bếp điều chỉnh thời gian hoàn thành (processing_time) 
        của món ăn linh hoạt theo thực tế vận hành.
        """
        item = self.get_item(item_code)
        if item is None:
            raise ValueError(f"Không tìm thấy món ăn có mã '{item_code}'")

        if new_processing_time < 0:
            raise ValueError("Thời gian hoàn thành không được âm")

        item.processing_time = int(new_processing_time)
        self.save()
        return item

    def set_active_status(self, item_code: str, is_active: bool) -> MenuItem:
        """Kinh doanh hoặc tạm ngừng kinh doanh món ăn."""
        item = self.get_item(item_code)
        if item is None:
            raise ValueError(f"Không tìm thấy món ăn có mã '{item_code}'")

        if is_active:
            item.activate()
        else:
            item.deactivate()
        self.save()
        return item

    def delete_item(self, item_code: str) -> None:
        """Xóa vĩnh viễn một món ăn khỏi thực đơn."""
        normalized_code = str(item_code).strip().upper()
        if normalized_code not in self._items:
            raise ValueError(f"Không tìm thấy món ăn có mã '{item_code}'")

        del self._items[normalized_code]
        self.save()