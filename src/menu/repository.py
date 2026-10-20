"""Persistence and lookup operations for menu items."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from src.shared.repository import JsonListRepository, RepositoryDataError
from src.storage.json_storage import JsonStorage
from src.menu.model import MenuItem


class MenuRepository(JsonListRepository[MenuItem]):
    entity_name = "Menu item"
    identifier_fields = ("code",)
    required_fields = ("name", "price")

    def __init__(
        self,
        storage_or_path: Any = None,
        seed_storage: JsonStorage | None = None,
        legacy_storage: JsonStorage | None = None,
    ):
        default_data = Path(__file__).resolve().parents[2] / "data"
        if storage_or_path is None:
            storage = JsonStorage(default_data / "menu.json")
            seed_storage = seed_storage or JsonStorage(default_data / "menu_seed.json")
            legacy_storage = legacy_storage or JsonStorage(default_data / "menu_sample.json")
            initialize_from_seed = True
        elif isinstance(storage_or_path, JsonStorage):
            storage = storage_or_path
            initialize_from_seed = seed_storage is not None or legacy_storage is not None
        elif isinstance(storage_or_path, (str, Path)):
            storage = JsonStorage(storage_or_path)
            initialize_from_seed = False
        else:
            raise TypeError("MenuRepository requires a path or JSON storage object")
        super().__init__(storage)

        if initialize_from_seed and not storage.exists():
            if legacy_storage is not None and legacy_storage.exists():
                seed_data = legacy_storage.load(default=[])
            elif seed_storage is not None:
                seed_data = seed_storage.load(default=[])
            else:
                seed_data = []
            if not isinstance(seed_data, list):
                raise RepositoryDataError(
                    f"Menu seed in '{storage.file_path}' must be a JSON array"
                )
            # Validate before copying seed data into the live file.
            for index, item in enumerate(seed_data):
                self.validate_record(item, index)
                if not isinstance(item, dict) or not (
                    item.get("code") or item.get("item_id")
                ):
                    raise RepositoryDataError(
                        f"Menu item {index} in '{storage.file_path}' is missing "
                        "required field(s): code or item_id"
                    )
                MenuItem.from_dict(item)
            storage.save(seed_data)

    def validate_record(self, record: Any, index: int) -> dict[str, Any]:
        validated = super().validate_record(record, index)
        code = validated.get("code") or validated.get("item_id")
        if not code:
            raise RepositoryDataError(
                f"Menu item {index} in '{self.storage.file_path}' is missing "
                "required field(s): code or item_id"
            )
        if not isinstance(code, str) or not isinstance(validated["name"], str):
            raise RepositoryDataError(
                f"Menu item {index} in '{self.storage.file_path}' requires "
                "string code and name fields"
            )
        if (
            isinstance(validated["price"], bool)
            or not isinstance(validated["price"], (int, float))
        ):
            raise RepositoryDataError(
                f"Menu item {index} in '{self.storage.file_path}' requires a numeric price"
            )
        if "is_active" in validated and not isinstance(validated["is_active"], bool):
            raise RepositoryDataError(
                f"Menu item {index} in '{self.storage.file_path}' requires "
                "a boolean is_active field"
            )
        return validated

    def deserialize(self, record: dict[str, Any]) -> MenuItem:
        try:
            return MenuItem.from_dict(record)
        except (TypeError, ValueError) as error:
            raise RepositoryDataError(
                f"Invalid menu item in '{self.storage.file_path}': {error}"
            ) from error

    def find_by_code(self, code: str) -> MenuItem | None:
        normalized = code.strip().upper()
        return next(
            (item for item in self.list_all() if item.code == normalized),
            None,
        )

    def search_items(self, keyword: str) -> list[MenuItem]:
        normalized = keyword.strip().casefold()
        if not normalized:
            return self.list_all()
        return [
            item for item in self.list_all()
            if normalized in item.code.casefold()
            or normalized in item.name.casefold()
        ]
