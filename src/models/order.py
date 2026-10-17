"""Mô hình đơn hàng."""
class Order:
    def __init__(self, order_id, table_id):
        self.order_id = order_id
        self.table_id = table_id
        self.items = []
        self.status = "NEW"

        
"""Các lớp dùng để lưu thông tin đơn hàng."""

# Lớp lưu thông tin của một món ăn trong đơn hàng
class OrderItem:
        # Hàm khởi tạo, chạy khi tạo một đối tượng OrderItem

    def __init__(self, item_code, item_name, quantity, unit_price):
        self.item_code = item_code
        self.item_name = item_name
        self.quantity = quantity
        self.unit_price = unit_price

  # Hàm tính thành tiền của món ăn
    def subtotal(self):
        return self.quantity * self.unit_price


# Lớp lưu thông tin của một đơn hàng
class Order:
     # Hàm khởi tạo đơn hàng
    def __init__(self, order_id, table_id=None):
        self.order_id = order_id
        self.table_id = table_id
        self.items = []
        self.status = "NEW"

 # Hàm thêm một món ăn vào đơn hàng
    def add_line(self, item_code, item_name, quantity, unit_price):
        # Duyệt qua từng món đã có trong đơn hàng. Nếu món đã có thì cộng thêm số lượng
        for item in self.items:
            if item.item_code == item_code:
                item.quantity += quantity
                return

        # Nếu chưa có món này thì tạo đối tượng OrderItem mới
        self.items.append(
            OrderItem(item_code, item_name, quantity, unit_price)
        )

# Hàm tính tổng tiền của toàn bộ đơn hàng
    def total(self):
        total_money = 0
        for item in self.items:
            total_money += item.subtotal()
        return total_money
