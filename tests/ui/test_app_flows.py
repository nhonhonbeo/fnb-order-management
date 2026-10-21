from __future__ import annotations

import pytest

from tests.ui.conftest import element_by_key


def _run_without_exceptions(app):
    assert not app.exception, [exception.message for exception in app.exception]
    return app


def _navigate(app, page):
    element_by_key(app, "radio", "navigation_widget").set_value(page).run()
    return _run_without_exceptions(app)


def _texts(elements):
    return [element.value for element in elements]


def test_login_rejects_bad_password_accepts_valid_and_logs_out(isolated_app):
    app = isolated_app
    element_by_key(app, "text_input", "login_username").set_value("admin")
    element_by_key(app, "text_input", "login_password").set_value("incorrect")
    element_by_key(app, "button", "login_submit").click().run()

    assert any("không chính xác" in message.lower() for message in _texts(app.error))
    assert app.session_state.authenticated_user is None

    element_by_key(app, "text_input", "login_password").set_value("admin123")
    element_by_key(app, "button", "login_submit").click().run()
    assert app.session_state.authenticated_user.role == "Quản lý"
    assert any("Quản lý bàn" in title for title in _texts(app.title))

    element_by_key(app, "button", "logout_button").click().run()
    assert app.session_state.authenticated_user is None
    assert any(button.key == "login_submit" for button in app.button)


def test_registration_valid_duplicate_and_missing_fields(isolated_app):
    app = isolated_app
    element_by_key(app, "button", "register_submit").click().run()
    assert any("tên đăng nhập" in message.lower() for message in _texts(app.error))

    element_by_key(app, "text_input", "register_username").set_value("uitestuser")
    element_by_key(app, "text_input", "register_password").set_value("password123")
    element_by_key(app, "text_input", "register_confirm_password").set_value("password123")
    element_by_key(app, "button", "register_submit").click().run()
    assert any("họ và tên" in message.lower() for message in _texts(app.error))

    element_by_key(app, "text_input", "register_full_name").set_value("UI Test User")
    element_by_key(app, "button", "register_submit").click().run()
    assert app.session_state.authenticated_user.username == "uitestuser"
    assert any(button.key == "logout_button" for button in app.button)

    element_by_key(app, "button", "logout_button").click().run()
    element_by_key(app, "text_input", "register_full_name").set_value("UI Test User")
    element_by_key(app, "text_input", "register_username").set_value("uitestuser")
    element_by_key(app, "text_input", "register_password").set_value("password123")
    element_by_key(app, "text_input", "register_confirm_password").set_value("password123")
    element_by_key(app, "button", "register_submit").click().run()
    assert any("đã tồn tại" in message for message in _texts(app.error))
    assert app.session_state.auth_service.get_users()


@pytest.mark.parametrize(
    ("role", "can_see_revenue", "can_see_menu"),
    [
        ("Quản lý", True, True),
        ("Thu ngân", True, False),
        ("Đầu bếp", False, False),
        ("Nhân viên", False, True),
    ],
)
def test_navigation_and_page_controls_follow_role_permissions(
    isolated_app,
    login_as,
    role,
    can_see_revenue,
    can_see_menu,
):
    app = login_as(isolated_app, role)
    options = element_by_key(app, "radio", "navigation_widget").options
    assert ("Báo cáo doanh thu" in options) is can_see_revenue
    assert ("Thực đơn" in options) is can_see_menu
    assert any("Quản lý bàn" in value for value in _texts(app.subheader)) is (
        role == "Quản lý"
    )
    assert any(
        button.key is not None and button.key.startswith("delete_table_")
        for button in app.button
    ) is (role == "Quản lý")

    if can_see_menu:
        _navigate(app, "Thực đơn")
        editor_visible = any(
            "Thêm món mới" in value for value in _texts(app.subheader)
        )
        assert editor_visible is (role == "Quản lý")

    if can_see_revenue:
        _navigate(app, "Báo cáo doanh thu")
        assert any("Doanh thu" in metric.label for metric in app.metric)


def test_manager_can_add_edit_and_delete_menu_item(isolated_app, login_as):
    app = login_as(isolated_app, "Quản lý")
    _navigate(app, "Thực đơn")

    element_by_key(app, "text_input", "new_menu_code").set_value("UITEST01")
    element_by_key(app, "text_input", "new_menu_name").set_value("Món UI kiểm thử")
    element_by_key(app, "number_input", "new_menu_price").set_value(33000)
    element_by_key(app, "button", "add_menu_submit").click().run()
    assert app.session_state.menu_service.get_item("UITEST01").name == "Món UI kiểm thử"
    assert any("Món UI kiểm thử" in value for value in _texts(app.markdown))

    element_by_key(app, "text_input", "edit_name_UITEST01").set_value("Món UI đã sửa")
    element_by_key(app, "number_input", "edit_price_UITEST01").set_value(35000)
    element_by_key(app, "button", "save_menu_UITEST01").click().run()
    assert app.session_state.menu_service.get_item("UITEST01").price == 35000
    assert app.session_state.menu_service.get_item("UITEST01").name == "Món UI đã sửa"
    assert any("Món UI đã sửa" in value for value in _texts(app.markdown))

    element_by_key(app, "button", "delete_UITEST01").click().run()
    assert app.session_state.menu_service.get_item("UITEST01") is None
    assert all("Món UI đã sửa" not in value for value in _texts(app.markdown))


def test_manager_can_add_and_confirm_deletion_of_table(isolated_app, login_as):
    app = login_as(isolated_app, "Quản lý")
    element_by_key(app, "text_input", "new_table_name").set_value("Bàn UI")
    element_by_key(app, "button", "add_table_submit").click().run()
    assert app.session_state.table_service.list_tables()["Bàn UI"] == "Trống"
    assert any("Đã thêm bàn 'Bàn UI'" in value for value in _texts(app.success))
    assert any(button.key == "delete_table_Bàn UI" for button in app.button)

    element_by_key(app, "button", "delete_table_Bàn UI").click().run()
    assert any("Bạn có chắc muốn xoá bàn 'Bàn UI'" in value for value in _texts(app.warning))
    element_by_key(app, "button", "cancel_delete_table").click().run()
    assert not any("Bạn có chắc muốn xoá bàn 'Bàn UI'" in value for value in _texts(app.warning))

    element_by_key(app, "button", "delete_table_Bàn UI").click().run()
    element_by_key(app, "button", "confirm_delete_table").click().run()
    assert "Bàn UI" not in app.session_state.table_service.list_tables()
    assert any("Đã xoá bàn 'Bàn UI'" in value for value in _texts(app.success))

    _navigate(app, "Tạo đơn hàng")
    table_options = element_by_key(app, "selectbox", "new_order_table").options
    assert "Bàn UI" not in table_options


def test_order_edit_cancel_kitchen_fifo_and_payment_flow(isolated_app, login_as):
    app = login_as(isolated_app, "Quản lý")
    _navigate(app, "Tạo đơn hàng")
    element_by_key(app, "selectbox", "new_order_table").set_value("Bàn 1")
    item_select = element_by_key(app, "selectbox", "new_order_menu_item")
    item_select.set_value(next(option for option in item_select.options if "F001" in option))
    element_by_key(app, "number_input", "new_order_quantity").set_value(1)
    element_by_key(app, "button", "add_to_cart").click().run()
    item_select = element_by_key(app, "selectbox", "new_order_menu_item")
    item_select.set_value(next(option for option in item_select.options if "F002" in option))
    element_by_key(app, "button", "add_to_cart").click().run()
    assert any("Phở bò" in value for value in _texts(app.markdown))
    assert any("Bánh mì" in value for value in _texts(app.markdown))

    element_by_key(app, "button", "create_order_submit").click().run()
    order = app.session_state.order_service.list_orders()[-1]
    assert order.status == "IN_PROGRESS"
    assert any(order.order_id in item.label for item in app.expander)
    assert app.session_state.kitchen_service.current().order_id == order.order_id
    assert [
        request.item_code
        for request in app.session_state.kitchen_service.list_requests()
        if request.order_id == order.order_id
    ] == ["F001", "F002"]

    _navigate(app, "Bếp & thanh toán")
    element_by_key(
        app,
        "button",
        f"cook_{order.order_id}_F001",
    ).click().run()
    assert app.session_state.kitchen_service.current().status == "COOKING"
    element_by_key(
        app,
        "button",
        f"ready_{order.order_id}_F001",
    ).click().run()
    assert order.status == "IN_PROGRESS"
    assert app.session_state.kitchen_service.current().item_code == "F002"
    element_by_key(
        app,
        "button",
        f"cook_{order.order_id}_F002",
    ).click().run()
    element_by_key(
        app,
        "button",
        f"ready_{order.order_id}_F002",
    ).click().run()
    assert order.status == "COMPLETED"
    assert any(
        "Chưa có món nào chờ chế biến" in value
        for value in _texts(app.info)
    )

    invoice_count = len(app.session_state.billing_service.list_invoices())
    _navigate(app, "Bếp & thanh toán")
    element_by_key(app, "button", "confirm_payment").click().run()
    assert order.status == "PAID"
    assert len(app.session_state.billing_service.list_invoices()) == invoice_count + 1
    assert app.session_state.table_service.is_available("Bàn 1")
    assert any(
        "Hiện không có đơn hàng nào chờ thanh toán" in value
        for value in _texts(app.info)
    )


def test_order_edit_and_cancel_controls_are_wired_to_services(isolated_app, login_as):
    app = login_as(isolated_app, "Quản lý")
    _navigate(app, "Tạo đơn hàng")
    element_by_key(app, "selectbox", "new_order_table").set_value("Bàn 2")
    item_select = element_by_key(app, "selectbox", "new_order_menu_item")
    item_select.set_value(next(option for option in item_select.options if "F001" in option))
    element_by_key(app, "button", "add_to_cart").click().run()
    element_by_key(app, "button", "create_order_submit").click().run()
    order = app.session_state.order_service.list_orders()[-1]

    element_by_key(app, "text_area", f"edit_note_{order.order_id}").set_value("Không hành")
    element_by_key(app, "button", f"save_order_{order.order_id}").click().run()
    assert order.note == "Không hành"
    assert any("Không hành" in value for value in _texts(app.markdown))

    element_by_key(app, "button", f"show_cancel_{order.order_id}").click().run()
    element_by_key(app, "text_input", f"cancel_reason_{order.order_id}").set_value("Khách đổi ý")
    element_by_key(app, "button", f"confirm_cancel_{order.order_id}").click().run()
    assert order.status == "CANCELLED"
    assert order.cancel_reason == "Khách đổi ý"
    assert app.session_state.table_service.is_available("Bàn 2")
    assert all(
        request.order_id != order.order_id
        for request in app.session_state.kitchen_service.list_requests()
    )
    assert any(f"Đơn {order.order_id} đã được huỷ" in value for value in _texts(app.success))
