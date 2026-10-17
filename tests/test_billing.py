import pytest

from src.core.payment_service import PaymentError, PaymentService
from src.core.services.billing_service import BillingService
from src.core.services.menu_service import MenuService
from src.core.services.order_service import OrderService
from src.models.payment import PaymentStatus


def test_billing_calculation_and_invoicing(tmp_path):
    billing_storage = tmp_path / "invoices.json"
    billing_service = BillingService(storage_or_path=billing_storage)

    items = [
        {"price": 45000, "quantity": 2},
        {"price": 25000, "quantity": 1},
        {"price": 15000, "quantity": 3},
    ]
    total = billing_service.calculate_total(items)
    assert total == 45000 * 2 + 25000 * 1 + 15000 * 3  # 160000

    invoice = billing_service.create_invoice(
        order={"order_id": "DH001", "table_id": "Bàn 1", "total": total},
        payment_id="TT001",
    )
    assert invoice.total == 160000
    assert invoice.order_id == "DH001"
    assert invoice.payment_id == "TT001"
    assert billing_service.get_total_revenue() == 160000

    # Test load from file
    reloaded_billing = BillingService(storage_or_path=billing_storage)
    assert len(reloaded_billing.list_invoices()) == 1
    assert reloaded_billing.get_total_revenue() == 160000


def test_payment_service_workflow(tmp_path):
    data_dir = tmp_path / "data"
    menu_service = MenuService(data_dir / "menu.json")
    menu_service.add_item("F001", "Phở bò", 50000)

    order_service = OrderService(menu=menu_service, storage_or_path=data_dir / "orders.json")
    order = order_service.create_order(table_id="Bàn 3")
    order_service.add_item(order.order_id, "F001", quantity=2)

    payment_service = PaymentService(
        order_service=order_service,
        storage_or_path=data_dir / "payments.json",
    )

    # 1. Sai số tiền thanh toán
    with pytest.raises(PaymentError):
        payment_service.pay(order.order_id, amount=90000)

    # 2. Thanh toán đúng số tiền
    payment = payment_service.pay(order.order_id, amount=100000)
    assert payment.payment_id == "TT001"
    assert payment.status == PaymentStatus.SUCCESS
    assert order.status == "PAID"

    # 3. Thanh toán lại đơn đã PAID
    with pytest.raises(PaymentError):
        payment_service.pay(order.order_id, amount=100000)

    # 4. Kiểm tra lưu trữ thanh toán
    reloaded_payments = PaymentService(
        order_service=order_service,
        storage_or_path=data_dir / "payments.json",
    )
    assert len(reloaded_payments.list_payments()) == 1
    assert reloaded_payments.list_payments()[0].payment_id == "TT001"
