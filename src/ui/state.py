"""Dữ liệu phiên làm việc và kết nối giữa Frontend (Streamlit UI) và Backend Services."""
from __future__ import annotations

from typing import Any
from uuid import uuid4

import streamlit as st
from src.ui.presenters import menu_item_view
from src.money import to_vnd

def save_tables_state() -> None:
    """Lưu trạng thái sơ đồ bàn hiện tại vào storage."""
    st.session_state.storage_manager.save_tables(st.session_state.tables)


def sync_menu_state() -> None:
    """Đồng bộ danh sách thực đơn từ MenuService sang Session State."""
    st.session_state.menu = [
        menu_item_view(item)
        for item in st.session_state.menu_service.list_items(only_active=False)
    ]


def login_user(user: Any) -> None:
    """Lưu thông tin người dùng vào session state."""
    st.session_state.authenticated_user = user


def logout_user() -> None:
    """Đăng xuất người dùng và đặt lại trạng thái điều hướng."""
    st.session_state.authenticated_user = None
    st.session_state.current_page = "Quản lý bàn"


def get_current_user() -> Any:
    """Lấy người dùng hiện tại đang đăng nhập."""
    return st.session_state.get("authenticated_user")


def currency(value: Any) -> str:
    """Định dạng số tiền hiển thị theo chuẩn VND."""
    try:
        val = to_vnd(value)
        return f"{val:,.0f} đ".replace(",", ".")
    except (ValueError, TypeError):
        return f"{value} đ"


def new_id(prefix: str) -> str:
    """Tạo mã định danh ngẫu nhiên ngắn gọn."""
    return f"{prefix}-{uuid4().hex[:6].upper()}"


def order_total(order: Any) -> int:
    """Tính tổng tiền của một đơn hàng (hỗ trợ cả Order object và dict)."""
    if hasattr(order, "total"):
        return to_vnd(order.total())
    if isinstance(order, dict):
        if "total" in order and order["total"] is not None:
            return to_vnd(order["total"])
        items = order.get("items", [])
        return sum(to_vnd(line["price"]) * int(line["quantity"]) for line in items)
    return 0


def status_label(status: str) -> str:
    """Chuyển đổi mã trạng thái sang tiếng Việt dễ hiểu."""
    labels = {
        "NEW": "Mới",
        "IN_PROGRESS": "Đang nấu",
        "COOKING": "Đang nấu",
        "READY": "Đã phục vụ",
        "COMPLETED": "Đã phục vụ",
        "PAID": "Đã thanh toán",
        "CANCELLED": "Đã hủy",
    }
    return labels.get(status, status)
