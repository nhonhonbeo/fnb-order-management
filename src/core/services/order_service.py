"""Nghiệp vụ đơn hàng."""
class OrderService:
    def __init__(self):
        self.orders = {}
    def create_order(self, order):
        self.orders[order.order_id] = order
        return order
