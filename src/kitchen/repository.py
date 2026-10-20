"""Persistence and mapping for kitchen requests and their FIFO order."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from src.kitchen.queue import KitchenRequest
from src.shared.repository import RepositoryDataError
from src.storage.json_storage import JsonStorage


class KitchenRepository:
    """Persist kitchen progress and queue references in the existing JSON shape."""

    def __init__(self, storage_or_path: Any = None):
        default_path = Path(__file__).resolve().parents[2] / "data" / "kitchen.json"
        if storage_or_path is None:
            self.storage = JsonStorage(default_path)
        elif isinstance(storage_or_path, JsonStorage):
            self.storage = storage_or_path
        elif isinstance(storage_or_path, (str, Path)):
            self.storage = JsonStorage(storage_or_path)
        else:
            raise TypeError("KitchenRepository requires a path or JSON storage object")

    def exists(self) -> bool:
        return self.storage.exists()

    def load_state(self) -> tuple[list[KitchenRequest], list[tuple[str, str]]]:
        data = self.storage.load(default={})
        if isinstance(data, list):
            raw_requests = data
            raw_queue = None
        elif isinstance(data, dict):
            raw_requests = data.get("requests", [])
            raw_queue = data.get("queue")
            if not isinstance(raw_requests, list):
                raise RepositoryDataError(
                    f"Kitchen requests in '{self.storage.file_path}' must be a JSON array"
                )
        else:
            raise RepositoryDataError(
                f"Kitchen data in '{self.storage.file_path}' must be an object or legacy array"
            )

        requests = []
        by_key = {}
        for index, item in enumerate(raw_requests):
            if not isinstance(item, dict):
                raise RepositoryDataError(
                    f"Kitchen request {index} in '{self.storage.file_path}' must be an object"
                )
            required = ("order_id", "item_code", "item_name", "quantity")
            missing = [key for key in required if key not in item or item[key] in ("", None)]
            if missing:
                raise RepositoryDataError(
                    f"Kitchen request {index} in '{self.storage.file_path}' is missing "
                    f"required field(s): {', '.join(missing)}"
                )
            if any(
                not isinstance(item[key], str)
                for key in ("order_id", "item_code", "item_name")
            ):
                raise RepositoryDataError(
                    f"Kitchen request {index} in '{self.storage.file_path}' "
                    "requires string identifiers and item_name"
                )
            if (
                isinstance(item["quantity"], bool)
                or not isinstance(item["quantity"], int)
                or item["quantity"] <= 0
            ):
                raise RepositoryDataError(
                    f"Kitchen request {index} in '{self.storage.file_path}' "
                    "requires a positive integer quantity"
                )
            if item.get("status", "NEW") not in {"NEW", "COOKING", "READY", "DONE"}:
                raise RepositoryDataError(
                    f"Kitchen request {index} in '{self.storage.file_path}' "
                    "has an invalid status"
                )
            try:
                request = KitchenRequest(
                    order_id=item["order_id"],
                    item_code=item["item_code"],
                    item_name=item["item_name"],
                    quantity=item["quantity"],
                    status=str(item.get("status", "NEW")),
                )
            except (TypeError, ValueError) as error:
                raise RepositoryDataError(
                    f"Invalid kitchen request {index} in '{self.storage.file_path}': {error}"
                ) from error
            requests.append(request)
            by_key[(request.order_id, request.item_code)] = request

        if raw_queue is None:
            queue_keys = [
                (request.order_id, request.item_code)
                for request in requests
                if request.status not in {"READY", "DONE"}
            ]
        else:
            if not isinstance(raw_queue, list):
                raise RepositoryDataError(
                    f"Kitchen queue in '{self.storage.file_path}' must be a JSON array"
                )
            queue_keys = []
            for index, item in enumerate(raw_queue):
                if not isinstance(item, dict) or not item.get("order_id") or not item.get("item_code"):
                    raise RepositoryDataError(
                        f"Kitchen queue entry {index} in '{self.storage.file_path}' "
                        "requires order_id and item_code"
                    )
                if not isinstance(item["order_id"], str) or not isinstance(item["item_code"], str):
                    raise RepositoryDataError(
                        f"Kitchen queue entry {index} in '{self.storage.file_path}' "
                        "requires string order_id and item_code fields"
                    )
                key = (item["order_id"], item["item_code"])
                if key in queue_keys:
                    raise RepositoryDataError(
                        f"Kitchen queue in '{self.storage.file_path}' contains "
                        f"duplicate request {key}"
                    )
                if key not in by_key:
                    raise RepositoryDataError(
                        f"Kitchen queue entry {index} references missing request {key}"
                    )
                queue_keys.append(key)
        return requests, queue_keys

    def save_state(
        self,
        requests: list[KitchenRequest],
        queue: list[KitchenRequest],
    ) -> None:
        self.storage.save({
            "requests": [
                {
                    "order_id": request.order_id,
                    "item_code": request.item_code,
                    "item_name": request.item_name,
                    "quantity": request.quantity,
                    "status": request.status,
                }
                for request in requests
            ],
            "queue": [
                {"order_id": request.order_id, "item_code": request.item_code}
                for request in queue
            ],
        })
