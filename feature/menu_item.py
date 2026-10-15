from dataclasses import dataclass
from typing import Any, Dict


@dataclass
class MenuItem:
    code: str
    name: str
    price: int
    is_active: bool = True

    def __post_init__(self) -> None:
        """Hàm tự động gọi ngay sau khi đối tượng được khởi tạo."""
        # 1. Làm sạch dữ liệu (cắt khoảng trắng, chuyển mã thành chữ in hoa)
        if isinstance(self.code, str):
            self.code = self.code.strip().upper()
        if isinstance(self.name, str):
            self.name = self.name.strip()

        # 2. Kiểm tra mã và tên không được rỗng
        if not self.code or not self.name:
            raise ValueError("Mã và tên không được rỗng")

        # 3. Kiểm tra giá hợp lệ
        self._validate_price(self.price)

    @staticmethod
    def _validate_price(price: Any) -> None:
        """Hàm dùng chung để kiểm tra giá hợp lệ (phải là số nguyên > 0, loại trừ kiểu bool)."""
        # Trong Python, True/False cũng là thể hiện của int (isinstance(True, int) == True)
        if isinstance(price, bool) or not isinstance(price, int) or price <= 0:
            raise ValueError("Giá phải là số nguyên lớn hơn 0")

    def update(self, name: str | None = None, price: int | None = None) -> None:
        """Cập nhật tên và/hoặc giá của món ăn. Kiểm tra hợp lệ trước khi gán."""
        new_name = self.name
        if name is not None:
            new_name = name.strip()

        new_price = self.price
        if price is not None:
            new_price = price

        # Validate dữ liệu mới trước khi cập nhật
        if not new_name:
            raise ValueError("Mã và tên không được rỗng")
        self._validate_price(new_price)

        # Gán giá trị mới sau khi kiểm tra hợp lệ thành công
        self.name = new_name
        self.price = new_price

    def deactivate(self) -> None:
        """Tạm ngừng kinh doanh món ăn."""
        self.is_active = False

    def activate(self) -> None:
        """Mở bán lại món ăn."""
        self.is_active = True

    def to_dict(self) -> Dict[str, Any]:
        """Chuyển đổi đối tượng thành dictionary."""
        return {
            "code": self.code,
            "name": self.name,
            "price": self.price,
            "is_active": self.is_active,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MenuItem":
        """Tạo đối tượng MenuItem từ dictionary."""
        return cls(
            code=data["code"],
            name=data["name"],
            price=data["price"],
            is_active=data.get("is_active", True),
        )