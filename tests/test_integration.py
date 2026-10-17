"""Kiểm thử tích hợp toàn bộ hệ thống F&B từ Storage, Model, Services đến luồng nghiệp vụ."""
from src.core.order_queue import OrderQueue
from src.core.payment_service import PaymentService
from src.core.services.billing_service import BillingService
from src.core.services.kitchen_service import KitchenService
from src.core.services.menu_service import MenuService
from src.core.services.order_service import OrderService
from src.core.storage import StorageManager
from src.models.payment import PaymentStatus


def test_full_fnb_order_and_payment_flow(tmp_path):
    data_dir = tmp_path / "data"
    storage_manager = StorageManager(data_dir=data_dir)

    # 1. Khởi tạo Backend Services
    menu_service = MenuService(storage_or_path=storage_manager.menu_storage)
    order_queue = OrderQueue()
    kitchen_service = KitchenService(kitchen_queue=order_queue)
    order_service = OrderService(
        menu=menu_service,
        queue=order_queue,
        storage_or_path=storage_manager.orders_storage,
    )
    billing_service = BillingService(storage_or_path=storage_manager.invoices_storage)
    payment_service = PaymentService(
        order_service=order_service,
        storage_or_path=storage_manager.payments_storage,
    )

    # 2. Thêm món vào thực đơn và kiểm tra lưu trữ
    item1 = menu_service.add_item("F001", "Phở bò", 45000)
    item2 = menu_service.add_item("F002", "Bánh mì", 25000)
    assert len(menu_service.list_items()) == 2

    # 3. Tạo đơn hàng gắn với Bàn 1
    tables = storage_manager.load_tables()
    assert tables["Bàn 1"] == "Trống"

    order = order_service.create_order(table_id="Bàn 1")
    order_service.add_item(order.order_id, "F001", quantity=2)
    order_service.add_item(order.order_id, "F002", quantity=1)
    tables["Bàn 1"] = "Đang phục vụ"
    storage_manager.save_tables(tables)

    expected_total = 2 * 45000 + 1 * 25000  # 115000
    assert order.total() == expected_total

    # 4. Gửi đơn xuống bếp qua hàng đợi FIFO
    order_service.send_to_kitchen(order.order_id)
    assert order.status == "IN_PROGRESS"
    assert kitchen_service.size() == 2

    # Bếp nhận món lần lượt theo FIFO
    req1 = kitchen_service.next_item()
    assert req1.item_code == "F001"
    assert req1.quantity == 2
    req2 = kitchen_service.next_item()
    assert req2.item_code == "F002"
    assert req2.quantity == 1
    assert kitchen_service.is_empty() is True

    # 5. Bếp hoàn thành món
    order_service.mark_completed(order.order_id)
    assert order.status == "COMPLETED"

    # 6. Thu ngân thực hiện thanh toán
    payment = payment_service.pay(order.order_id, amount=expected_total)
    assert payment.status == PaymentStatus.SUCCESS
    assert order.status == "PAID"

    # 7. Xuất hóa đơn
    invoice = billing_service.create_invoice(order=order, payment_id=payment.payment_id)
    assert invoice.total == expected_total
    assert billing_service.get_total_revenue() == expected_total

    # 8. Mở lại bàn trống
    tables["Bàn 1"] = "Trống"
    storage_manager.save_tables(tables)

    # 9. Kiểm tra tính bền vững (Persistence) sau khi nạp lại từ Storage
    reloaded_storage = StorageManager(data_dir=data_dir)
    reloaded_menu = MenuService(storage_or_path=reloaded_storage.menu_storage)
    reloaded_orders = OrderService(
        menu=reloaded_menu,
        storage_or_path=reloaded_storage.orders_storage,
    )
    reloaded_billing = BillingService(storage_or_path=reloaded_storage.invoices_storage)
    reloaded_payments = PaymentService(
        order_service=reloaded_orders,
        storage_or_path=reloaded_storage.payments_storage,
    )
    reloaded_tables = reloaded_storage.load_tables()

    assert len(reloaded_menu.list_items()) == 2
    assert reloaded_menu.get_item("F001").name == "Phở bò"
    assert reloaded_tables["Bàn 1"] == "Trống"

    saved_order = reloaded_orders.get_order(order.order_id)
    assert saved_order.status == "PAID"
    assert saved_order.total() == expected_total

    assert len(reloaded_payments.list_payments()) == 1
    assert len(reloaded_billing.list_invoices()) == 1
    assert reloaded_billing.get_total_revenue() == expected_total
