"""Khởi tạo backend services và dữ liệu phiên Streamlit."""
from __future__ import annotations

from pathlib import Path

import streamlit as st

from src.core.queues.order_queue import KitchenRequest, OrderQueue
from src.core.services.auth_service import AuthService
from src.core.services.billing_service import BillingService
from src.core.services.kitchen_service import KitchenService
from src.core.services.menu_service import MenuService
from src.core.services.order_service import OrderService
from src.core.services.payment_service import PaymentService
from src.core.storage import StorageManager
from src.ui.presenters import menu_item_view, order_views


DATA_DIR = Path(__file__).resolve().parents[2] / "data"


def initialise_state() -> None:
    """Khởi tạo services một lần và nạp dữ liệu phiên từ storage."""
    if "storage_manager" not in st.session_state:
        st.session_state.storage_manager = StorageManager(DATA_DIR)

    storage = st.session_state.storage_manager

    if "auth_service" not in st.session_state:
        st.session_state.auth_service = AuthService(storage.users_storage.file_path)

    if "menu_service" not in st.session_state:
        st.session_state.menu_service = MenuService(storage.menu_storage)

    if "order_queue" not in st.session_state:
        st.session_state.order_queue = OrderQueue()

    if "order_service" not in st.session_state:
        st.session_state.order_service = OrderService(
            menu=st.session_state.menu_service,
            queue=st.session_state.order_queue,
            storage_or_path=storage.orders_storage,
        )

    if "kitchen_service" not in st.session_state:
        st.session_state.kitchen_service = KitchenService(
            st.session_state.order_queue,
            storage.kitchen_storage,
            st.session_state.order_service,
        )
    else:
        st.session_state.kitchen_service.set_order_service(st.session_state.order_service)

    if "billing_service" not in st.session_state:
        st.session_state.billing_service = BillingService(storage.invoices_storage)

    if "payment_service" not in st.session_state:
        st.session_state.payment_service = PaymentService(
            order_service=st.session_state.order_service,
            storage_or_path=storage.payments_storage,
        )

    st.session_state.setdefault("authenticated_user", None)

    if "menu" not in st.session_state or not st.session_state.menu:
        st.session_state.menu = [
            menu_item_view(item)
            for item in st.session_state.menu_service.list_items(only_active=False)
        ]

    if "tables" not in st.session_state:
        st.session_state.tables = storage.load_tables()

    if "orders" not in st.session_state:
        st.session_state.orders = order_views(st.session_state.order_service.list_orders())

    if "invoices" not in st.session_state:
        st.session_state.invoices = st.session_state.billing_service.list_invoices()

    if "kitchen_queue_initialized" not in st.session_state:
        if not storage.kitchen_storage.exists():
            for order in st.session_state.order_service.list_orders():
                if order.status == "IN_PROGRESS":
                    for item in order.items:
                        st.session_state.kitchen_service.send_to_kitchen(KitchenRequest(
                            order_id=order.order_id,
                            item_code=item.item_code,
                            item_name=item.item_name,
                            quantity=item.quantity,
                        ))
        st.session_state.kitchen_queue_initialized = True