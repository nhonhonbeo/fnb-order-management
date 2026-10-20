"""UI permission checks for authenticated users."""
from __future__ import annotations

from typing import Any


def can_manage_menu(user: Any) -> bool:
    return user is not None and getattr(user, "role", None) == "Quản lý"


def can_view_revenue(user: Any) -> bool:
    return user is not None and getattr(user, "role", None) in {"Quản lý", "Thu ngân"}
