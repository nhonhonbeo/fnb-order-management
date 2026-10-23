from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from types import SimpleNamespace

import pytest

from src.features.kitchen.queue import OrderQueue
from src.features.kitchen.service import KitchenService
from src.features.menu.model import MenuItem
from src.features.menu.service import DuplicateCodeError, ItemNotFoundError, MenuService
from src.features.orders.model import Order
from src.features.orders.service import OrderService
from src.features.payments.billing_service import BillingService
from src.features.payments.service import PaymentError, PaymentService
from src.reports.service import ReportingService
from src.features.tables.service import TableService
from src.users.permissions import can_cancel_order, can_change_table, can_edit_order


def test_order_creation_and_item_addition(tmp_path):
    storage_dir = tmp_path / "data"
    menu_service = MenuService(storage_dir / "menu.json")
    menu_service.add_item("F001", "Phở bò", 45000)
    menu_service.add_item("F002", "Bánh mì", 25000)

    queue = OrderQueue()
    order_service = OrderService(
        menu=menu_service,
        queue=queue,
        storage_or_path=storage_dir / "orders.json",
    )

    # 1. Tạo đơn hàng
    order = order_service.create_order(table_id="Bàn 1")
    assert order.order_id == "DH001"
    assert order.table_id == "Bàn 1"
    assert order.status == "NEW"

    # 2. Thêm món vào đơn
    order_service.add_item(order.order_id, "F001", quantity=2)
    order_service.add_item(order.order_id, "F002", quantity=1)
    assert len(order.items) == 2
    assert order.total() == 2 * 45000 + 1 * 25000  # 115000

    # Cộng dồn số lượng khi thêm món trùng mã
    order_service.add_item(order.order_id, "F001", quantity=1)
    assert len(order.items) == 2
    assert order.total() == 3 * 45000 + 1 * 25000  # 160000


def test_order_validation_and_kitchen_workflow(tmp_path):
    storage_dir = tmp_path / "data"
    menu_service = MenuService(storage_dir / "menu.json")
    menu_service.add_item("F001", "Phở bò", 45000)
    inactive_item = menu_service.add_item("F003", "Trà tắc", 15000)
    inactive_item.deactivate()

    queue = OrderQueue()
    order_service = OrderService(
        menu=menu_service,
        queue=queue,
        storage_or_path=storage_dir / "orders.json",
    )

    order = order_service.create_order(table_id="Bàn 2")

    # Số lượng không hợp lệ
    with pytest.raises(ValueError):
        order_service.add_item(order.order_id, "F001", quantity=0)

    # Món đã ngừng kinh doanh
    with pytest.raises(ValueError):
        order_service.add_item(order.order_id, "F003", quantity=1)

    # Món không tồn tại
    with pytest.raises(ValueError, match="Không tìm thấy món ăn"):
        order_service.add_item(order.order_id, "F999", quantity=1)

    # Không thể gửi đơn trống vào bếp
    with pytest.raises(ValueError):
        order_service.send_to_kitchen(order.order_id)

    order_service.add_item(order.order_id, "F001", quantity=2)

    # Gửi bếp thành công
    order_service.send_to_kitchen(order.order_id)
    assert order.status == "IN_PROGRESS"
    assert queue.size() == 1

    # Không thể sửa đơn đã gửi bếp
    with pytest.raises(ValueError):
        order_service.add_item(order.order_id, "F001", quantity=1)

    # Đánh dấu hoàn thành
    order_service.mark_completed(order.order_id)
    assert order.status == "COMPLETED"


@pytest.mark.parametrize("quantity", [0, -1, 1.5, "2", True])
def test_order_rejects_non_positive_or_non_integer_quantity(tmp_path, quantity):
    menu = MenuService(tmp_path / "menu.json")
    menu.add_item("F001", "Phở bò", 45000)
    service = OrderService(menu=menu, storage_or_path=tmp_path / "orders.json")
    order = service.create_order()

    with pytest.raises(ValueError, match="Số lượng phải là số nguyên lớn hơn 0"):
        service.add_item(order.order_id, "F001", quantity)


@pytest.mark.parametrize("price", [0, -1])
def test_menu_rejects_non_positive_price(tmp_path, price):
    menu = MenuService(tmp_path / "menu.json")

    with pytest.raises(ValueError, match="Giá phải là số nguyên lớn hơn 0"):
        menu.add_item("F001", "Phở bò", price)


@pytest.mark.parametrize("price", [1.5, "invalid", True])
def test_menu_rejects_non_whole_or_non_numeric_prices(tmp_path, price):
    menu = MenuService(tmp_path / "menu.json")

    with pytest.raises(ValueError):
        menu.add_item("F001", "Phở bò", price)

    assert menu.list_items() == []
    assert not (tmp_path / "menu.json").exists()


def test_menu_rejects_blank_code_and_missing_code_operations_are_safe(tmp_path):
    menu = MenuService(tmp_path / "menu.json")
    with pytest.raises(ValueError, match="Mã và tên"):
        menu.add_item("", "Phở bò", 45000)

    assert menu.get_item("F404") is None
    with pytest.raises(ItemNotFoundError):
        menu.update_item("F404", name="Không tồn tại")
    assert menu.remove_item("F404") is False
    assert menu.list_items() == []


def test_menu_rejects_duplicate_code_and_deactivates_referenced_item(tmp_path):
    menu = MenuService(tmp_path / "menu.json")
    item = menu.add_item("F001", "Phở bò", 45000)

    with pytest.raises(DuplicateCodeError):
        menu.add_item("F001", "Bánh mì", 25000)

    orders = OrderService(menu=menu, storage_or_path=tmp_path / "orders.json")
    order = orders.create_order()
    orders.add_item(order.order_id, "F001", 1)

    assert menu.remove_item("F001", used_codes=orders.used_codes()) is True
    assert menu.get_item("F001") is item
    assert item.is_active is False


def test_menu_invalid_update_preserves_cached_and_persisted_values(tmp_path):
    menu = MenuService(tmp_path / "menu.json")
    item = menu.add_item("F001", "Phở bò", 45000)

    with pytest.raises(ValueError, match="Giá"):
        menu.update_item("F001", name="Phở mới", price=-10)

    assert menu.get_item("F001") is item
    assert (item.name, item.price) == ("Phở bò", 45000)
    restored = MenuService(tmp_path / "menu.json").get_item("F001")
    assert (restored.name, restored.price) == ("Phở bò", 45000)


def test_menu_update_storage_failure_does_not_mutate_cached_item(tmp_path, monkeypatch):
    menu = MenuService(tmp_path / "menu.json")
    item = menu.add_item("F001", "Phở bò", 45000)

    def fail_update(_item):
        raise OSError("disk full")

    monkeypatch.setattr(menu.repository, "update", fail_update)
    with pytest.raises(OSError, match="disk full"):
        menu.update_item("F001", name="Phở mới", price=50000)

    assert menu.get_item("F001") is item
    assert (item.name, item.price) == ("Phở bò", 45000)
    assert MenuService(tmp_path / "menu.json").get_item("F001").name == "Phở bò"


def test_empty_cart_and_missing_order_leave_order_queue_and_files_unchanged(tmp_path):
    menu = MenuService(tmp_path / "menu.json")
    menu.add_item("F001", "Phở bò", 45000)
    queue = OrderQueue()
    service = OrderService(menu, queue, tmp_path / "orders.json")

    with pytest.raises(ValueError, match="Đơn phải có món"):
        service.create_order_from_cart("Bàn 1", [])
    with pytest.raises(ValueError, match="Không tìm thấy"):
        service.add_item("DH999", "F001", 1)

    assert service.list_orders() == []
    assert queue.is_empty()
    assert not (tmp_path / "orders.json").exists()


def test_repeated_add_item_increments_once_per_action_and_invalid_repeat_is_atomic(tmp_path):
    menu = MenuService(tmp_path / "menu.json")
    menu.add_item("F001", "Phở bò", 45000)
    service = OrderService(menu=menu, storage_or_path=tmp_path / "orders.json")
    order = service.create_order()
    service.add_item(order.order_id, "F001", 1)
    service.add_item(order.order_id, "F001", 1)

    with pytest.raises(ValueError, match="Số lượng"):
        service.add_item(order.order_id, "F001", 0)

    assert order.total() == 90000
    assert len(order.items) == 1
    assert order.items[0].quantity == 2
    restored = OrderService(menu=menu, storage_or_path=tmp_path / "orders.json")
    assert restored.get_order(order.order_id).total() == 90000


def test_order_persistence_and_used_codes(tmp_path):
    storage_file = tmp_path / "orders.json"
    menu_service = MenuService(tmp_path / "menu.json")
    menu_service.add_item("F001", "Phở bò", 45000)

    queue = OrderQueue()
    service1 = OrderService(menu=menu_service, queue=queue, storage_or_path=storage_file)
    order1 = service1.create_order(table_id="Bàn 5")
    created_at = order1.created_at
    assert datetime.fromisoformat(created_at)
    service1.add_item(order1.order_id, "F001", quantity=3)

    assert service1.used_codes() == {"F001"}

    # Khởi tạo lại service đọc từ file cũ
    service2 = OrderService(menu=menu_service, queue=queue, storage_or_path=storage_file)
    reloaded_order = service2.get_order(order1.order_id)
    assert reloaded_order.total() == 135000
    assert reloaded_order.table_id == "Bàn 5"
    assert reloaded_order.created_at == created_at
    assert service2.used_codes() == {"F001"}


def test_legacy_order_json_loads_new_fields_with_safe_defaults():
    order = Order.from_dict({
        "order_id": "DH001",
        "table_id": "Bàn 1",
        "status": "NEW",
        "items": [],
    })

    assert order.note == ""
    assert order.cancelled_at is None
    assert order.cancel_reason is None
    assert order.to_dict()["note"] == ""


def _order_edit_services(tmp_path):
    menu = MenuService(tmp_path / "menu.json")
    menu.add_item("F001", "Phở bò", 45000)
    menu.add_item("F002", "Bánh mì", 25000)
    menu.add_item("F003", "Trà tắc", 15000)
    tables = TableService(tmp_path / "tables.json")
    queue = OrderQueue()
    orders = OrderService(
        menu=menu,
        queue=queue,
        storage_or_path=tmp_path / "orders.json",
        table_service=tables,
    )
    kitchen = KitchenService(queue, tmp_path / "kitchen.json", orders)
    orders.set_kitchen_service(kitchen)
    return menu, tables, queue, orders, kitchen


def test_edit_order_changes_lines_note_and_preserves_fifo(tmp_path):
    menu, tables, queue, orders, kitchen = _order_edit_services(tmp_path)
    first = orders.create_order("Bàn 1")
    tables.reserve("Bàn 1")
    orders.add_item(first.order_id, "F001", 2)
    orders.add_item(first.order_id, "F002", 1)
    orders.send_to_kitchen(first.order_id)

    second = orders.create_order("Bàn 2")
    tables.reserve("Bàn 2")
    orders.add_item(second.order_id, "F002", 1)
    orders.send_to_kitchen(second.order_id)
    actor = SimpleNamespace(role="Nhân viên")

    orders.edit_order(
        first.order_id,
        [
            {"code": "F001", "quantity": 3},
            {"code": "F003", "quantity": 2},
        ],
        user=actor,
        note="Không cay",
    )

    assert [(item.item_code, item.quantity) for item in first.items] == [
        ("F001", 3),
        ("F003", 2),
    ]
    assert first.note == "Không cay"
    assert first.total() == 165000
    assert [(item.order_id, item.item_code, item.quantity) for item in queue.list_requests()] == [
        (first.order_id, "F001", 3),
        (second.order_id, "F002", 1),
        (first.order_id, "F003", 2),
    ]
    restored = OrderService(menu, storage_or_path=tmp_path / "orders.json")
    assert restored.get_order(first.order_id).note == "Không cay"
    assert kitchen.list_requests()[0].quantity == 3


def test_edit_order_rejects_quantity_change_after_kitchen_started(tmp_path):
    _, tables, queue, orders, kitchen = _order_edit_services(tmp_path)
    order = orders.create_order("Bàn 1")
    tables.reserve("Bàn 1")
    orders.add_item(order.order_id, "F001", 2)
    orders.send_to_kitchen(order.order_id)
    kitchen.start(order.order_id, "F001")

    with pytest.raises(ValueError, match="đã bắt đầu chế biến"):
        orders.edit_order(
            order.order_id,
            [{"code": "F001", "quantity": 1}],
            user=SimpleNamespace(role="Nhân viên"),
        )

    assert order.items[0].quantity == 2
    assert queue.peek().status == "COOKING"
    assert kitchen.list_requests()[0].quantity == 2


def test_failed_order_save_rolls_back_kitchen_edit(tmp_path, monkeypatch):
    _, tables, queue, orders, kitchen = _order_edit_services(tmp_path)
    order = orders.create_order("Bàn 1")
    tables.reserve("Bàn 1")
    orders.add_item(order.order_id, "F001", 2)
    orders.send_to_kitchen(order.order_id)
    kitchen_before = (tmp_path / "kitchen.json").read_text(encoding="utf-8")
    orders_before = (tmp_path / "orders.json").read_text(encoding="utf-8")

    def fail_save():
        raise OSError("orders file is not writable")

    monkeypatch.setattr(orders, "save", fail_save)
    with pytest.raises(OSError, match="orders file is not writable"):
        orders.edit_order(
            order.order_id,
            [{"code": "F001", "quantity": 3}],
            user=SimpleNamespace(role="Nhân viên"),
        )

    assert order.items[0].quantity == 2
    assert queue.peek().quantity == 2
    assert kitchen.list_requests()[0].quantity == 2
    assert (tmp_path / "kitchen.json").read_text(encoding="utf-8") == kitchen_before
    assert (tmp_path / "orders.json").read_text(encoding="utf-8") == orders_before


def test_edit_order_moves_reservation_to_available_table(tmp_path):
    _, tables, _, orders, _ = _order_edit_services(tmp_path)
    order = orders.create_order("Bàn 1")
    tables.reserve("Bàn 1")
    orders.add_item(order.order_id, "F001", 1)

    orders.edit_order(
        order.order_id,
        [{"code": "F001", "quantity": 1}],
        user=SimpleNamespace(role="Nhân viên"),
        table_id="Bàn 2",
    )

    assert order.table_id == "Bàn 2"
    assert tables.is_available("Bàn 1")
    assert not tables.is_available("Bàn 2")


def test_completed_order_with_new_item_returns_to_kitchen(tmp_path):
    _, _, _, orders, kitchen = _order_edit_services(tmp_path)
    order = orders.create_order_from_cart(
        "Bàn 1",
        [{"code": "F001", "quantity": 1}],
    )
    kitchen.start(order.order_id, "F001")
    kitchen.complete(order.order_id, "F001")
    assert order.status == "COMPLETED"

    orders.edit_order(
        order.order_id,
        [
            {"code": "F001", "quantity": 1},
            {"code": "F003", "quantity": 1},
        ],
        user=SimpleNamespace(role="Nhân viên"),
    )

    assert order.status == "IN_PROGRESS"
    assert kitchen.current().item_code == "F003"
    kitchen.start(order.order_id, "F003")
    kitchen.complete(order.order_id, "F003")
    assert order.status == "COMPLETED"


def test_cancel_order_requires_reason_and_releases_table(tmp_path):
    _, tables, queue, orders, _ = _order_edit_services(tmp_path)
    order = orders.create_order("Bàn 1")
    tables.reserve("Bàn 1")
    orders.add_item(order.order_id, "F001", 1)
    staff = SimpleNamespace(role="Nhân viên")

    with pytest.raises(ValueError, match="lý do"):
        orders.cancel_order(order.order_id, "  ", staff)

    assert order.status == "NEW"
    assert not tables.is_available("Bàn 1")

    orders.cancel_order(order.order_id, "Khách đổi ý", staff)

    assert order.status == "CANCELLED"
    assert order.cancel_reason == "Khách đổi ý"
    assert order.cancelled_at
    assert queue.is_empty()
    assert tables.is_available("Bàn 1")
    restored = OrderService(storage_or_path=tmp_path / "orders.json")
    assert restored.get_order(order.order_id).cancel_reason == "Khách đổi ý"


def test_cancel_sent_order_requires_manager_and_removes_kitchen_requests(tmp_path):
    _, tables, queue, orders, kitchen = _order_edit_services(tmp_path)
    order = orders.create_order("Bàn 1")
    tables.reserve("Bàn 1")
    orders.add_item(order.order_id, "F001", 1)
    orders.add_item(order.order_id, "F002", 1)
    orders.send_to_kitchen(order.order_id)

    with pytest.raises(ValueError, match="không có quyền"):
        orders.cancel_order(
            order.order_id,
            "Khách đổi ý",
            SimpleNamespace(role="Nhân viên"),
        )
    assert queue.size() == 2

    orders.cancel_order(
        order.order_id,
        "Khách đổi ý",
        SimpleNamespace(role="Quản lý"),
    )

    assert order.status == "CANCELLED"
    assert queue.is_empty()
    assert kitchen.list_requests() == []
    assert tables.is_available("Bàn 1")


def test_failed_order_save_rolls_back_cancellation_queue_and_table(tmp_path, monkeypatch):
    _, tables, queue, orders, kitchen = _order_edit_services(tmp_path)
    order = orders.create_order("Bàn 1")
    tables.reserve("Bàn 1")
    orders.add_item(order.order_id, "F001", 1)
    orders.send_to_kitchen(order.order_id)
    kitchen_before = (tmp_path / "kitchen.json").read_text(encoding="utf-8")
    orders_before = (tmp_path / "orders.json").read_text(encoding="utf-8")

    def fail_save():
        raise OSError("orders file is not writable")

    monkeypatch.setattr(orders, "save", fail_save)
    with pytest.raises(OSError, match="orders file is not writable"):
        orders.cancel_order(
            order.order_id,
            "Khách đổi ý",
            SimpleNamespace(role="Quản lý"),
        )

    assert order.status == "IN_PROGRESS"
    assert queue.size() == 1
    assert len(kitchen.list_requests()) == 1
    assert not tables.is_available("Bàn 1")
    assert (tmp_path / "kitchen.json").read_text(encoding="utf-8") == kitchen_before
    assert (tmp_path / "orders.json").read_text(encoding="utf-8") == orders_before


def test_paid_order_cannot_be_cancelled_or_edited(tmp_path):
    _, _, _, orders, _ = _order_edit_services(tmp_path)
    order = orders.create_order()
    order.status = "PAID"
    orders.save()
    manager = SimpleNamespace(role="Quản lý")

    with pytest.raises(ValueError, match="đã thanh toán"):
        orders.cancel_order(order.order_id, "Lý do", manager)
    with pytest.raises(ValueError, match="quyền sửa"):
        orders.edit_order(order.order_id, [], user=manager)

    assert order.status == "PAID"


def test_cancelled_order_cannot_be_paid_or_included_in_reports(tmp_path):
    _, _, _, orders, _ = _order_edit_services(tmp_path)
    order = orders.create_order()
    orders.add_item(order.order_id, "F001", 1)
    orders.cancel_order(
        order.order_id,
        "Khách đổi ý",
        SimpleNamespace(role="Nhân viên"),
    )
    payments = PaymentService(orders, tmp_path / "payments.json")

    with pytest.raises(PaymentError, match="Đơn đã hủy"):
        payments.pay(order.order_id, 45000)

    order_views = [{
        "id": order.order_id,
        "table": "Bàn 1",
        "status": "CANCELLED",
        "created_at": "2026-10-20T12:00:00",
        "items": [{"name": "Phở bò", "quantity": 1, "price": 45000}],
    }]
    reporting = ReportingService()
    assert reporting.best_sellers(order_views) == []
    assert reporting.hourly_revenue(order_views)["12:00"] == 0
    assert reporting.table_statuses(
        {"Bàn 1": "Trống"},
        order_views,
    )[0]["total"] is None

    request = SimpleNamespace(order_id=order.order_id, status="NEW")
    assert reporting.dashboard_alerts(
        order_views,
        [request],
        now=datetime.fromisoformat("2026-10-20T15:00:00"),
    ) == []


def test_order_edit_and_cancel_permissions_are_role_aware():
    order = Order("DH001", status="NEW")
    staff = SimpleNamespace(role="Nhân viên")
    manager = SimpleNamespace(role="Quản lý")
    cashier = SimpleNamespace(role="Thu ngân")
    chef = SimpleNamespace(role="Đầu bếp")

    assert can_change_table(staff)
    assert can_change_table(manager)
    assert can_change_table(cashier)
    assert not can_change_table(chef)
    assert can_edit_order(staff, order)
    assert can_edit_order(manager, order)
    assert not can_edit_order(cashier, order)
    assert can_cancel_order(staff, order)

    order.status = "IN_PROGRESS"
    assert not can_cancel_order(staff, order)
    assert can_cancel_order(manager, order)
    order.status = "PAID"
    assert not can_edit_order(manager, order)
    assert not can_cancel_order(manager, order)


def test_order_from_legacy_dict_without_created_at():
    loaded_order = Order.from_dict({"order_id": "DH001", "items": []})

    assert loaded_order.created_at is None


def test_order_search_filters_and_history_sorting(tmp_path):
    service = OrderService(storage_or_path=tmp_path / "orders.json")
    orders = {order.order_id: order for order in (service.create_order() for _ in range(7))}
    orders["DH001"].status = "NEW"
    orders["DH002"].status = "IN_PROGRESS"
    orders["DH003"].status = "COMPLETED"
    orders["DH004"].status = "PAID"
    orders["DH004"].created_at = "2026-01-01T10:00:00"
    orders["DH005"].status = "CANCELLED"
    orders["DH005"].created_at = "2026-03-01T10:00:00"

    older_paid = orders["DH006"]
    older_paid.status = "PAID"
    older_paid.created_at = "2025-12-01T10:00:00"
    legacy_cancelled = orders["DH007"]
    legacy_cancelled.status = "CANCELLED"
    legacy_cancelled.created_at = None

    assert [order.order_id for order in service.search_orders()] == [
        "DH001", "DH002", "DH003", "DH004", "DH005", "DH006", "DH007",
    ]
    assert [order.order_id for order in service.search_orders(keyword="dh00")] == [
        "DH001", "DH002", "DH003", "DH004", "DH005", "DH006", "DH007",
    ]
    assert [order.order_id for order in service.search_orders("003")] == ["DH003"]
    assert [order.order_id for order in service.search_orders(status="IN_PROGRESS")] == [
        "DH002",
    ]
    assert [order.order_id for order in service.search_orders("dh00", "PAID")] == [
        "DH004", "DH006",
    ]
    assert service.search_orders("missing") == []
    assert [order.order_id for order in service.list_history()] == [
        "DH005", "DH004", "DH006", "DH007",
    ]


def _table_change_services(tmp_path):
    table_service = TableService(tmp_path / "tables.json")
    for table_name in ("Bàn A", "Bàn B", "Bàn C"):
        table_service.add_table(table_name)
    order_service = OrderService(
        storage_or_path=tmp_path / "orders.json",
        table_service=table_service,
    )
    return table_service, order_service


def _create_seated_order(table_service, order_service, table_name, status="NEW"):
    order = order_service.create_order(table_name)
    order.status = status
    order_service.save()
    table_service.reserve(table_name)
    return order


def test_change_table_and_chain_then_checkout_releases_current_table(tmp_path):
    tables, orders = _table_change_services(tmp_path)
    menu = MenuService(tmp_path / "menu.json")
    menu.add_item("F001", "Phở bò", 45000)
    menu.add_item("F002", "Bánh mì", 25000)
    orders.menu = menu
    queue = OrderQueue()
    orders.queue = queue
    kitchen = KitchenService(queue, tmp_path / "kitchen.json", orders)
    orders.set_kitchen_service(kitchen)
    order = _create_seated_order(tables, orders, "Bàn A")
    order.table_id = " Bàn A "
    orders.save()
    orders.add_item(order.order_id, "F001", 1)
    orders.add_item(order.order_id, "F002", 1)
    orders.send_to_kitchen(order.order_id)
    kitchen.start(order.order_id, "F001")
    queue_before = [
        (item.order_id, item.item_code, item.status)
        for item in kitchen.list_requests()
    ]

    changed_order = orders.change_table(" Bàn A ", " Bàn B ")
    assert changed_order.order_id == order.order_id
    assert (changed_order.table_id, tables.list_tables()["Bàn A"], tables.list_tables()["Bàn B"]) == (
        "Bàn B", "Trống", "Đang phục vụ",
    )
    changed_order = orders.change_table("Bàn B", "Bàn C")
    assert (changed_order.table_id, tables.list_tables()["Bàn B"], tables.list_tables()["Bàn C"]) == (
        "Bàn C", "Trống", "Đang phục vụ",
    )
    assert [
        (item.order_id, item.item_code, item.status)
        for item in kitchen.list_requests()
    ] == queue_before

    restored_tables = TableService(tmp_path / "tables.json")
    restored_orders = OrderService(
        storage_or_path=tmp_path / "orders.json",
        table_service=restored_tables,
    )
    assert restored_orders.get_order(order.order_id).table_id == "Bàn C"
    assert restored_tables.list_tables()["Bàn C"] == "Đang phục vụ"

    restored_kitchen = KitchenService(
        OrderQueue(),
        tmp_path / "kitchen.json",
        restored_orders,
    )
    assert [
        (item.order_id, item.item_code, item.status)
        for item in restored_kitchen.list_requests()
    ] == queue_before
    restored_kitchen.complete(order.order_id, "F001")
    restored_kitchen.start(order.order_id, "F002")
    restored_kitchen.complete(order.order_id, "F002")
    billing = BillingService(tmp_path / "invoices.json")
    payments = PaymentService(
        restored_orders,
        tmp_path / "payments.json",
        billing_service=billing,
        table_service=restored_tables,
        kitchen_service=restored_kitchen,
    )
    _, invoice = payments.checkout(order.order_id)
    assert invoice.table_id == "Bàn C"
    assert restored_tables.list_tables()["Bàn A"] == "Trống"
    assert restored_tables.list_tables()["Bàn B"] == "Trống"
    assert restored_tables.list_tables()["Bàn C"] == "Trống"


def test_change_table_then_checkout_saves_invoice_with_destination_table(tmp_path):
    tables, orders = _table_change_services(tmp_path)
    menu = MenuService(tmp_path / "menu.json")
    menu.add_item("F001", "Phở bò", 45000)
    orders.menu = menu
    queue = OrderQueue()
    orders.queue = queue
    kitchen = KitchenService(queue, tmp_path / "kitchen.json", orders)
    orders.set_kitchen_service(kitchen)
    order = _create_seated_order(tables, orders, "Bàn A")
    orders.add_item(order.order_id, "F001", 1)
    order.status = "COMPLETED"
    orders.save()
    orders.change_table("Bàn A", "Bàn B")
    billing = BillingService(tmp_path / "invoices.json")
    payments = PaymentService(
        orders,
        tmp_path / "payments.json",
        billing_service=billing,
        table_service=tables,
        kitchen_service=kitchen,
    )

    _, invoice = payments.checkout(order.order_id)

    assert invoice.table_id == "Bàn B"
    assert tables.list_tables()["Bàn A"] == "Trống"
    assert tables.list_tables()["Bàn B"] == "Trống"


def test_change_table_save_failure_rolls_back_order_and_both_files(
    tmp_path,
    monkeypatch,
):
    tables, orders = _table_change_services(tmp_path)
    order = _create_seated_order(tables, orders, "Bàn A")
    original_order_file = (tmp_path / "orders.json").read_bytes()
    original_table_file = (tmp_path / "tables.json").read_bytes()

    def fail_save():
        raise OSError("disk full")

    monkeypatch.setattr(orders, "save", fail_save)
    with pytest.raises(OSError, match="disk full"):
        orders.change_table("Bàn A", "Bàn B")

    assert order.table_id == "Bàn A"
    assert tables.list_tables()["Bàn A"] == "Đang phục vụ"
    assert tables.list_tables()["Bàn B"] == "Trống"
    saved_order = OrderService(storage_or_path=tmp_path / "orders.json")
    assert saved_order.get_order(order.order_id).table_id == "Bàn A"
    assert (tmp_path / "orders.json").read_bytes() == original_order_file
    assert (tmp_path / "tables.json").read_bytes() == original_table_file


@pytest.mark.parametrize(
    ("source", "target", "status", "expected_error"),
    [
        ("Bàn A", "Bàn A", "NEW", "chính bàn"),
        ("Bàn A", "Bàn thiếu", "NEW", "không tồn tại"),
        ("Bàn rỗng", "Bàn B", "NEW", "không có đơn đang hoạt động"),
        ("Bàn A", "Bàn B", "PAID", "đã thanh toán"),
        ("Bàn A", "Bàn B", "CANCELLED", "đã bị hủy"),
    ],
)
def test_change_table_reports_invalid_source_and_target(
    tmp_path,
    source,
    target,
    status,
    expected_error,
):
    tables, orders = _table_change_services(tmp_path)
    if source != "Bàn rỗng":
        _create_seated_order(tables, orders, source, status=status)
    else:
        tables.add_table(source)

    with pytest.raises(ValueError, match=expected_error):
        orders.change_table(source, target)


def test_change_table_rejects_occupied_target_and_missing_source_table(tmp_path):
    tables, orders = _table_change_services(tmp_path)
    _create_seated_order(tables, orders, "Bàn A")
    _create_seated_order(tables, orders, "Bàn B")

    with pytest.raises(ValueError, match="đang có khách"):
        orders.change_table("Bàn A", "Bàn B")
    with pytest.raises(ValueError, match="Bàn nguồn.*không tồn tại"):
        orders.change_table("Bàn thiếu", "Bàn C")


def test_change_table_requires_source_order_table_id(tmp_path):
    tables, orders = _table_change_services(tmp_path)
    order = orders.create_order(None)

    with pytest.raises(ValueError, match="không có table_id"):
        orders.change_table(None, "Bàn A")
    assert order.table_id is None
    assert tables.list_tables()["Bàn A"] == "Trống"


@pytest.mark.parametrize("status", ["NEW", "IN_PROGRESS", "COMPLETED"])
def test_change_table_accepts_each_unpaid_order_status(tmp_path, status):
    tables, orders = _table_change_services(tmp_path)
    order = _create_seated_order(tables, orders, "Bàn A", status=status)

    changed_order = orders.change_table("Bàn A", "Bàn B")

    assert changed_order.order_id == order.order_id
    assert changed_order.table_id == "Bàn B"


def test_active_order_queries_normalize_table_names_and_detect_bad_data(tmp_path):
    _, orders = _table_change_services(tmp_path)
    first = orders.create_order(" Bàn A ")
    second = orders.create_order("Bàn A")

    assert orders.active_table_ids() == {"Bàn A"}
    with pytest.raises(ValueError, match="nhiều hơn một"):
        orders.get_active_order_by_table(" Bàn A ")

    second.status = "PAID"
    assert orders.get_active_order_by_table("Bàn A") is first
    assert orders.active_table_ids() == {"Bàn A"}
    first.status = "CANCELLED"
    assert orders.get_active_order_by_table("Bàn A") is None
    assert orders.active_table_ids() == set()


def test_two_order_services_cannot_claim_same_destination_table(tmp_path):
    first_tables, first_orders = _table_change_services(tmp_path)
    _create_seated_order(first_tables, first_orders, "Bàn A")
    _create_seated_order(first_tables, first_orders, "Bàn B")
    second_tables = TableService(tmp_path / "tables.json")
    second_orders = OrderService(
        storage_or_path=tmp_path / "orders.json",
        table_service=second_tables,
    )
    barrier = Barrier(2)

    def change(order_service, source):
        barrier.wait()
        try:
            order_service.change_table(source, "Bàn C")
            return "success"
        except ValueError as error:
            return str(error)

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(
            lambda args: change(*args),
            [
                (first_orders, "Bàn A"),
                (second_orders, "Bàn B"),
            ],
        ))

    assert sum(result == "success" for result in results) == 1
    assert sum(isinstance(result, str) and "đang có khách" in result for result in results) == 1
    final_orders = OrderService(storage_or_path=tmp_path / "orders.json").list_orders()
    assert sum(order.table_id == "Bàn C" for order in final_orders) == 1
