"""Shared JSON-backed repository operations for list-shaped entities."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Generic, Iterable, TypeVar

from src.features.storage.json_storage import JsonStorage


Entity = TypeVar("Entity")


class RepositoryDataError(ValueError):
    """Raised when valid JSON does not match an entity repository's schema."""


def as_json_storage(source: Any, default_path: Path) -> JsonStorage:
    if source is None:
        return JsonStorage(default_path)
    if isinstance(source, JsonStorage):
        return source
    if isinstance(source, (str, Path)):
        return JsonStorage(source)
    if hasattr(source, "load") and hasattr(source, "save"):
        return source
    raise TypeError("Repository requires a path or JSON storage object")


class JsonListRepository(Generic[Entity]):
    """Reusable persistence and CRUD operations for JSON arrays."""

    entity_name = "Entity"
    identifier_fields: tuple[str, ...] = ("id",)
    required_fields: tuple[str, ...] = ()

    def __init__(self, storage: JsonStorage):
        self.storage = storage

    def identifier(self, entity: Entity) -> str:
        for field in self.identifier_fields:
            value = getattr(entity, field, None)
            if value:
                return str(value)
        raise RepositoryDataError(f"{self.entity_name} has no identifier")

    def validate_record(self, record: Any, index: int) -> dict[str, Any]:
        path = self.storage.file_path
        if not isinstance(record, dict):
            raise RepositoryDataError(
                f"{self.entity_name} record {index} in '{path}' must be an object"
            )
        missing = [
            field for field in self.required_fields
            if field not in record or record[field] in ("", None)
        ]
        if missing:
            raise RepositoryDataError(
                f"{self.entity_name} record {index} in '{path}' is missing "
                f"required field(s): {', '.join(missing)}"
            )
        return record

    def deserialize(self, record: dict[str, Any]) -> Entity:
        raise NotImplementedError

    def serialize(self, entity: Entity) -> dict[str, Any]:
        serializer = getattr(entity, "to_dict", None)
        if serializer is None:
            raise TypeError(f"{self.entity_name} must provide to_dict()")
        return serializer()

    def list_all(self) -> list[Entity]:
        raw_data = self.storage.load(default=[])
        if not isinstance(raw_data, list):
            raise RepositoryDataError(
                f"{self.entity_name} data in '{self.storage.file_path}' must be a JSON array"
            )
        return [
            self.deserialize(self.validate_record(record, index))
            for index, record in enumerate(raw_data)
        ]

    def save_all(self, entities: Iterable[Entity]) -> None:
        self.storage.save([self.serialize(entity) for entity in entities])

    def find_by_id(self, identifier: str) -> Entity | None:
        return next(
            (entity for entity in self.list_all()
             if self.identifier(entity) == str(identifier)),
            None,
        )

    def add(self, entity: Entity) -> Entity:
        identifier = self.identifier(entity)
        entities = self.list_all()
        if any(self.identifier(existing) == identifier for existing in entities):
            raise RepositoryDataError(
                f"{self.entity_name} '{identifier}' already exists"
            )
        entities.append(entity)
        self.save_all(entities)
        return entity

    def update(self, entity: Entity) -> Entity:
        identifier = self.identifier(entity)
        entities = self.list_all()
        for index, existing in enumerate(entities):
            if self.identifier(existing) == identifier:
                entities[index] = entity
                self.save_all(entities)
                return entity
        raise RepositoryDataError(f"{self.entity_name} '{identifier}' was not found")

    def delete(self, identifier: str) -> bool:
        entities = self.list_all()
        remaining = [
            entity for entity in entities
            if self.identifier(entity) != str(identifier)
        ]
        if len(remaining) == len(entities):
            return False
        self.save_all(remaining)
        return True

    def search(self, field: str, keyword: str) -> list[Entity]:
        normalized = keyword.casefold()
        return [
            entity for entity in self.list_all()
            if normalized in str(getattr(entity, field, "")).casefold()
        ]
