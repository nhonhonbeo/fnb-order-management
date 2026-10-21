"""UI permission checks for authenticated users."""
from __future__ import annotations

from typing import Any


def can_manage_menu(user: Any) -> bool:
    return user is not None and getattr(user, "role", None) == "Quản lý"


def can_manage_tables(user: Any) -> bool:
    return user is not None and getattr(user, "role", None) == "Quản lý"


def can_view_revenue(user: Any) -> bool:
    return user is not None and getattr(user, "role", None) in {"Quản lý", "Thu ngân"}


def can_edit_order(user: Any, order: Any) -> bool:
    return (
        user is not None
        and getattr(user, "role", None) in {"Quản lý", "Nhân viên"}
        and getattr(order, "status", None) not in {"PAID", "CANCELLED"}
    )


def can_cancel_order(user: Any, order: Any) -> bool:
    if user is None or getattr(order, "status", None) in {"PAID", "CANCELLED"}:
        return False
    role = getattr(user, "role", None)
    if getattr(order, "status", None) == "NEW":
        return role in {"Quản lý", "Nhân viên"}
    return role == "Quản lý"
