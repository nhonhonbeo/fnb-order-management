"""Khởi tạo backend services và dữ liệu phiên Streamlit."""
from __future__ import annotations

from pathlib import Path

import streamlit as st

from src.features.kitchen.queue import KitchenRequest, OrderQueue
from src.features.kitchen.repository import KitchenRepository
from src.features.kitchen.service import KitchenService
from src.features.menu.repository import MenuRepository
from src.features.menu.service import MenuService
from src.features.orders.repository import OrderRepository
from src.features.orders.service import OrderService
from src.features.payments.billing_service import BillingService
from src.features.payments.invoice_repository import InvoiceRepository
from src.features.payments.payment_repository import PaymentRepository
from src.features.payments.service import PaymentService
from src.reports.service import ReportingService
from src.features.storage.json_storage import StorageManager
from src.features.tables.repository import TableRepository
from src.features.tables.service import TableService
from src.users.repository import UserRepository
from src.users.service import AuthService
from src.ui.presenters import menu_item_view, order_views


DATA_DIR = Path(__file__).resolve().parents[2] / "data"


def initialise_state() -> None:
    """Khởi tạo services một lần và nạp dữ liệu phiên từ storage."""
    if "storage_manager" not in st.session_state:
        st.session_state.storage_manager = StorageManager(DATA_DIR)

    storage = st.session_state.storage_manager

    if "table_service" not in st.session_state:
        st.session_state.table_repository = TableRepository(storage.tables_storage)
        st.session_state.table_service = TableService(st.session_state.table_repository)

    if "auth_service" not in st.session_state:
        st.session_state.user_repository = UserRepository(storage.users_storage)
        st.session_state.auth_service = AuthService(st.session_state.user_repository)

    if "menu_service" not in st.session_state:
        st.session_state.menu_repository = MenuRepository(
            storage.menu_storage,
            seed_storage=storage.menu_seed_storage,
            legacy_storage=storage.legacy_menu_storage,
        )
        st.session_state.menu_service = MenuService(st.session_state.menu_repository)

    if "order_queue" not in st.session_state:
        st.session_state.order_queue = OrderQueue()

    if "order_service" not in st.session_state:
        st.session_state.order_repository = OrderRepository(storage.orders_storage)
        st.session_state.order_service = OrderService(
            menu=st.session_state.menu_service,
            queue=st.session_state.order_queue,
            storage_or_path=st.session_state.order_repository,
            table_service=st.session_state.table_service,
        )

    st.session_state.table_service.set_orders_provider(
        st.session_state.order_service.list_orders
    )

    st.session_state.menu_service.set_order_service(st.session_state.order_service)

    if "kitchen_service" not in st.session_state:
        st.session_state.kitchen_repository = KitchenRepository(storage.kitchen_storage)
        st.session_state.kitchen_service = KitchenService(
            st.session_state.order_queue,
            st.session_state.kitchen_repository,
            st.session_state.order_service,
        )
    else:
        st.session_state.kitchen_service.set_order_service(st.session_state.order_service)
    st.session_state.order_service.set_kitchen_service(
        st.session_state.kitchen_service
    )

    if "billing_service" not in st.session_state:
        st.session_state.invoice_repository = InvoiceRepository(storage.invoices_storage)
        st.session_state.billing_service = BillingService(
            st.session_state.invoice_repository
        )

    if "reporting_service" not in st.session_state:
        st.session_state.reporting_service = ReportingService()

    if "payment_service" not in st.session_state:
        st.session_state.payment_repository = PaymentRepository(storage.payments_storage)
        st.session_state.payment_service = PaymentService(
            order_service=st.session_state.order_service,
            storage_or_path=st.session_state.payment_repository,
            billing_service=st.session_state.billing_service,
            table_service=st.session_state.table_service,
            kitchen_service=st.session_state.kitchen_service,
        )

    st.session_state.setdefault("authenticated_user", None)

    if "menu" not in st.session_state or not st.session_state.menu:
        st.session_state.menu = [
            menu_item_view(item)
            for item in st.session_state.menu_service.list_items(only_active=False)
        ]

    st.session_state.tables = st.session_state.table_service.list_tables()

    if "orders" not in st.session_state:
        st.session_state.orders = order_views(st.session_state.order_service.list_orders())

    if "invoices" not in st.session_state:
        st.session_state.invoices = st.session_state.billing_service.list_invoices()

    if "kitchen_queue_initialized" not in st.session_state:
        if not st.session_state.kitchen_repository.exists():
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