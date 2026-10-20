"""Mô hình người dùng trong hệ thống F&B."""
from dataclasses import asdict, dataclass


@dataclass
class User:
    username: str
    password_hash: str
    full_name: str
    role: str = "Nhân viên"
    created_at: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "User":
        return cls(
            username=data.get("username", ""),
            password_hash=data.get("password_hash", ""),
            full_name=data.get("full_name", ""),
            role=data.get("role", "Nhân viên"),
            created_at=data.get("created_at", ""),
        )
