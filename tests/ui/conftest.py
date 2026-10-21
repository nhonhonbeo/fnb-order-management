from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

import pytest
from streamlit.testing.v1 import AppTest

import src.ui.bootstrap as bootstrap


ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def isolated_app(tmp_path, monkeypatch):
    source_data = ROOT / "data"
    copied_data = tmp_path / "data"
    shutil.copytree(source_data, copied_data)
    original_files = {
        path.relative_to(source_data): path.read_bytes()
        for path in source_data.rglob("*")
        if path.is_file()
    }
    (copied_data / "orders.json").write_text("[]\n", encoding="utf-8")
    (copied_data / "kitchen.json").write_text(
        '{"requests": [], "queue": []}\n',
        encoding="utf-8",
    )
    (copied_data / "invoices.json").write_text("[]\n", encoding="utf-8")
    (copied_data / "payments.json").write_text("[]\n", encoding="utf-8")
    (copied_data / "tables.json").write_text(
        json.dumps(
            {f"Bàn {index}": "Trống" for index in range(1, 11)},
            ensure_ascii=False,
            indent=2,
        ) + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(bootstrap, "DATA_DIR", copied_data)

    app = AppTest.from_file(ROOT / "src" / "app.py", default_timeout=30).run()
    assert not app.exception, [exception.message for exception in app.exception]
    yield app

    assert {
        path.relative_to(source_data): path.read_bytes()
        for path in source_data.rglob("*")
        if path.is_file()
    } == original_files


def element_by_key(app: AppTest, collection: str, key: str) -> Any:
    matches = [
        element
        for element in getattr(app, collection)
        if getattr(element, "key", None) == key
    ]
    assert len(matches) == 1, f"Expected one {collection} element with key {key!r}"
    return matches[0]


@pytest.fixture
def login_as():
    def login(app: AppTest, role: str) -> AppTest:
        accounts = {
            "Quản lý": ("admin", "admin123"),
            "Nhân viên": ("nhanvien", "123456"),
        }
        if role in accounts:
            username, password = accounts[role]
        else:
            username = {
                "Thu ngân": "ui_cashier",
                "Đầu bếp": "ui_chef",
            }[role]
            success, message, _ = app.session_state.auth_service.register(
                username=username,
                password="ui-test-password",
                full_name=f"Người dùng {role}",
                role=role,
            )
            assert success, message
            password = "ui-test-password"

        element_by_key(app, "text_input", "login_username").set_value(username)
        element_by_key(app, "text_input", "login_password").set_value(password)
        element_by_key(app, "button", "login_submit").click().run()
        assert not app.exception, [exception.message for exception in app.exception]
        assert app.session_state.authenticated_user.role == role
        return app

    return login
