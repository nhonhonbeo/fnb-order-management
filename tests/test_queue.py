import json

import pytest
from types import SimpleNamespace

from src.shared.data_structures.queue import Queue
from src.shared.data_structures.linked_list import LinkedList
from src.kitchen.queue import EmptyQueueError, KitchenRequest, OrderQueue
from src.kitchen.service import KitchenService
from src.menu.service import MenuService
from src.orders.service import OrderService


def test_custom_linked_list_queue():
    q = Queue()
    assert q.is_empty() is True
    assert q.size() == 0

    q.enqueue("A")
    q.enqueue("B")
    q.enqueue("C")

    assert q.is_empty() is False
    assert q.size() == 3
    assert q.peek() == "A"
    assert q.dequeue() == "A"
    assert q.dequeue() == "B"
    assert q.size() == 1
    assert q.dequeue() == "C"
    assert q.is_empty() is True

    with pytest.raises(IndexError):
        q.dequeue()


def test_linked_list_tail_stays_valid_after_delete_and_emptying():
    linked_list = LinkedList()
    linked_list.append("A")
    linked_list.append("B")
    assert linked_list.tail.data == "B"

    assert linked_list.delete("B") is True
    linked_list.append("C")
    assert list(linked_list) == ["A", "C"]
    assert linked_list.tail.data == "C"

    assert linked_list.pop_front() == "A"
    assert linked_list.pop_front() == "C"
    assert linked_list.is_empty() is True
    assert linked_list.tail is None

    linked_list.append("D")
    assert linked_list.peek_front() == "D"
    assert linked_list.tail.data == "D"


def test_order_queue_fifo_and_cancellation():
    oq = OrderQueue()
    assert oq.is_empty() is True

    req1 = KitchenRequest(order_id="DH001", item_code="F001", item_name="Phở bò", quantity=2)
    req2 = KitchenRequest(order_id="DH002", item_code="F002", item_name="Bánh mì", quantity=1)
    req3 = KitchenRequest(order_id="DH001", item_code="F003", item_name="Trà tắc", quantity=2)

    oq.enqueue(req1)
    oq.enqueue(req2)
    oq.enqueue(req3)

    assert oq.size() == 3
    assert oq.peek() == req1

    # Remove all requests belonging to DH001 when order is cancelled
    oq.remove_by_order("DH001")
    assert oq.size() == 1
    assert oq.dequeue() == req2
    assert oq.is_empty() is True

    with pytest.raises(EmptyQueueError):
        oq.dequeue()


def test_order_queue_rejects_duplicate_request_without_changing_fifo():
    oq = OrderQueue()
    first = KitchenRequest("DH001", "F001", "Phở bò", 1)
    second = KitchenRequest("DH002", "F002", "Bánh mì", 1)
    oq.enqueue(first)
    oq.enqueue(second)

    with pytest.raises(ValueError, match="đã có trong hàng đợi"):
        oq.enqueue(KitchenRequest("DH001", "F001", "Phở bò", 1))

    assert oq.list_requests() == [first, second]
    assert oq.peek() is first
    assert oq.dequeue() is first
    assert oq.dequeue() is second


def test_kitchen_rejects_missing_or_duplicate_requests_without_losing_fifo(tmp_path):
    queue = OrderQueue()
    kitchen = KitchenService(queue, tmp_path / "kitchen.json")
    first = KitchenRequest("DH001", "F001", "Phở bò", 1)
    kitchen.send_to_kitchen(first)
    kitchen.send_to_kitchen(KitchenRequest("DH002", "F002", "Bánh mì", 1))

    with pytest.raises(ValueError, match="Không tìm thấy|đầu hàng đợi"):
        kitchen.start("DH999", "F999")
    with pytest.raises(ValueError, match="đã có trong hàng đợi"):
        kitchen.send_to_kitchen(KitchenRequest("DH001", "F001", "Phở bò", 1))

    assert queue.list_requests()[0] is first
    assert [request.order_id for request in kitchen.list_requests()] == ["DH001", "DH002"]


def test_cancelling_cooking_order_removes_it_but_preserves_other_fifo_items(tmp_path):
    menu = MenuService(tmp_path / "menu.json")
    menu.add_item("F001", "Phở bò", 1)
    menu.add_item("F002", "Bánh mì", 1)
    queue = OrderQueue()
    orders = OrderService(menu, queue, tmp_path / "orders.json")
    kitchen = KitchenService(queue, tmp_path / "kitchen.json", orders)
    cooking_order = orders.create_order()
    orders.add_item(cooking_order.order_id, "F001", 1)
    orders.send_to_kitchen(cooking_order.order_id)
    kitchen.start(cooking_order.order_id, "F001")
    other = KitchenRequest("DH999", "F002", "Bánh mì", 1)
    kitchen.send_to_kitchen(other)

    orders.cancel_order(
        cooking_order.order_id,
        "Khách đổi ý",
        SimpleNamespace(role="Quản lý"),
    )

    assert cooking_order.status == "CANCELLED"
    assert queue.list_requests() == [other]
    assert kitchen.list_requests() == [other]


def test_kitchen_service_updates_request_status(tmp_path):
    queue = OrderQueue()
    service = KitchenService(queue, tmp_path / "kitchen.json")
    request = KitchenRequest("DH001", "F001", "Phở bò", 2)

    service.send_to_kitchen(request)
    service.update_status("DH001", "F001", "COOKING")

    assert service.list_requests() == [request]
    assert service.list_requests()[0].status == "COOKING"

    with pytest.raises(ValueError, match="không hợp lệ"):
        service.update_status("DH001", "F001", "INVALID")


def _create_kitchen_workflow(tmp_path):
    menu = MenuService(tmp_path / "menu.json")
    menu.add_item("F001", "Phở bò", 45000)
    menu.add_item("F002", "Bánh mì", 25000)
    queue = OrderQueue()
    orders = OrderService(menu, queue, tmp_path / "orders.json")
    order = orders.create_order("Bàn 1")
    orders.add_item(order.order_id, "F001", 1)
    orders.add_item(order.order_id, "F002", 1)
    orders.send_to_kitchen(order.order_id)
    kitchen = KitchenService(queue, tmp_path / "kitchen.json", orders)
    return order, orders, queue, kitchen, tmp_path / "kitchen.json"


def test_kitchen_service_enforces_fifo_and_completes_order(tmp_path):
    order, _, _, kitchen, _ = _create_kitchen_workflow(tmp_path)
    requests = kitchen.list_requests()

    with pytest.raises(ValueError, match="đầu hàng đợi"):
        kitchen.start(order.order_id, requests[1].item_code)

    kitchen.start(order.order_id, requests[0].item_code)
    kitchen.complete(order.order_id, requests[0].item_code)
    assert kitchen.current() == requests[1]

    kitchen.start(order.order_id, requests[1].item_code)
    kitchen.complete(order.order_id, requests[1].item_code)

    assert kitchen.current() is None
    assert order.status == "COMPLETED"


def test_failed_kitchen_persistence_restores_order_status_and_fifo(tmp_path, monkeypatch):
    order, orders, queue, kitchen, kitchen_path = _create_kitchen_workflow(tmp_path)
    first = kitchen.current()
    kitchen.start(order.order_id, first.item_code)

    save_state = kitchen.repository.save_state
    fail_once = True

    def fail_first_save(requests, queued):
        nonlocal fail_once
        if fail_once:
            fail_once = False
            raise OSError("kitchen file is not writable")
        save_state(requests, queued)

    monkeypatch.setattr(kitchen.repository, "save_state", fail_first_save)
    with pytest.raises(OSError, match="kitchen file is not writable"):
        kitchen.complete(order.order_id, first.item_code)

    assert order.status == "IN_PROGRESS"
    assert [request.item_code for request in queue.list_requests()] == ["F001", "F002"]
    assert first.status == "COOKING"
    assert json.loads(kitchen_path.read_text(encoding="utf-8"))["queue"] == [
        {"order_id": order.order_id, "item_code": "F001"},
        {"order_id": order.order_id, "item_code": "F002"},
    ]
    assert json.loads((tmp_path / "orders.json").read_text(encoding="utf-8"))[0]["status"] == "IN_PROGRESS"


def test_resending_order_to_kitchen_does_not_duplicate_requests(tmp_path):
    menu = MenuService(tmp_path / "menu.json")
    menu.add_item("F001", "Phở bò", 45000)
    queue = OrderQueue()
    orders = OrderService(menu, queue, tmp_path / "orders.json")
    order = orders.create_order()
    orders.add_item(order.order_id, "F001", 1)

    orders.send_to_kitchen(order.order_id)
    with pytest.raises(ValueError, match="đang ở trạng thái NEW"):
        orders.send_to_kitchen(order.order_id)

    assert order.status == "IN_PROGRESS"
    assert queue.size() == 1
    assert queue.peek().order_id == order.order_id


def test_kitchen_service_restores_queue_order_and_status(tmp_path):
    order, orders, _, kitchen, storage_path = _create_kitchen_workflow(tmp_path)
    first_request = kitchen.current()
    kitchen.start(order.order_id, first_request.item_code)

    restored_queue = OrderQueue()
    restored = KitchenService(restored_queue, storage_path, orders)

    assert [request.item_code for request in restored.list_requests()] == [
        "F001",
        "F002",
    ]
    assert restored.current().item_code == "F001"
    assert restored.current().status == "COOKING"
    assert restored.list_requests()[1].status == "NEW"


def test_cancelling_order_removes_and_persists_kitchen_requests(tmp_path):
    order, orders, queue, kitchen, storage_path = _create_kitchen_workflow(tmp_path)

    orders.cancel_order(
        order.order_id,
        "Khách đổi ý",
        SimpleNamespace(role="Quản lý"),
    )

    assert order.status == "CANCELLED"
    assert queue.is_empty()
    restored = KitchenService(OrderQueue(), storage_path, orders)
    assert restored.current() is None
    assert restored.list_requests() == []
