from src.models.order import Order
from src.ui.presenters import menu_item_view, order_view


def test_order_view_maps_domain_fields_and_statuses():
    order = Order("DH001", "Bàn 1", status="COMPLETED")
    order.add_line("F001", "Phở bò", 2, 45000)

    view = order_view(order)

    assert view["id"] == "DH001"
    assert view["table"] == "Bàn 1"
    assert view["status"] == "READY"
    assert view["items"] == [{
        "code": "F001",
        "item_id": "F001",
        "name": "Phở bò",
        "price": 45000,
        "quantity": 2,
    }]
    assert view["total"] == 90000


def test_menu_item_view_supports_domain_objects():
    from src.models.menu_item import MenuItem

    view = menu_item_view(MenuItem("F001", "Phở bò", 45000))

    assert view == {
        "item_id": "F001",
        "code": "F001",
        "name": "Phở bò",
        "price": 45000,
        "is_active": True,
    }