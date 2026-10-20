from datetime import datetime

import pytest

from src.kitchen.queue import OrderQueue
from src.menu.model import MenuItem
from src.menu.service import DuplicateCodeError, MenuService
from src.orders.model import Order
from src.orders.service import OrderService


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
