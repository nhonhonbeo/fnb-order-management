from src.orders.model import Order
from src.shared.data_structures.hash_map import HashMap
from src.ui.presenters import menu_item_view, order_view


def test_order_view_maps_domain_fields_and_statuses():
    order = Order("DH001", "Bàn 1", status="COMPLETED")
    order.add_line("F001", "Phở bò", 2, 45000)

    view = order_view(order)

    assert isinstance(view, HashMap)
    assert isinstance(view["items"][0], HashMap)
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
    from src.menu.model import MenuItem

    view = menu_item_view(MenuItem("F001", "Phở bò", 45000))

    assert isinstance(view, HashMap)
    assert view == {
        "item_id": "F001",
        "code": "F001",
        "name": "Phở bò",
        "price": 45000,
        "is_active": True,
    }


def test_presenters_accept_standard_mappings():
    view = order_view({
        "id": "DH002",
        "table": "Bàn 2",
        "status": "IN_PROGRESS",
        "items": [{
            "item_code": "F002",
            "item_name": "Bún bò",
            "unit_price": 50000,
            "quantity": 1,
        }],
    })

    assert view["id"] == "DH002"
    assert view["status"] == "COOKING"
    assert view["total"] == 50000
    assert view["items"][0]["code"] == "F002"