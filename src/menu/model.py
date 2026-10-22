"""Mô hình món ăn trong hệ thống F&B."""
from __future__ import annotations

from typing import Any, Dict, Optional

from src.shared.money import to_whole_vnd


class MenuItem:
    """Đại diện cho một món ăn trong thực đơn.

    Hỗ trợ cả truy cập dạng thuộc tính (item.code) lẫn dạng từ điển (item['code']),
    đồng bộ tương thích giữa mã 'code' và 'item_id'.
    """

    def __init__(
        self,
        code: str = "",
        name: str = "",
        price: int = 0,
        is_active: bool = True,
        item_id: Optional[str] = None,
        processing_time: int = 5,  # Thời gian hoàn thành (phút)
    ):
        raw_code = item_id if item_id is not None else code
        self.code: str = str(raw_code).strip().upper() if raw_code else ""
        self.name: str = str(name).strip() if name else ""
        self.price: int = to_whole_vnd(price)
        self.is_active: bool = bool(is_active)
        self.processing_time: int = int(processing_time)

        self._validate()

    def _validate(self) -> None:
        """Kiểm tra tính hợp lệ của mã món, tên món, giá bán và thời gian chế biến."""
        if not self.code or not self.name:
            raise ValueError("Mã và tên không được rỗng")
        self._validate_price(self.price)
        if self.processing_time < 0:
            raise ValueError("Thời gian hoàn thành không được âm")

    @staticmethod
    def _validate_price(price: Any) -> None:
        """Kiểm tra giá hợp lệ (phải là số nguyên > 0, loại trừ boolean)."""
        if isinstance(price, bool) or not isinstance(price, int) or price <= 0:
            raise ValueError("Giá phải là số nguyên lớn hơn 0")

    @property
    def item_id(self) -> str:
        """Bí danh (alias) tương thích với item_id."""
        return self.code

    @item_id.setter
    def item_id(self, value: str) -> None:
        self.code = str(value).strip().upper()

    def update(
        self, 
        name: Optional[str] = None, 
        price: Optional[int] = None, 
        processing_time: Optional[int] = None
    ) -> None:
        """Cập nhật tên, đơn giá và/hoặc thời gian hoàn thành của món ăn."""
        new_name = self.name if name is None else str(name).strip()
        new_price = self.price if price is None else to_whole_vnd(price)
        new_time = self.processing_time if processing_time is None else int(processing_time)

        if not new_name:
            raise ValueError("Mã và tên không được rỗng")
        self._validate_price(new_price)
        if new_time < 0:
            raise ValueError("Thời gian hoàn thành không được âm")

        self.name = new_name
        self.price = new_price
        self.processing_time = new_time

    def deactivate(self) -> None:
        """Tạm ngừng kinh doanh món ăn."""
        self.is_active = False

    def activate(self) -> None:
        """Mở bán lại món ăn."""
        self.is_active = True

    def to_dict(self) -> Dict[str, Any]:
        """Chuyển đổi thành từ điển phục vụ lưu trữ JSON."""
        return {
            "item_id": self.code,
            "code": self.code,
            "name": self.name,
            "price": self.price,
            "is_active": self.is_active,
            "processing_time": self.processing_time,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MenuItem":
        """Tạo đối tượng MenuItem từ từ điển dữ liệu."""
        code = data.get("code") or data.get("item_id", "")
        return cls(
            code=code,
            name=data.get("name", ""),
            price=data.get("price", 0),
            is_active=bool(data.get("is_active", True)),
            processing_time=int(data.get("processing_time", 5)),
        )

    def __getitem__(self, key: str) -> Any:
        mapping = {
            "item_id": self.code,
            "code": self.code,
            "name": self.name,
            "price": self.price,
            "is_active": self.is_active,
            "processing_time": self.processing_time,
        }
        if key in mapping:
            return mapping[key]
        raise KeyError(key)

    def __setitem__(self, key: str, value: Any) -> None:
        if key in ("code", "item_id"):
            self.code = str(value).strip().upper()
        elif key == "name":
            self.name = str(value).strip()
        elif key == "price":
            self.price = to_whole_vnd(value)
        elif key == "is_active":
            self.is_active = bool(value)
        elif key == "processing_time":
            self.processing_time = int(value)
        else:
            setattr(self, key, value)

    def get(self, key: str, default: Any = None) -> Any:
        try:
            return self[key]
        except KeyError:
            return default

    def __contains__(self, key: str) -> bool:
        return key in ("item_id", "code", "name", "price", "is_active", "processing_time")

    def __repr__(self) -> str:
        return (
            f"MenuItem(code='{self.code}', name='{self.name}', "
            f"price={self.price}, is_active={self.is_active}, processing_time={self.processing_time})"
        )