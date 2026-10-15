"""Mô hình đơn hàng."""
class Order:
    def __init__(self, order_id, table_id):
        self.order_id = order_id
        self.table_id = table_id
        self.items = []
        self.status = "NEW"
