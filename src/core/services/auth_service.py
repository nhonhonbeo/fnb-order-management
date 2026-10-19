"""Nghiệp vụ xác thực người dùng và quản lý tài khoản."""
import hashlib
import secrets
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple

from src.core.data_structures.hash_table import HashTable
from src.core.storage import JsonStorage
from src.models.user import User


class AuthService:
    def __init__(self, storage_path: str | Path | None = None):
        if storage_path is None:
            storage_path = Path(__file__).resolve().parents[3] / "data" / "users.json"
        self.storage = JsonStorage(storage_path)
        self._users_by_username = HashTable()
        self._ensure_default_users()
        self._rebuild_username_index()

    def _rebuild_username_index(self) -> None:
        """Tạo index tra cứu username không phân biệt hoa thường."""
        for user in self.get_users():
            self._users_by_username.insert(user.username.casefold(), user)

    @staticmethod
    def hash_password(password: str, salt: str | None = None) -> str:
        """Băm mật khẩu bằng PBKDF2-HMAC-SHA256 kèm salt ngẫu nhiên."""
        if not salt:
            salt = secrets.token_hex(16)
        iterations = 100_000
        hash_bytes = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt.encode("utf-8"),
            iterations,
        )
        return f"{salt}${iterations}${hash_bytes.hex()}"

    @staticmethod
    def verify_password(password: str, stored_hash: str) -> bool:
        """Kiểm tra mật khẩu nhập vào có khớp với hash đã lưu hay không."""
        try:
            salt, iterations_str, hash_hex = stored_hash.split("$")
            iterations = int(iterations_str)
            computed_hash = hashlib.pbkdf2_hmac(
                "sha256",
                password.encode("utf-8"),
                salt.encode("utf-8"),
                iterations,
            ).hex()
            return secrets.compare_digest(computed_hash, hash_hex)
        except Exception:
            return False

    def _ensure_default_users(self) -> None:
        """Khởi tạo tài khoản mẫu nếu tệp dữ liệu người dùng chưa tồn tại."""
        existing = self.storage.load(default=None)
        if existing is None:
            default_users = [
                User(
                    username="admin",
                    password_hash=self.hash_password("admin123"),
                    full_name="Quản Trị Viên",
                    role="Quản lý",
                    created_at=datetime.now().isoformat(),
                ).to_dict(),
                User(
                    username="nhanvien",
                    password_hash=self.hash_password("123456"),
                    full_name="Nguyễn Văn Thu Ngân",
                    role="Nhân viên",
                    created_at=datetime.now().isoformat(),
                ).to_dict(),
            ]
            self.storage.save(default_users)

    def get_users(self) -> list[User]:
        """Lấy danh sách tất cả người dùng."""
        raw_users = self.storage.load(default=[])
        return [User.from_dict(item) for item in raw_users]

    def get_user_by_username(self, username: str) -> Optional[User]:
        """Tìm người dùng theo tên đăng nhập (không phân biệt hoa thường)."""
        clean_name = username.strip().casefold()
        return self._users_by_username.get(clean_name)

    def authenticate(self, username: str, password: str) -> Optional[User]:
        """Xác thực đăng nhập tài khoản và mật khẩu."""
        if not username or not password:
            return None
        user = self.get_user_by_username(username)
        if not user:
            return None
        if self.verify_password(password, user.password_hash):
            return user
        return None

    def register(
        self, username: str, password: str, full_name: str, role: str = "Nhân viên"
    ) -> Tuple[bool, str, Optional[User]]:
        """Đăng ký tài khoản mới với các bước kiểm tra tính hợp lệ."""
        username_clean = username.strip()
        full_name_clean = full_name.strip()

        if not username_clean:
            return False, "Vui lòng nhập tên đăng nhập.", None
        if len(username_clean) < 3:
            return False, "Tên đăng nhập phải có ít nhất 3 ký tự.", None
        if not username_clean.isalnum() and "_" not in username_clean:
            return False, "Tên đăng nhập chỉ chứa chữ cái, số và dấu gạch dưới.", None
        if not full_name_clean:
            return False, "Vui lòng nhập họ và tên.", None
        if not password:
            return False, "Vui lòng nhập mật khẩu.", None
        if len(password) < 6:
            return False, "Mật khẩu phải có độ dài tối thiểu 6 ký tự.", None

        if self.get_user_by_username(username_clean):
            return False, f"Tài khoản '{username_clean}' đã tồn tại trong hệ thống.", None

        valid_roles = ["Quản lý", "Nhân viên", "Thu ngân", "Đầu bếp"]
        assigned_role = role if role in valid_roles else "Nhân viên"

        new_user = User(
            username=username_clean,
            password_hash=self.hash_password(password),
            full_name=full_name_clean,
            role=assigned_role,
            created_at=datetime.now().isoformat(),
        )

        all_users = self.get_users()
        all_users.append(new_user)
        self.storage.save([u.to_dict() for u in all_users])
        self._users_by_username.insert(new_user.username.casefold(), new_user)
        return True, "Đăng ký tài khoản thành công!", new_user
