"""Dữ liệu phiên làm việc và kết nối giữa Frontend (Streamlit UI) và Backend Services."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

import streamlit as st

try:
    from src.core.order_queue import OrderQueue
    from src.core.payment_service import PaymentService
    from src.core.services.auth_service import AuthService
    from src.core.services.billing_service import BillingService
    from src.core.services.kitchen_service import KitchenService
    from src.core.services.menu_service import MenuService
    from src.core.services.order_service import OrderService
    from src.core.storage import StorageManager
    from src.models.menu_item import MenuItem
    from src.models.order import Order
except ImportError:
    from core.order_queue import OrderQueue
    from core.payment_service import PaymentService
    from core.services.auth_service import AuthService
    from core.services.billing_service import BillingService
    from core.services.kitchen_service import KitchenService
    from core.services.menu_service import MenuService
    from core.services.order_service import OrderService
    from core.storage import StorageManager
    from models.menu_item import MenuItem
    from models.order import Order


DATA_DIR = Path(__file__).resolve().parents[2] / "data"


def initialise_state() -> None:
    """Khởi tạo toàn bộ dịch vụ backend, nạp dữ liệu từ Storage và liên kết với Session State."""
    # 1. Quản lý lưu trữ tập trung
    if "storage_manager" not in st.session_state:
        st.session_state.storage_manager = StorageManager(DATA_DIR)

    storage = st.session_state.storage_manager

    # 2. Khởi tạo các Backend Services
    if "auth_service" not in st.session_state:
        st.session_state.auth_service = AuthService(storage.users_storage.file_path)

    if "menu_service" not in st.session_state:
        st.session_state.menu_service = MenuService(storage.menu_storage)

    if "order_queue" not in st.session_state:
        st.session_state.order_queue = OrderQueue()

    if "kitchen_service" not in st.session_state:
        st.session_state.kitchen_service = KitchenService(st.session_state.order_queue)

    if "order_service" not in st.session_state:
        st.session_state.order_service = OrderService(
            menu=st.session_state.menu_service,
            queue=st.session_state.order_queue,
            storage_or_path=storage.orders_storage,
        )

    if "billing_service" not in st.session_state:
        st.session_state.billing_service = BillingService(storage.invoices_storage)

    if "payment_service" not in st.session_state:
        st.session_state.payment_service = PaymentService(
            order_service=st.session_state.order_service,
            storage_or_path=storage.payments_storage,
        )

    st.session_state.setdefault("authenticated_user", None)

    # 3. Đồng bộ dữ liệu hiển thị trên giao diện từ Backend
    # Thực đơn
    if "menu" not in st.session_state or not st.session_state.menu:
        st.session_state.menu = st.session_state.menu_service.list_items(only_active=False)

    # Sơ đồ bàn (Đọc từ storage hoặc mặc định 10 bàn)
    if "tables" not in st.session_state:
        st.session_state.tables = storage.load_tables()

    # Danh sách đơn hàng
    if "orders" not in st.session_state:
        st.session_state.orders = st.session_state.order_service.list_orders()

    # Hóa đơn thanh toán
    if "invoices" not in st.session_state:
        st.session_state.invoices = st.session_state.billing_service.list_invoices()

    # Hàng đợi bếp
    if "kitchen_queue" not in st.session_state:
        st.session_state.kitchen_queue = []
        # Tái hiện các món chưa hoàn tất chế biến từ các đơn hàng hiện có
        for order in st.session_state.orders:
            if order["status"] in ("NEW", "IN_PROGRESS", "COOKING"):
                item_status = "COOKING" if order["status"] == "COOKING" else "NEW"
                for item in order["items"]:
                    st.session_state.kitchen_queue.append({
                        "order_id": order["id"],
                        "table": order["table"],
                        "name": item["name"],
                        "item_code": item.get("code") or item.get("item_id"),
                        "quantity": item["quantity"],
                        "price": item["price"],
                        "status": item_status,
                    })


def save_tables_state() -> None:
    """Lưu trạng thái sơ đồ bàn hiện tại vào storage."""
    storage: StorageManager = st.session_state.storage_manager
    storage.save_tables(st.session_state.tables)


def sync_menu_state() -> None:
    """Đồng bộ danh sách thực đơn từ MenuService sang Session State."""
    st.session_state.menu = st.session_state.menu_service.list_items(only_active=False)


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
        val = float(value)
        return f"{val:,.0f} đ".replace(",", ".")
    except (ValueError, TypeError):
        return f"{value} đ"


def new_id(prefix: str) -> str:
    """Tạo mã định danh ngẫu nhiên ngắn gọn."""
    return f"{prefix}-{uuid4().hex[:6].upper()}"


def order_total(order: Any) -> float:
    """Tính tổng tiền của một đơn hàng (hỗ trợ cả Order object và dict)."""
    if hasattr(order, "total"):
        return float(order.total())
    if isinstance(order, dict):
        if "total" in order and order["total"] is not None:
            return float(order["total"])
        items = order.get("items", [])
        return float(sum(line["price"] * line["quantity"] for line in items))
    return 0.0


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
