"""Đọc và ghi dữ liệu JSON cho ứng dụng."""
import json
from pathlib import Path
from typing import Any


class JsonStorage:
    def __init__(self, file_path: str | Path):
        self.file_path = Path(file_path)

    def load(self, default: Any = None) -> Any:
        try:
            with self.file_path.open("r", encoding="utf-8") as json_file:
                return json.load(json_file)
        except FileNotFoundError:
            return default

    def save(self, data: Any) -> None:
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        with self.file_path.open("w", encoding="utf-8") as json_file:
            json.dump(data, json_file, ensure_ascii=False, indent=2)
            json_file.write("\n")
