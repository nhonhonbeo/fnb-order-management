"""Persistence and username lookup for users."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from src.shared.repository import JsonListRepository, RepositoryDataError
from src.features.storage.json_storage import JsonStorage
from src.users.model import User


class UserRepository(JsonListRepository[User]):
    entity_name = "User"
    identifier_fields = ("username",)
    required_fields = ("username", "password_hash", "full_name")

    def __init__(self, storage_or_path: Any = None):
        default_path = Path(__file__).resolve().parents[2] / "data" / "users.json"
        storage = (
            JsonStorage(default_path)
            if storage_or_path is None
            else storage_or_path
            if isinstance(storage_or_path, JsonStorage)
            else JsonStorage(storage_or_path)
            if isinstance(storage_or_path, (str, Path))
            else None
        )
        if storage is None:
            raise TypeError("UserRepository requires a path or JSON storage object")
        super().__init__(storage)

    def deserialize(self, record: dict[str, Any]) -> User:
        if any(
            not isinstance(record[field], str)
            for field in ("username", "password_hash", "full_name")
        ):
            raise RepositoryDataError(
                f"User data in '{self.storage.file_path}' requires string "
                "username, password_hash, and full_name fields"
            )
        if "role" in record and not isinstance(record["role"], str):
            raise RepositoryDataError(
                f"User data in '{self.storage.file_path}' requires a string role"
            )
        if "created_at" in record and not isinstance(record["created_at"], str):
            raise RepositoryDataError(
                f"User data in '{self.storage.file_path}' requires a string created_at"
            )
        return User.from_dict(record)

    def serialize(self, entity: User) -> dict[str, Any]:
        return entity.to_dict()

    def find_by_username(self, username: str) -> User | None:
        normalized = username.strip().casefold()
        return next(
            (user for user in self.list_all()
             if user.username.casefold() == normalized),
            None,
        )
