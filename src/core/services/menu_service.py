"""Nghiệp vụ thực đơn."""
class MenuService:
    def __init__(self, menu_map):
        self.menu_map = menu_map
    def add_item(self, item):
        self.menu_map.put(item.item_id, item)
    def find_item(self, item_id):
        return self.menu_map.get(item_id)
