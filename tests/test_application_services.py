from datetime import datetime

import pytest

from src.kitchen.queue import OrderQueue
from src.kitchen.service import KitchenService
from src.menu.service import MenuService
from src.orders.service import OrderService
from src.payments.billing_service import BillingService
from src.payments.service import PaymentError, PaymentService
from src.reports.service import ReportingService
from src.storage.json_storage import StorageManager
from src.tables.repository import TableRepository
from src.tables.service import TableService
from src.users.permissions import can_manage_menu, can_view_revenue


def test_menu_service_search_edit_toggle_and_safe_remove(tmp_path):
    menu = MenuService(tmp_path / "menu.json")
    menu.add_item("F001", "Phở bò", 45000)
    menu.add_item("F002", "Bánh mì", 25000)

    assert [item.code for item in menu.search("PHỞ")] == ["F001"]
    updated = menu.update_item("F001", name="Phở đặc biệt", price=50000)
    assert (updated.name, updated.price) == ("Phở đặc biệt", 50000)
    assert menu.toggle_status("F001").is_active is False
    assert menu.toggle_status("F001").is_active is True

    orders = OrderService(menu=menu, storage_or_path=tmp_path / "orders.json")
    menu.set_order_service(orders)
    order = orders.create_order()
    orders.add_item(order.order_id, "F001", 1)

    assert menu.remove_item("F001") is True
    assert menu.get_item("F001") is updated
    assert updated.is_active is False
    assert menu.remove_item("F002") is True
    assert menu.get_item("F002") is None

    restored = MenuService(tmp_path / "menu.json")
    assert restored.get_item("F001").is_active is False
    assert restored.get_item("F002") is None


def test_order_service_validates_cart_and_places_order(tmp_path):
    storage = StorageManager(tmp_path / "data")
    tables = TableService(TableRepository(storage.tables_storage))
    menu = MenuService(tmp_path / "menu" / "menu.json")
    menu.add_item("F001", "Phở bò", 45000)
    queue = OrderQueue()
    orders = OrderService(
        menu=menu,
        queue=queue,
        storage_or_path=storage.orders_storage,
        table_service=tables,
    )
    menu.set_order_service(orders)

    cart = []
    orders.add_to_cart(cart, "F001", 2)
    orders.add_to_cart(cart, "F001", 1)
    assert len(cart) == 1
    assert cart[0]["quantity"] == 3
    assert orders.calculate_cart_total(cart) == 135000

    with pytest.raises(ValueError, match="Số lượng"):
        orders.add_to_cart(cart, "F001", True)
    with pytest.raises(ValueError, match="Không tìm thấy món ăn"):
        orders.add_to_cart(cart, "F999", 1)

    order = orders.create_order_from_cart("Bàn 1", cart)
    assert order.total() == 135000
    assert order.status == "IN_PROGRESS"
    assert queue.size() == 1
    assert tables.is_available("Bàn 1") is False
    assert tables.repository.find_by_id("Bàn 1") == "Đang phục vụ"

    with pytest.raises(ValueError, match="Bàn không tồn tại hoặc đang được phục vụ"):
        orders.create_order_from_cart("Bàn 1", cart)
    assert len(orders.list_orders()) == 1


def test_payment_checkout_coordinates_invoice_table_and_kitchen(tmp_path):
    storage = StorageManager(tmp_path / "data")
    tables = TableService(TableRepository(storage.tables_storage))
    menu = MenuService(tmp_path / "menu" / "menu.json")
    menu.add_item("F001", "Phở bò", 45000)
    queue = OrderQueue()
    orders = OrderService(
        menu=menu,
        queue=queue,
        storage_or_path=storage.orders_storage,
        table_service=tables,
    )
    kitchen = KitchenService(queue, storage.kitchen_storage, orders)
    billing = BillingService(storage.invoices_storage)
    payments = PaymentService(
        orders,
        storage.payments_storage,
        billing_service=billing,
        table_service=tables,
        kitchen_service=kitchen,
    )

    order = orders.create_order_from_cart(
        "Bàn 1",
        [{"code": "F001", "quantity": 2}],
    )
    request = kitchen.current()
    kitchen.start(order.order_id, request.item_code)
    kitchen.complete(order.order_id, request.item_code)

    payment, invoice = payments.checkout(order.order_id)

    assert payment.order_id == order.order_id
    assert invoice.order_id == order.order_id
    assert invoice.payment_id == payment.payment_id
    assert order.status == "PAID"
    assert tables.is_available("Bàn 1")
    assert kitchen._requests[(order.order_id, "F001")].status == "DONE"

    with pytest.raises(PaymentError, match="Đơn đã thanh toán"):
        payments.checkout(order.order_id)


def test_checkout_invoice_failure_rolls_back_payment_and_keeps_workflow_state(tmp_path, monkeypatch):
    storage = StorageManager(tmp_path / "data")
    tables = TableService(TableRepository(storage.tables_storage))
    menu = MenuService(tmp_path / "menu.json")
    menu.add_item("F001", "Phở bò", 45000)
    queue = OrderQueue()
    orders = OrderService(menu, queue, storage.orders_storage, tables)
    kitchen = KitchenService(queue, storage.kitchen_storage, orders)
    billing = BillingService(storage.invoices_storage)
    payments = PaymentService(
        orders,
        storage.payments_storage,
        billing_service=billing,
        table_service=tables,
        kitchen_service=kitchen,
    )
    order = orders.create_order_from_cart(
        "Bàn 1",
        [{"code": "F001", "quantity": 1}],
    )
    request = kitchen.current()
    kitchen.start(order.order_id, request.item_code)
    kitchen.complete(order.order_id, request.item_code)
    assert order.status == "COMPLETED"

    def fail_invoice(*_args, **_kwargs):
        raise OSError("invoice file is not writable")

    monkeypatch.setattr(billing, "create_invoice", fail_invoice)
    with pytest.raises(OSError, match="invoice file is not writable"):
        payments.checkout(order.order_id)

    assert order.status == "COMPLETED"
    assert tables.repository.find_by_id("Bàn 1") == "Đang phục vụ"
    assert kitchen._requests[(order.order_id, "F001")].status == "READY"
    assert payments.list_payments() == []
    assert billing.list_invoices() == []
    assert PaymentService(orders, storage.payments_storage).list_payments() == []
    assert BillingService(storage.invoices_storage).get_total_revenue() == 0


@pytest.mark.parametrize("failure_stage", ["table", "kitchen"])
def test_checkout_downstream_failure_restores_all_related_state(
    tmp_path,
    monkeypatch,
    failure_stage,
):
    storage = StorageManager(tmp_path / "data")
    tables = TableService(TableRepository(storage.tables_storage))
    menu = MenuService(tmp_path / "menu.json")
    menu.add_item("F001", "Phở bò", 45000)
    queue = OrderQueue()
    orders = OrderService(menu, queue, storage.orders_storage, tables)
    kitchen = KitchenService(queue, storage.kitchen_storage, orders)
    billing = BillingService(storage.invoices_storage)
    payments = PaymentService(
        orders,
        storage.payments_storage,
        billing_service=billing,
        table_service=tables,
        kitchen_service=kitchen,
    )
    order = orders.create_order_from_cart(
        "Bàn 1",
        [{"code": "F001", "quantity": 1}],
    )
    request = kitchen.current()
    kitchen.start(order.order_id, request.item_code)
    kitchen.complete(order.order_id, request.item_code)

    def fail(*_args, **_kwargs):
        raise OSError(f"{failure_stage} update failed")

    target = tables if failure_stage == "table" else kitchen
    method = "release" if failure_stage == "table" else "mark_order_done"
    monkeypatch.setattr(target, method, fail)
    with pytest.raises(OSError, match=f"{failure_stage} update failed"):
        payments.checkout(order.order_id)

    assert order.status == "COMPLETED"
    assert tables.repository.find_by_id("Bàn 1") == "Đang phục vụ"
    assert kitchen._requests[(order.order_id, "F001")].status == "READY"
    assert queue.is_empty()
    assert payments.list_payments() == []
    assert billing.list_invoices() == []
    assert PaymentService(orders, storage.payments_storage).list_payments() == []
    assert BillingService(storage.invoices_storage).get_total_revenue() == 0


def test_invoice_rejects_inconsistent_order_total_and_preserves_revenue(tmp_path):
    billing = BillingService(tmp_path / "invoices.json")
    order = {
        "order_id": "DH001",
        "total": 99999,
        "items": [{"price": 45000, "quantity": 2}],
    }

    with pytest.raises(ValueError, match="không khớp"):
        billing.create_invoice(order, payment_id="TT001")

    assert billing.list_invoices() == []
    assert billing.get_total_revenue() == 0
    assert not (tmp_path / "invoices.json").exists()


def test_reporting_service_calculates_dashboard_data_without_streamlit():
    service = ReportingService()
    now = datetime(2026, 10, 20, 12, 30)
    orders = [{
        "id": "DH001",
        "table": "Bàn 1",
        "status": "IN_PROGRESS",
        "created_at": "2026-10-20T12:00:00",
        "total": 90000,
        "items": [{"name": "Phở bò", "quantity": 2, "price": 45000}],
    }]

    tables = service.table_statuses({"Bàn 1": "Đang phục vụ"}, orders, now=now)
    assert tables[0]["status"] == "Đang phục vụ"
    assert tables[0]["seated_time"] == "30 phút"
    assert tables[0]["total"] == 90000
    assert service.best_sellers(orders) == [("Phở bò", 2)]
    assert service.hourly_revenue(orders)["12:00"] == 90000

    class Request:
        order_id = "DH001"
        status = "NEW"

    assert service.dashboard_alerts(orders, [Request()], now=now) == [
        "2 món đang chờ bếp quá 15 phút."
    ]


def test_ui_permissions_deny_unknown_and_unauthenticated_users():
    class User:
        def __init__(self, role):
            self.role = role

    assert can_manage_menu(User("Quản lý"))
    assert not can_manage_menu(User("Nhân viên"))
    assert not can_manage_menu(None)
    assert can_view_revenue(User("Thu ngân"))
    assert not can_view_revenue(User("Đầu bếp"))
    assert not can_view_revenue(None)
