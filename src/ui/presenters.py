"""Chuyển domain models thành dữ liệu ổn định cho các trang Streamlit."""
from typing import Any, Dict

from src.money import to_vnd


ORDER_STATUS_LABELS = {
    "IN_PROGRESS": "COOKING",
    "COMPLETED": "READY",
}


def menu_item_view(item: Any) -> Dict[str, Any]:
    if isinstance(item, dict):
        code = item.get("code") or item.get("item_id", "")
        return {
            "item_id": item.get("item_id") or code,
            "code": code,
            "name": item.get("name", ""),
            "price": item.get("price", 0),
            "is_active": item.get("is_active", True),
        }

    return {
        "item_id": item.code,
        "code": item.code,
        "name": item.name,
        "price": item.price,
        "is_active": item.is_active,
    }


def order_view(order: Any) -> Dict[str, Any]:
    if isinstance(order, dict):
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
        if isinstance(item, dict):
            code = item.get("code") or item.get("item_code") or item.get("item_id", "")
            name = item.get("name") or item.get("item_name", "")
            price = item.get("price", item.get("unit_price", 0))
            quantity = item.get("quantity", 0)
        else:
            code = item.item_code
            name = item.item_name
            price = item.unit_price
            quantity = item.quantity

        view_items.append({
            "code": code,
            "item_id": code,
            "name": name,
            "price": price,
            "quantity": quantity,
        })

    if total is None:
        total = sum(item["price"] * item["quantity"] for item in view_items)

    return {
        "id": order_id,
        "table": table,
        "status": ORDER_STATUS_LABELS.get(status, status),
        "created_at": getattr(order, "created_at", None) if not isinstance(order, dict) else order.get("created_at"),
        "items": view_items,
        "total": to_vnd(total),
    }


def order_views(orders: list[Any]) -> list[Dict[str, Any]]:
    return [order_view(order) for order in orders]