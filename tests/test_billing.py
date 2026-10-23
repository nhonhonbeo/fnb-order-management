import pytest

from src.features.kitchen.queue import OrderQueue
from src.features.menu.service import MenuService
from src.features.orders.model import Order
from src.features.orders.service import OrderService
from src.features.payments.billing_service import BillingService
from src.features.payments.invoice import Invoice
from src.features.payments.payment import Payment, PaymentStatus
from src.features.payments.service import PaymentError, PaymentService


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
    assert isinstance(total, int)

    invoice = billing_service.create_invoice(
        order={"order_id": "DH001", "table_id": "Bàn 1", "total": total},
        payment_id="TT001",
    )
    assert invoice.total == 160000
    assert isinstance(invoice.total, int)
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

    queue = OrderQueue()
    order_service = OrderService(
        menu=menu_service,
        queue=queue,
        storage_or_path=data_dir / "orders.json",
    )
    order = order_service.create_order(table_id="Bàn 3")
    order_service.add_item(order.order_id, "F001", quantity=2)

    payment_service = PaymentService(
        order_service=order_service,
        storage_or_path=data_dir / "payments.json",
    )

    with pytest.raises(ValueError, match="Đơn chưa chế biến xong, không thể thanh toán"):
        payment_service.pay(order.order_id, amount=100000)

    order_service.send_to_kitchen(order.order_id)
    with pytest.raises(ValueError, match="Đơn chưa chế biến xong, không thể thanh toán"):
        payment_service.pay(order.order_id, amount=100000)

    order_service.mark_completed(order.order_id)

    # 1. Sai số tiền thanh toán
    with pytest.raises(PaymentError):
        payment_service.pay(order.order_id, amount=90000)

    with pytest.raises(PaymentError):
        payment_service.pay(order.order_id, amount=100000.5)

    # 2. Thanh toán đúng số tiền
    payment = payment_service.pay(order.order_id, amount=100000)
    assert payment.payment_id == "TT001"
    assert isinstance(payment.amount, int)
    assert payment.status == PaymentStatus.SUCCESS
    assert order.status == "PAID"

    # 3. Thanh toán lại đơn đã PAID
    with pytest.raises(PaymentError):
        payment_service.pay(order.order_id, amount=100000)

    with pytest.raises(ValueError, match="Không thể hủy đơn đã thanh toán"):
        order_service.cancel_order(order.order_id)
    assert order.status == "PAID"

    # 4. Kiểm tra lưu trữ thanh toán
    reloaded_payments = PaymentService(
        order_service=order_service,
        storage_or_path=data_dir / "payments.json",
    )
    assert len(reloaded_payments.list_payments()) == 1
    assert reloaded_payments.list_payments()[0].payment_id == "TT001"


def test_legacy_decimal_money_values_are_normalized_to_integer_vnd():
    order = Order.from_dict({
        "order_id": "DH001",
        "items": [{
            "item_code": "F001",
            "item_name": "Phở bò",
            "quantity": 1,
            "unit_price": 45000.0,
        }],
    })
    invoice = Invoice.from_dict({"order_id": "DH001", "total": 45000.0})
    payment = Payment.from_dict({
        "payment_id": "TT001",
        "order_id": "DH001",
        "amount": 45000.0,
    })

    assert order.total() == 45000
    assert isinstance(order.total(), int)
    assert isinstance(invoice.total, int)
    assert isinstance(payment.amount, int)


def test_payment_rejects_missing_order_without_creating_transaction(tmp_path):
    order_service = OrderService(storage_or_path=tmp_path / "orders.json")
    payment_service = PaymentService(
        order_service=order_service,
        storage_or_path=tmp_path / "payments.json",
    )

    with pytest.raises(PaymentError, match="Không tìm thấy đơn hàng"):
        payment_service.pay("DH404", 10000)

    assert payment_service.list_payments() == []
    assert not (tmp_path / "payments.json").exists()


def test_order_save_failure_during_payment_removes_payment_and_restores_state(
    tmp_path,
    monkeypatch,
):
    menu = MenuService(tmp_path / "menu.json")
    menu.add_item("F001", "Phở bò", 45000)
    queue = OrderQueue()
    orders = OrderService(
        menu=menu,
        queue=queue,
        storage_or_path=tmp_path / "orders.json",
    )
    order = orders.create_order()
    orders.add_item(order.order_id, "F001", 1)
    orders.send_to_kitchen(order.order_id)
    orders.mark_completed(order.order_id)
    payments = PaymentService(orders, tmp_path / "payments.json")
    original_save = orders.save

    def fail_save():
        raise OSError("orders file is not writable")

    monkeypatch.setattr(orders, "save", fail_save)
    with pytest.raises(OSError, match="orders file is not writable"):
        payments.pay(order.order_id, 45000)
    monkeypatch.setattr(orders, "save", original_save)

    assert order.status == "COMPLETED"
    assert payments.list_payments() == []
    assert PaymentService(orders, tmp_path / "payments.json").list_payments() == []
