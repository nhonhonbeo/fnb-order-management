"""Dữ liệu phiên làm việc và các thao tác dùng chung cho giao diện."""
import json
from pathlib import Path
from uuid import uuid4

import streamlit as st

try:
    from src.core.services.auth_service import AuthService
except ImportError:
    from core.services.auth_service import AuthService


MENU_FILE = Path(__file__).resolve().parents[2] / "data" / "menu_sample.json"


def initialise_state():
    if "auth_service" not in st.session_state:
        st.session_state.auth_service = AuthService()

    st.session_state.setdefault("authenticated_user", None)

    if "menu" not in st.session_state:
        with MENU_FILE.open(encoding="utf-8") as file:
            st.session_state.menu = json.load(file)

    st.session_state.setdefault(
        "tables", {f"Bàn {number}": "Trống" for number in range(1, 11)}
    )
    st.session_state.setdefault("orders", [])
    st.session_state.setdefault("kitchen_queue", [])
    st.session_state.setdefault("invoices", [])


def login_user(user):
    """Lưu thông tin người dùng vào session state."""
    st.session_state.authenticated_user = user


def logout_user():
    """Đăng xuất người dùng và đặt lại trạng thái điều hướng."""
    st.session_state.authenticated_user = None
    st.session_state.current_page = "Quản lý bàn"


def get_current_user():
    """Lấy người dùng hiện tại đang đăng nhập."""
    return st.session_state.get("authenticated_user")


def currency(value):
    return f"{value:,.0f} đ".replace(",", ".")


def new_id(prefix):
    return f"{prefix}-{uuid4().hex[:6].upper()}"


def order_total(order):
    return sum(line["price"] * line["quantity"] for line in order["items"])


def status_label(status):
    return {"NEW": "Mới", "COOKING": "Đang nấu", "READY": "Đã phục vụ", "PAID": "Đã thanh toán"}.get(status, status)
