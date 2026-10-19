import pytest

from src.core.queues.order_queue import OrderQueue
from src.core.services.kitchen_service import KitchenService
from src.core.services.menu_service import MenuService
from src.core.services.order_service import OrderService
from src.core.services.payment_service import PaymentService
from src.core.storage import JsonStorage, StorageManager


def test_save_and_load_json_with_utf8_and_nested_path(tmp_path):
    file_path = tmp_path / "data" / "menu.json"
    storage = JsonStorage(file_path)
    menu = [{"item_id": "F001", "name": "Phở bò", "price": 45000}]

    storage.save(menu)

    assert storage.load() == menu
    assert "Phở bò" in file_path.read_text(encoding="utf-8")


def test_load_missing_file_returns_default(tmp_path):
    default = []

    assert JsonStorage(tmp_path / "missing.json").load(default) is default


def test_storage_manager_seeds_live_menu_once(tmp_path):
    data_dir = tmp_path / "data"
    storage = StorageManager(data_dir)
    seed_menu = storage.menu_seed_storage.load(default=[])

    assert storage.menu_storage.load() == seed_menu

    live_menu = [dict(seed_menu[0], name="Món đã chỉnh sửa")]
    storage.menu_storage.save(live_menu)
    reloaded_storage = StorageManager(data_dir)

    assert reloaded_storage.menu_storage.load() == live_menu
    assert reloaded_storage.menu_seed_storage.load() == seed_menu


@pytest.mark.parametrize("corrupt", [False, True], ids=["missing", "invalid-json"])
def test_services_start_with_missing_or_corrupt_data_files(tmp_path, corrupt):
    storage = StorageManager(tmp_path / "data")
    storages = [
        storage.menu_storage,
        storage.orders_storage,
        storage.payments_storage,
        storage.kitchen_storage,
    ]

    if corrupt:
        for data_storage in storages:
            data_storage.file_path.write_text("{ invalid json", encoding="utf-8")

    menu = MenuService(storage.menu_storage)
    queue = OrderQueue()
    orders = OrderService(menu=menu, queue=queue, storage_or_path=storage.orders_storage)
    kitchen = KitchenService(queue, storage.kitchen_storage, orders)
    payments = PaymentService(orders, storage.payments_storage)

    assert len(menu.list_items()) == (0 if corrupt else 3)
    assert orders.list_orders() == []
    assert kitchen.list_requests() == []
    assert payments.list_payments() == []
