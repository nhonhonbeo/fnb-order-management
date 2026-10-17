import pytest

from src.core.data_structures.queue import Queue
from src.core.order_queue import EmptyQueueError, KitchenRequest, OrderQueue


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
