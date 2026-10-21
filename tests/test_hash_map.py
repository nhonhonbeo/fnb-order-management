from src.shared.data_structures.hash_map import HashMap
from src.shared.data_structures.hash_table import HashTable


def test_hash_map_crud_and_resize():
    hmap = HashMap(initial_capacity=4)
    hmap.put("F001", "Phở bò")
    hmap.put("F002", "Bánh mì")
    hmap.put("F003", "Trà tắc")

    assert hmap.get("F001") == "Phở bò"
    assert hmap.get("F002") == "Bánh mì"
    assert hmap.get("F003") == "Trà tắc"
    assert hmap.get("F999") is None

    # Update value
    hmap.put("F001", "Phở bò đặc biệt")
    assert hmap.get("F001") == "Phở bò đặc biệt"

    # Resize trigger
    hmap.put("F004", "Cà phê sữa")
    hmap.put("F005", "Bún chả")
    assert hmap.get("F004") == "Cà phê sữa"
    assert hmap.get("F005") == "Bún chả"

    # Remove
    assert hmap.remove("F002") is True
    assert hmap.get("F002") is None
    assert hmap.remove("F002") is False


def test_hash_map_supports_mapping_access_and_defaults():
    hmap = HashMap()
    hmap.put("present", None)

    assert hmap["present"] is None
    assert hmap.get("missing", "fallback") == "fallback"
    assert "present" in hmap
    assert list(hmap) == ["present"]
    assert len(hmap) == 1
    assert hmap == {"present": None}


def test_hash_table_separate_chaining():
    ht = HashTable(capacity=3)
    ht.insert("K1", "Val1")
    ht.insert("K2", "Val2")
    ht.insert("K3", "Val3")
    ht.insert("K4", "Val4")

    assert ht.get("K1") == "Val1"
    assert ht.get("K4") == "Val4"
    assert ht.get("K99") is None

    # Update
    ht.insert("K1", "Val1_updated")
    assert ht.get("K1") == "Val1_updated"

    # Remove
    assert ht.remove("K2") is True
    assert ht.get("K2") is None
    assert ht.remove("K99") is False
