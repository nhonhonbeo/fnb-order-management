"""Shared JSON file access for repository implementations."""
from __future__ import annotations

import json
import os
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any


class InvalidJsonFileError(ValueError):
    """Raised when a persisted JSON file cannot be decoded."""

    def __init__(self, file_path: Path, error: json.JSONDecodeError):
        super().__init__(
            f"Invalid JSON in '{file_path}' at line {error.lineno}, "
            f"column {error.colno}: {error.msg}"
        )
        self.file_path = file_path


class JsonStorage:
    """Read and write UTF-8 JSON files."""

    def __init__(self, file_path: str | Path):
        self.file_path = Path(file_path)

    def exists(self) -> bool:
        return self.file_path.is_file()

    def load(self, default: Any = None) -> Any:
        """Return default only for a missing file; malformed JSON is an error."""
        try:
            with self.file_path.open("r", encoding="utf-8") as json_file:
                return json.load(json_file)
        except FileNotFoundError:
            return default
        except json.JSONDecodeError as error:
            raise InvalidJsonFileError(self.file_path, error) from error

    def save(self, data: Any) -> None:
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path = None
        try:
            with NamedTemporaryFile(
                "w",
                encoding="utf-8",
                dir=self.file_path.parent,
                prefix=f".{self.file_path.name}.",
                suffix=".tmp",
                delete=False,
            ) as json_file:
                temporary_path = Path(json_file.name)
                json.dump(data, json_file, ensure_ascii=False, indent=2)
                json_file.write("\n")
            os.replace(temporary_path, self.file_path)
            temporary_path = None
        finally:
            if temporary_path is not None:
                try:
                    temporary_path.unlink()
                except FileNotFoundError:
                    pass

    def delete(self) -> bool:
        if self.file_path.exists():
            self.file_path.unlink()
            return True
        return False


class StorageManager:
    """Create shared JSON storage handles for repositories."""

    DEFAULT_TABLES = {f"Bàn {i}": "Trống" for i in range(1, 11)}

    def __init__(self, data_dir: str | Path | None = None):
        self.data_dir = (
            Path(data_dir)
            if data_dir is not None
            else Path(__file__).resolve().parents[2] / "data"
        )
        self.data_dir.mkdir(parents=True, exist_ok=True)

        seed_path = self.data_dir / "menu_seed.json"
        if not seed_path.exists():
            seed_path = Path(__file__).resolve().parents[2] / "data" / "menu_seed.json"
        self.menu_seed_storage = JsonStorage(seed_path)
        self.menu_storage = JsonStorage(self.data_dir / "menu.json")
        self.legacy_menu_storage = JsonStorage(self.data_dir / "menu_sample.json")
        self.users_storage = JsonStorage(self.data_dir / "users.json")
        self.orders_storage = JsonStorage(self.data_dir / "orders.json")
        self.tables_storage = JsonStorage(self.data_dir / "tables.json")
        self.invoices_storage = JsonStorage(self.data_dir / "invoices.json")
        self.payments_storage = JsonStorage(self.data_dir / "payments.json")
        self.kitchen_storage = JsonStorage(self.data_dir / "kitchen.json")
