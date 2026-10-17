from src.core.services.auth_service import AuthService


def test_auth_service_seeds_default_users(tmp_path):
    storage_path = tmp_path / "data" / "users.json"
    service = AuthService(storage_path)

    users = service.get_users()
    assert len(users) == 2
    usernames = [u.username for u in users]
    assert "admin" in usernames
    assert "nhanvien" in usernames


def test_auth_service_authenticate_success_and_failure(tmp_path):
    storage_path = tmp_path / "data" / "users.json"
    service = AuthService(storage_path)

    admin_user = service.authenticate("admin", "admin123")
    assert admin_user is not None
    assert admin_user.username == "admin"
    assert admin_user.role == "Quản lý"

    wrong_pw_user = service.authenticate("admin", "wrong_pass")
    assert wrong_pw_user is None

    unknown_user = service.authenticate("ghost", "pass123")
    assert unknown_user is None


def test_auth_service_register_new_user(tmp_path):
    storage_path = tmp_path / "data" / "users.json"
    service = AuthService(storage_path)

    success, msg, user = service.register(
        username="lethib",
        password="password123",
        full_name="Lê Thị B",
        role="Thu ngân",
    )
    assert success is True
    assert user is not None
    assert user.username == "lethib"
    assert user.role == "Thu ngân"

    # Authenticate newly registered user
    authenticated = service.authenticate("lethib", "password123")
    assert authenticated is not None
    assert authenticated.full_name == "Lê Thị B"

    # Duplicate registration fails
    dup_success, dup_msg, dup_user = service.register(
        username="lethib",
        password="password456",
        full_name="Lê Thị B khác",
    )
    assert dup_success is False
    assert "đã tồn tại" in dup_msg


def test_auth_service_validation_errors(tmp_path):
    storage_path = tmp_path / "data" / "users.json"
    service = AuthService(storage_path)

    # Empty username
    ok, msg, _ = service.register("", "123456", "Tên")
    assert not ok

    # Short username
    ok, msg, _ = service.register("ab", "123456", "Tên")
    assert not ok

    # Short password
    ok, msg, _ = service.register("user_abc", "123", "Tên")
    assert not ok

    # Empty full name
    ok, msg, _ = service.register("user_abc", "123456", "")
    assert not ok
