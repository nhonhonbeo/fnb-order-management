"""Queue FIFO khởi đầu; có thể tối ưu thêm khi học cấu trúc dữ liệu."""
class Queue:
    def __init__(self):
        self._items = []
    def enqueue(self, item):
        self._items.append(item)
    def dequeue(self):
        if not self._items:
            raise IndexError("Queue is empty")
        return self._items.pop(0)
    def is_empty(self):
        return len(self._items) == 0
    def size(self):
        return len(self._items)
