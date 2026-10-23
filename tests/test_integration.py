"""Kiểm thử tích hợp toàn bộ hệ thống F&B từ Storage, Model, Services đến luồng nghiệp vụ."""
from src.features.kitchen.queue import OrderQueue
from src.features.kitchen.repository import KitchenRepository
from src.features.kitchen.service import KitchenService
from src.features.menu.repository import MenuRepository
from src.features.menu.service import MenuService
from src.features.orders.repository import OrderRepository
from src.features.orders.service import OrderService
from src.features.payments.billing_service import BillingService
from src.features.payments.payment import PaymentStatus
from src.features.payments.service import PaymentService
from src.features.storage.json_storage import StorageManager
from src.features.tables.repository import TableRepository
from src.features.tables.service import TableService


def test_full_fnb_order_and_payment_flow(tmp_path):
    data_dir = tmp_path / "data"
    storage_manager = StorageManager(data_dir=data_dir)

    # 1. Khởi tạo Backend Services
    menu_repository = MenuRepository(
        storage_manager.menu_storage,
        seed_storage=storage_manager.menu_seed_storage,
        legacy_storage=storage_manager.legacy_menu_storage,
    )
    menu_service = MenuService(storage_or_path=menu_repository)
    order_queue = OrderQueue()
    order_service = OrderService(
        menu=menu_service,
        queue=order_queue,
        storage_or_path=storage_manager.orders_storage,
    )
    kitchen_service = KitchenService(
        kitchen_queue=order_queue,
        storage_or_path=storage_manager.kitchen_storage,
        order_service=order_service,
    )
    billing_service = BillingService(storage_or_path=storage_manager.invoices_storage)
    payment_service = PaymentService(
        order_service=order_service,
        storage_or_path=storage_manager.payments_storage,
    )

    # 2. Thêm món vào thực đơn và kiểm tra lưu trữ
    assert len(menu_service.list_items()) == 3

    # 3. Tạo đơn hàng gắn với Bàn 1
    table_service = TableService(TableRepository(storage_manager.tables_storage))
    tables = table_service.list_tables()
    assert tables["Bàn 1"] == "Trống"

    order = order_service.create_order(table_id="Bàn 1")
    order_service.add_item(order.order_id, "F001", quantity=2)
    order_service.add_item(order.order_id, "F002", quantity=1)
    table_service.reserve("Bàn 1")

    expected_total = 2 * 45000 + 1 * 25000  # 115000
    assert order.total() == expected_total

    # 4. Gửi đơn xuống bếp qua hàng đợi FIFO
    order_service.send_to_kitchen(order.order_id)
    assert order.status == "IN_PROGRESS"
    assert kitchen_service.size() == 2

    # Bếp chế biến món lần lượt theo FIFO
    req1 = kitchen_service.current()
    assert req1.item_code == "F001"
    assert req1.quantity == 2
    kitchen_service.start(order.order_id, req1.item_code)
    kitchen_service.complete(order.order_id, req1.item_code)

    req2 = kitchen_service.current()
    assert req2.item_code == "F002"
    assert req2.quantity == 1
    kitchen_service.start(order.order_id, req2.item_code)
    kitchen_service.complete(order.order_id, req2.item_code)

    # 5. Bếp tự hoàn thành đơn khi mọi món đã sẵn sàng
    assert order.status == "COMPLETED"
    assert kitchen_service.is_empty() is True

    # 6. Thu ngân thực hiện thanh toán
    payment = payment_service.pay(order.order_id, amount=expected_total)
    assert payment.status == PaymentStatus.SUCCESS
    assert order.status == "PAID"

    # 7. Xuất hóa đơn
    invoice = billing_service.create_invoice(order=order, payment_id=payment.payment_id)
    assert invoice.total == expected_total
    assert billing_service.get_total_revenue() == expected_total

    # 8. Mở lại bàn trống
    table_service.release("Bàn 1")

    # 9. Kiểm tra tính bền vững (Persistence) sau khi nạp lại từ Storage
    reloaded_storage = StorageManager(data_dir=data_dir)
    reloaded_menu = MenuService(
        storage_or_path=MenuRepository(
            reloaded_storage.menu_storage,
            seed_storage=reloaded_storage.menu_seed_storage,
            legacy_storage=reloaded_storage.legacy_menu_storage,
        )
    )
    reloaded_orders = OrderService(
        menu=reloaded_menu,
        storage_or_path=reloaded_storage.orders_storage,
    )
    reloaded_billing = BillingService(storage_or_path=reloaded_storage.invoices_storage)
    reloaded_payments = PaymentService(
        order_service=reloaded_orders,
        storage_or_path=reloaded_storage.payments_storage,
    )
    reloaded_tables = TableRepository(reloaded_storage.tables_storage).list_all()

    assert len(reloaded_menu.list_items()) == 3
    assert reloaded_menu.get_item("F001").name == "Phở bò"
    assert reloaded_tables["Bàn 1"] == "Trống"

    saved_order = reloaded_orders.get_order(order.order_id)
    assert saved_order.status == "PAID"
    assert saved_order.total() == expected_total

    assert len(reloaded_payments.list_payments()) == 1
    assert len(reloaded_billing.list_invoices()) == 1
    assert reloaded_billing.get_total_revenue() == expected_total
