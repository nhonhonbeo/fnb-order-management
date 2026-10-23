"""Chuyển domain models thành dữ liệu ổn định cho các trang Streamlit."""
from collections.abc import Mapping
from typing import Any

from src.features.payments.billing_service import BillingService
from src.shared.data_structures.hash_map import HashMap
from src.shared.money import to_vnd


def _make_hash_map(*entries: tuple[str, Any]) -> HashMap:
    result = HashMap()
    for key, value in entries:
        result.put(key, value)
    return result


ORDER_STATUS_LABELS = _make_hash_map(
    ("IN_PROGRESS", "COOKING"),
    ("COMPLETED", "READY"),
)


def menu_item_view(item: Any) -> HashMap:
    if isinstance(item, Mapping):
        code = item.get("code") or item.get("item_id", "")
        return _make_hash_map(
            ("item_id", item.get("item_id") or code),
            ("code", code),
            ("name", item.get("name", "")),
            ("price", item.get("price", 0)),
            ("is_active", item.get("is_active", True)),
        )

    return _make_hash_map(
        ("item_id", item.code),
        ("code", item.code),
        ("name", item.name),
        ("price", item.price),
        ("is_active", item.is_active),
    )


def order_view(order: Any) -> HashMap:
    if isinstance(order, Mapping):
        order_id = order.get("id") or order.get("order_id", "")
        table = order.get("table") or order.get("table_id", "")
        status = order.get("status", "NEW")
        items = order.get("items", [])
        total = order.get("total")
    else:
        order_id = order.order_id
        table = order.table_id or ""
        status = order.status
        items = order.items
        total = order.total()

    view_items = []
    for item in items:
        if isinstance(item, Mapping):
            code = item.get("code") or item.get("item_code") or item.get("item_id", "")
            name = item.get("name") or item.get("item_name", "")
            price = item.get("price", item.get("unit_price", 0))
            quantity = item.get("quantity", 0)
        else:
            code = item.item_code
            name = item.item_name
            price = item.unit_price
            quantity = item.quantity

        view_items.append(_make_hash_map(
            ("code", code),
            ("item_id", code),
            ("name", name),
            ("price", price),
            ("quantity", quantity),
        ))

    if total is None:
        total = BillingService.calculate_total(view_items)

    return _make_hash_map(
        ("id", order_id),
        ("table", table),
        ("status", ORDER_STATUS_LABELS.get(status, status)),
        (
            "created_at",
            order.get("created_at") if isinstance(order, Mapping)
            else getattr(order, "created_at", None),
        ),
        (
            "note",
            order.get("note", "") if isinstance(order, Mapping)
            else getattr(order, "note", ""),
        ),
        (
            "cancelled_at",
            order.get("cancelled_at") if isinstance(order, Mapping)
            else getattr(order, "cancelled_at", None),
        ),
        (
            "cancel_reason",
            order.get("cancel_reason") if isinstance(order, Mapping)
            else getattr(order, "cancel_reason", None),
        ),
        ("items", view_items),
        ("total", to_vnd(total)),
    )


def order_views(orders: list[Any]) -> list[HashMap]:
    return [order_view(order) for order in orders]