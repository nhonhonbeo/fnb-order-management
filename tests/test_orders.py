import pytest

from src.core.queues.order_queue import OrderQueue
from src.core.services.menu_service import MenuService
from src.core.services.order_service import OrderService
from src.models.menu_item import MenuItem


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


def test_order_persistence_and_used_codes(tmp_path):
    storage_file = tmp_path / "orders.json"
    menu_service = MenuService(tmp_path / "menu.json")
    menu_service.add_item("F001", "Phở bò", 45000)

    queue = OrderQueue()
    service1 = OrderService(menu=menu_service, queue=queue, storage_or_path=storage_file)
    order1 = service1.create_order(table_id="Bàn 5")
    service1.add_item(order1.order_id, "F001", quantity=3)

    assert service1.used_codes() == {"F001"}

    # Khởi tạo lại service đọc từ file cũ
    service2 = OrderService(menu=menu_service, queue=queue, storage_or_path=storage_file)
    reloaded_order = service2.get_order(order1.order_id)
    assert reloaded_order.total() == 135000
    assert reloaded_order.table_id == "Bàn 5"
    assert service2.used_codes() == {"F001"}
