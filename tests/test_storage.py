import pytest
import json

from src.kitchen.queue import OrderQueue
from src.kitchen.repository import KitchenRepository
from src.kitchen.service import KitchenService
from src.menu.model import MenuItem
from src.menu.repository import MenuRepository
from src.menu.service import MenuService
from src.orders.repository import OrderRepository
from src.orders.service import OrderService
from src.payments.payment_repository import PaymentRepository
from src.payments.service import PaymentService
from src.shared.repository import RepositoryDataError
from src.storage.json_storage import InvalidJsonFileError, JsonStorage, StorageManager
from src.tables.repository import TableRepository


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


def test_menu_repository_seeds_live_menu_once(tmp_path):
    data_dir = tmp_path / "data"
    storage = StorageManager(data_dir)
    seed_menu = storage.menu_seed_storage.load(default=[])

    repository = MenuRepository(
        storage.menu_storage,
        seed_storage=storage.menu_seed_storage,
        legacy_storage=storage.legacy_menu_storage,
    )
    assert repository.list_all()

    live_menu = [dict(seed_menu[0], name="Món đã chỉnh sửa")]
    storage.menu_storage.save(live_menu)
    reloaded_storage = StorageManager(data_dir)

    reloaded_repository = MenuRepository(
        reloaded_storage.menu_storage,
        seed_storage=reloaded_storage.menu_seed_storage,
        legacy_storage=reloaded_storage.legacy_menu_storage,
    )
    assert reloaded_storage.menu_storage.load() == live_menu
    assert len(reloaded_repository.list_all()) == len(live_menu)
    assert reloaded_storage.menu_seed_storage.load() == seed_menu


def test_services_start_with_missing_data_files(tmp_path):
    storage = StorageManager(tmp_path / "data")
    menu = MenuService(MenuRepository(
        storage.menu_storage,
        seed_storage=storage.menu_seed_storage,
        legacy_storage=storage.legacy_menu_storage,
    ))
    queue = OrderQueue()
    orders = OrderService(
        menu=menu,
        queue=queue,
        storage_or_path=OrderRepository(storage.orders_storage),
    )
    kitchen = KitchenService(queue, KitchenRepository(storage.kitchen_storage), orders)
    payments = PaymentService(orders, PaymentRepository(storage.payments_storage))

    assert len(menu.list_items()) == 3
    assert orders.list_orders() == []
    assert kitchen.list_requests() == []
    assert payments.list_payments() == []


def test_malformed_json_is_reported_and_not_overwritten(tmp_path):
    storage = JsonStorage(tmp_path / "menu.json")
    invalid_content = "{ invalid json"
    storage.file_path.write_text(invalid_content, encoding="utf-8")

    with pytest.raises(InvalidJsonFileError, match="line 1, column"):
        MenuRepository(storage).list_all()

    assert storage.file_path.read_text(encoding="utf-8") == invalid_content


def test_empty_json_file_is_reported_without_replacement(tmp_path):
    storage = JsonStorage(tmp_path / "empty.json")
    storage.file_path.write_text("", encoding="utf-8")

    with pytest.raises(InvalidJsonFileError):
        storage.load(default=[])

    assert storage.file_path.read_text(encoding="utf-8") == ""


def test_failed_json_write_preserves_previous_file(tmp_path, monkeypatch):
    storage = JsonStorage(tmp_path / "menu.json")
    storage.save([{"code": "F001", "name": "Phở", "price": 45000}])
    original = storage.file_path.read_text(encoding="utf-8")

    def fail_dump(*_args, **_kwargs):
        raise OSError("disk full")

    monkeypatch.setattr(json, "dump", fail_dump)
    with pytest.raises(OSError, match="disk full"):
        storage.save([{"code": "F002", "name": "Bánh mì", "price": 25000}])

    assert storage.file_path.read_text(encoding="utf-8") == original
    assert list(tmp_path.glob(".*.tmp")) == []


def test_repository_rejects_missing_required_fields(tmp_path):
    storage = JsonStorage(tmp_path / "users.json")
    storage.save([{"username": "missing-password"}])

    from src.users.repository import UserRepository

    with pytest.raises(ValueError, match="password_hash"):
        UserRepository(storage).list_all()


@pytest.mark.parametrize(
    "record, message",
    [
        ({"code": "F001", "name": "Phở", "price": True}, "numeric price"),
        ({"code": "F001", "name": "Phở", "price": 45000, "is_active": "false"}, "boolean"),
    ],
)
def test_menu_repository_rejects_wrong_field_types_without_overwriting(
    tmp_path, record, message
):
    storage = JsonStorage(tmp_path / "menu.json")
    storage.save([record])

    with pytest.raises(RepositoryDataError, match=message):
        MenuRepository(storage).list_all()

    assert storage.load() == [record]


def test_order_repository_rejects_wrong_quantity_type(tmp_path):
    storage = JsonStorage(tmp_path / "orders.json")
    orders = [{
        "order_id": "DH001",
        "items": [{
            "item_code": "F001",
            "item_name": "Phở",
            "quantity": 1.5,
            "unit_price": 45000,
        }],
    }]
    storage.save(orders)

    with pytest.raises(RepositoryDataError, match="positive integer quantity"):
        OrderRepository(storage).list_all()

    assert storage.load() == orders


def test_kitchen_repository_rejects_wrong_quantity_type(tmp_path):
    storage = JsonStorage(tmp_path / "kitchen.json")
    kitchen_data = {
        "requests": [{
            "order_id": "DH001",
            "item_code": "F001",
            "item_name": "Phở",
            "quantity": "2",
            "status": "NEW",
        }],
        "queue": [{"order_id": "DH001", "item_code": "F001"}],
    }
    storage.save(kitchen_data)

    with pytest.raises(RepositoryDataError, match="positive integer quantity"):
        KitchenRepository(storage).load_state()

    assert storage.load() == kitchen_data


def test_kitchen_repository_rejects_duplicate_persisted_requests(tmp_path):
    storage = JsonStorage(tmp_path / "kitchen.json")
    duplicate = {
        "order_id": "DH001",
        "item_code": "F001",
        "item_name": "Phở",
        "quantity": 1,
        "status": "NEW",
    }
    kitchen_data = {
        "requests": [duplicate, duplicate],
        "queue": [{"order_id": "DH001", "item_code": "F001"}],
    }
    storage.save(kitchen_data)

    with pytest.raises(RepositoryDataError, match="duplicate request"):
        KitchenRepository(storage).load_state()

    assert storage.load() == kitchen_data


def test_kitchen_repository_rejects_non_string_status_without_overwriting(tmp_path):
    storage = JsonStorage(tmp_path / "kitchen.json")
    kitchen_data = {
        "requests": [{
            "order_id": "DH001",
            "item_code": "F001",
            "item_name": "Phở",
            "quantity": 1,
            "status": ["NEW"],
        }],
        "queue": [{"order_id": "DH001", "item_code": "F001"}],
    }
    storage.save(kitchen_data)

    with pytest.raises(RepositoryDataError, match="invalid status"):
        KitchenRepository(storage).load_state()

    assert storage.load() == kitchen_data


def test_payment_repository_rejects_unknown_status_without_overwriting(tmp_path):
    storage = JsonStorage(tmp_path / "payments.json")
    payments = [{
        "payment_id": "TT001",
        "order_id": "DH001",
        "amount": 45000,
        "status": "FAILED-BUT-UNSUPPORTED",
    }]
    storage.save(payments)

    with pytest.raises(RepositoryDataError, match="Trạng thái thanh toán không hợp lệ"):
        PaymentRepository(storage).list_all()

    assert storage.load() == payments


def test_menu_repository_crud_search_and_reload(tmp_path):
    repository = MenuRepository(tmp_path / "menu.json")
    item = repository.add(MenuItem(code="F001", name="Phở bò", price=45000))

    assert repository.find_by_code("f001").code == item.code
    assert [result.code for result in repository.search_items("PHỞ")] == ["F001"]

    item.update(name="Phở đặc biệt", price=50000)
    repository.update(item)
    reloaded = MenuRepository(tmp_path / "menu.json")
    assert reloaded.find_by_code("F001").name == "Phở đặc biệt"

    assert reloaded.delete("F001") is True
    assert reloaded.delete("F001") is False
    assert reloaded.list_all() == []


def test_table_repository_initializes_and_updates_legacy_mapping(tmp_path):
    storage = JsonStorage(tmp_path / "tables.json")
    repository = TableRepository(storage)

    assert repository.find_by_id("Bàn 1") == "Trống"
    repository.update("Bàn 1", "Đang phục vụ")
    assert TableRepository(storage).find_by_id("Bàn 1") == "Đang phục vụ"
    assert repository.search("Bàn 1") == {
        "Bàn 1": "Đang phục vụ",
        "Bàn 10": "Trống",
    }
    assert repository.delete("Bàn 1") is True
    assert repository.find_by_id("Bàn 1") is None


def test_table_repository_does_not_replace_invalid_root_data(tmp_path):
    storage = JsonStorage(tmp_path / "tables.json")
    storage.save(None)

    with pytest.raises(RepositoryDataError, match="JSON object"):
        TableRepository(storage).list_all()

    assert storage.load() is None
