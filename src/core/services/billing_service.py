"""Nghiệp vụ tính hóa đơn."""
class BillingService:
    def calculate_total(self, order_items):
        return sum(item["price"] * item["quantity"] for item in order_items)
