from typing import Container, Dict, List, Optional
try:
    from src.models.menu_item import MenuItem
except ImportError:
    try:
        from models.menu_item import MenuItem
    except ImportError:
        from feature.menu_item import MenuItem


class DuplicateCodeError(Exception):
    """Ngoại lệ ném ra khi mã món đã tồn tại trong thực đơn."""
    pass


class ItemNotFoundError(Exception):
    """Ngoại lệ ném ra khi không tìm thấy món trong thực đơn."""
    pass


class MenuManager:
    def __init__(self) -> None:
        """Khởi tạo danh mục thực đơn dạng dict[str, MenuItem] nội bộ."""
        self._items: Dict[str, MenuItem] = {}

    @staticmethod
    def _chuan_hoa(code: str) -> str:
        """Hàm phụ giúp cắt khoảng trắng và chuyển mã thành chữ in hoa."""
        if not isinstance(code, str):
            raise ValueError("Mã món phải là chuỗi ký tự")
        return code.strip().upper()

    def add_item(self, code: str, name: str, price: int) -> MenuItem:
        """Thêm món mới vào thực đơn.
        
        - Tạo MenuItem trước để kích hoạt validate dữ liệu tự động.
        - Chặn mã trùng, báo lỗi DuplicateCodeError nếu mã đã tồn tại.
        """
        # Tạo MenuItem trước (việc validate mã, tên, giá chạy tự động ở __post_init__ của MenuItem)
        item = MenuItem(code=code, name=name, price=price)

        # Kiểm tra trùng mã
        if item.code in self._items:
            raise DuplicateCodeError(f"Mã món '{item.code}' đã tồn tại trong thực đơn.")

        self._items[item.code] = item
        return item

    def get_item(self, code: str) -> MenuItem:
        """Tra cứu món theo mã với độ phức tạp O(1).
        
        Ném lỗi ItemNotFoundError nếu mã không tồn tại.
        """
        ma = self._chuan_hoa(code)
        if ma not in self._items:
            raise ItemNotFoundError(f"Không tìm thấy món ăn với mã '{ma}'.")
        return self._items[ma]

    def update_item(
        self, code: str, name: Optional[str] = None, price: Optional[int] = None
    ) -> MenuItem:
        """Cập nhật thông tin món ăn (tên/giá)."""
        item = self.get_item(code)
        item.update(name=name, price=price)
        return item

    def remove_item(self, code: str, used_codes: Container[str]) -> None:
        """Xóa món chưa dùng trong đơn hàng; nếu đã được dùng thì chỉ ngừng kinh doanh (deactivate)."""
        item = self.get_item(code)

        # Chuẩn hóa tập hợp các mã đã từng dùng trong đơn hàng
        normalized_used = {self._chuan_hoa(c) for c in used_codes}

        if item.code in normalized_used:
            item.deactivate()
        else:
            del self._items[item.code]

    def list_items(self, only_active: bool = False) -> List[MenuItem]:
        """Trả về danh sách món ăn, được sắp xếp theo mã món.
        
        - only_active = True: chỉ trả về các món đang kinh doanh (is_active == True).
        - only_active = False: trả về toàn bộ các món trong thực đơn.
        """
        ds = list(self._items.values())

        if only_active:
            ds = [item for item in ds if item.is_active]

        # Sắp xếp danh sách theo mã món (code)
        return sorted(ds, key=lambda x: x.code)