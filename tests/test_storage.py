from src.core.storage import JsonStorage


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
