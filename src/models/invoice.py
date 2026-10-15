"""Mô hình hóa đơn."""
class Invoice:
    def __init__(self, order_id, total):
        self.order_id = order_id
        self.total = total
