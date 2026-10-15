"""Nghiệp vụ hàng đợi bếp."""
class KitchenService:
    def __init__(self, kitchen_queue):
        self.kitchen_queue = kitchen_queue
    def send_to_kitchen(self, order_item):
        self.kitchen_queue.enqueue(order_item)
    def next_item(self):
        return self.kitchen_queue.dequeue()
