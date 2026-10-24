"""Nghiệp vụ đơn hàng."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set

from src.kitchen.queue import KitchenRequest
from src.orders.repository import OrderRepository
from src.orders.model import Order, OrderItem
from src.users.permissions import can_cancel_order, can_edit_order


class OrderOperationRollbackError(RuntimeError):
    """Raised when an order operation fails and compensation is incomplete."""


class OrderService:
    def __init__(
        self,
        menu: Any = None,
        queue: Any = None,
        storage_or_path: Optional[Any] = None,
        table_service: Any = None,
        kitchen_service: Any = None,
    ):
        self.menu = menu
        self.queue = queue
        self.table_service = table_service
        self.kitchen_service = kitchen_service
        self.repository = (
            storage_or_path
            if isinstance(storage_or_path, OrderRepository)
            else OrderRepository(storage_or_path)
        )

        # Lưu tất cả đơn hàng vào dictionary
        self.orders: Dict[str, Order] = {}
        self.next_no = 1
        self.load()

    def load(self) -> None:
        """Đọc danh sách đơn hàng từ storage vào bộ nhớ."""
        self.orders = {order.order_id: order for order in self.repository.load()}

        max_no = 0
        for oid in self.orders.keys():
            if str(oid).startswith("DH") and str(oid)[2:].isdigit():
                max_no = max(max_no, int(str(oid)[2:]))
        self.next_no = max(self.next_no, max_no + 1)

    def save(self) -> None:
        """Lưu toàn bộ danh sách đơn hàng ra storage."""
        self.repository.save(self.orders.values())

    def create_order(self, table_id: Any = None) -> Order:
        order_id = "DH" + str(self.next_no).zfill(3)
        self.next_no += 1
        order = Order(order_id, table_id)
        self.orders[order_id] = order
        self.save()
        return order

    def get_order(self, order_id: str) -> Order:
        if order_id not in self.orders:
            raise ValueError("Không tìm thấy đơn hàng")
        return self.orders[order_id]

    def list_orders(self) -> List[Order]:
        return list(self.orders.values())

    def get_active_order_by_table(self, table_id: str) -> Order | None:
        normalized_table_id = table_id.strip() if isinstance(table_id, str) else ""
        if not normalized_table_id:
            return None
        matching_orders = [
            order for order in self.orders.values()
            if isinstance(order.table_id, str)
            and order.table_id.strip() == normalized_table_id
            and order.status not in {"PAID", "CANCELLED"}
        ]
        if len(matching_orders) > 1:
            raise ValueError(
                f"Có nhiều hơn một đơn đang hoạt động tại bàn '{normalized_table_id}'"
            )
        return matching_orders[0] if matching_orders else None

    def active_table_ids(self) -> set[str]:
        return {
            order.table_id.strip()
            for order in self.orders.values()
            if isinstance(order.table_id, str)
            and order.table_id.strip()
            and order.status not in {"PAID", "CANCELLED"}
        }

    def change_table(self, from_table_id: str, to_table_id: str) -> Order:
        if self.table_service is None:
            raise ValueError("Chưa kết nối dịch vụ bàn")

        with self.table_service.transaction():
            self.load()
            source_name = from_table_id.strip() if isinstance(from_table_id, str) else ""
            target_name = to_table_id.strip() if isinstance(to_table_id, str) else ""
            if not source_name:
                raise ValueError("Đơn không có table_id để đổi bàn")
            if not target_name:
                raise ValueError("Bàn đích không tồn tại")
            if source_name == target_name:
                raise ValueError("Không thể đổi sang chính bàn hiện tại")

            tables = self.table_service.list_tables()
            normalized_tables = {
                table_id.strip(): table_id for table_id in tables
            }
            source_table = normalized_tables.get(source_name)
            target_table = normalized_tables.get(target_name)
            if source_table is None:
                raise ValueError(f"Bàn nguồn '{source_name}' không tồn tại")
            if target_table is None:
                raise ValueError(f"Bàn đích '{target_name}' không tồn tại")

            matching_orders = [
                order for order in self.orders.values()
                if isinstance(order.table_id, str)
                and order.table_id.strip() == source_name
            ]
            active_orders = [
                order for order in matching_orders
                if order.status not in {"PAID", "CANCELLED"}
            ]
            if len(active_orders) > 1:
                raise ValueError(
                    f"Có nhiều hơn một đơn đang hoạt động tại bàn '{source_name}'"
                )
            if not active_orders:
                if any(order.status == "PAID" for order in matching_orders):
                    raise ValueError("Đơn tại bàn nguồn đã thanh toán")
                if any(order.status == "CANCELLED" for order in matching_orders):
                    raise ValueError("Đơn tại bàn nguồn đã bị hủy")
                raise ValueError(f"Bàn nguồn '{source_name}' không có đơn đang hoạt động")
            order = active_orders[0]
            if not order.table_id or not order.table_id.strip():
                raise ValueError("Đơn không có table_id để đổi bàn")
            if tables[target_table] != "Trống":
                raise ValueError(f"Bàn đích '{target_table}' đang có khách")

            original_orders = list(self.orders.values())
            original_tables = dict(tables)
            original_table_id = order.table_id
            try:
                self.table_service.reserve(target_table)
                order.table_id = target_table
                self.save()
                self.table_service.release(source_table)
            except Exception as error:
                rollback_errors = []
                order.table_id = original_table_id
                try:
                    self.repository.save_all(original_orders)
                    self.orders = {
                        original_order.order_id: original_order
                        for original_order in original_orders
                    }
                except Exception as rollback_error:
                    rollback_errors.append(rollback_error)
                try:
                    self.table_service.repository.save_all(original_tables)
                    self.table_service._tables = original_tables
                except Exception as rollback_error:
                    rollback_errors.append(rollback_error)
                if rollback_errors:
                    details = "; ".join(str(failure) for failure in rollback_errors)
                    raise OrderOperationRollbackError(
                        "Đổi bàn thất bại và không thể khôi phục đầy đủ trạng thái: "
                        f"{details}"
                    ) from error
                raise
            return order

    def set_kitchen_service(self, kitchen_service: Any) -> None:
        self.kitchen_service = kitchen_service

    def search_orders(
        self,
        keyword: str | None = None,
        status: str | None = None,
    ) -> List[Order]:
        """Tìm đơn theo một phần mã đơn và/hoặc trạng thái."""
        orders = self.list_orders()
        if keyword is not None:
            normalized_keyword = keyword.casefold()
            orders = [
                order for order in orders
                if normalized_keyword in order.order_id.casefold()
            ]
        if status is not None:
            orders = [order for order in orders if order.status == status]
        return orders

    def list_history(self) -> List[Order]:
        """Liệt kê đơn đã thanh toán hoặc hủy, mới nhất trước."""
        history = [
            order for order in self.orders.values()
            if order.status in {"PAID", "CANCELLED"}
        ]

        def sort_key(order: Order) -> tuple[int, float]:
            if not isinstance(order.created_at, str) or not order.created_at:
                return 1, 0
            try:
                created_at = datetime.fromisoformat(order.created_at)
            except ValueError:
                return 1, 0
            if created_at.tzinfo is None:
                created_at = created_at.replace(tzinfo=timezone.utc)
            return 0, -created_at.timestamp()

        return sorted(history, key=sort_key)

    def add_item(self, order_id: str, code: str, quantity: int) -> Order:
        order = self.get_order(order_id)

        if order.status != "NEW":
            raise ValueError("Không thể sửa đơn hàng này")

        self._validate_quantity(quantity)

        if self.menu is None:
            raise ValueError("Chưa kết nối thực đơn")

        item = self.menu.get_item(code)
        if item is None:
            raise ValueError("Không tìm thấy món ăn")
        if not item.is_active:
            raise ValueError("Món ăn đã ngừng kinh doanh")

        order.add_line(item.code, item.name, quantity, item.price)
        self.save()
        return order

    def remove_item(self, order_id: str, item_code: str) -> Order:
        """
        Hủy/xóa đúng MỘT món cụ thể khỏi đơn hàng khi đơn chưa gửi bếp (trạng thái NEW).
        """
        order = self.get_order(order_id)
        if order.status != "NEW":
            raise ValueError("Không thể hủy món vì bếp đã xác nhận nấu hoặc đơn đang được xử lý.")

        normalized_code = item_code.strip().upper()
        initial_len = len(order.items)
        
        order.items = [item for item in order.items if item.item_code != normalized_code]
        
        if len(order.items) == initial_len:
            raise ValueError(f"Không tìm thấy món có mã '{normalized_code}' trong đơn hàng.")

        self.save()
        
        if self.queue is not None:
            current_requests = self.queue.list_requests()
            updated_requests = [
                req for req in current_requests 
                if not (req.order_id == order_id and req.item_code == normalized_code)
            ]
            self.queue.replace_all(updated_requests)

        return order

    def update_item_quantity(self, order_id: str, item_code: str, new_quantity: int) -> Order:
        """
        Đổi số lượng của đúng MỘT món cụ thể khi đơn hàng ở trạng thái NEW.
        """
        order = self.get_order(order_id)
        if order.status != "NEW":
            raise ValueError("Không thể đổi số lượng món vì bếp đã xác nhận nấu hoặc đơn đang được xử lý.")

        self._validate_quantity(new_quantity)
        normalized_code = item_code.strip().upper()
        
        found = False
        for item in order.items:
            if item.item_code == normalized_code:
                item.quantity = new_quantity
                found = True
                break
                
        if not found:
            raise ValueError(f"Không tìm thấy món có mã '{normalized_code}' trong đơn hàng.")

        self.save()
        return order

    def add_to_cart(self, cart: List[Dict[str, Any]], code: str, quantity: int) -> None:
        """Validate a menu selection and add or increment it in the unsaved cart."""
        self._validate_quantity(quantity)
        if self.menu is None:
            raise ValueError("Chưa kết nối thực đơn")
        item = self.menu.get_item(code)
        if item is None:
            raise ValueError("Không tìm thấy món ăn")
        if not item.is_active:
            raise ValueError("Món ăn đã ngừng kinh doanh")

        existing = next(
            (line for line in cart if line.get("code", line.get("item_id")) == item.code),
            None,
        )
        if existing is not None:
            existing["quantity"] += quantity
            return
        cart.append({
            "item_id": item.code,
            "code": item.code,
            "name": item.name,
            "price": item.price,
            "quantity": quantity,
        })

    def calculate_cart_total(self, cart: List[Dict[str, Any]]) -> int:
        """Calculate the cart total from current menu prices."""
        if self.menu is None:
            raise ValueError("Chưa kết nối thực đơn")
        total = 0
        for line in cart:
            self._validate_quantity(line.get("quantity"))
            item = self.menu.get_item(line.get("code", line.get("item_id", "")))
            if item is None:
                raise ValueError("Không tìm thấy món ăn")
            total += item.price * line["quantity"]
        return total

    @staticmethod
    def _validate_quantity(quantity: Any) -> None:
        if not isinstance(quantity, int) or isinstance(quantity, bool) or quantity <= 0:
            raise ValueError("Số lượng phải là số nguyên lớn hơn 0")

    def create_order_from_cart(self, table_id: str, cart: List[Dict[str, Any]]) -> Order:
        """Validate and place a complete cart as an order (or append to active table order), sending new items to the kitchen."""
        if not cart:
            raise ValueError("Đơn phải có món")
        if self.menu is None:
            raise ValueError("Chưa kết nối thực đơn")
        if self.queue is None:
            raise ValueError("Chưa kết nối hàng đợi bếp")

        # Kiểm tra xem bàn đã có đơn hàng nào đang hoạt động chưa (gọi thêm món)
        active_order = self.get_active_order_by_table(table_id)

        resolved_items: Dict[str, tuple[Any, int]] = {}
        for line in cart:
            self._validate_quantity(line.get("quantity"))
            item = self.menu.get_item(line.get("code", line.get("item_id", "")))
            if item is None:
                raise ValueError("Không tìm thấy món ăn")
            if not item.is_active:
                raise ValueError("Món ăn đã ngừng kinh doanh")
            if item.code in resolved_items:
                existing_item, existing_quantity = resolved_items[item.code]
                resolved_items[item.code] = (
                    existing_item,
                    existing_quantity + line["quantity"],
                )
            else:
                resolved_items[item.code] = (item, line["quantity"])

        # TRƯỜNG HỢP 1: Bàn đang có đơn hoạt động -> TỰ ĐỘNG GỌI THÊM MÓN VÀO ĐƠN HIỆN TẠI
        if active_order is not None:
            for item, quantity in resolved_items.values():
                existing_order_item = next(
                    (i for i in active_order.items if i.item_code == item.code), 
                    None
                )
                if existing_order_item is not None:
                    existing_order_item.quantity += quantity
                else:
                    active_order.add_line(item.code, item.name, quantity, item.price)
                
                menu_item = self.menu.get_item(item.code)
                proc_time = menu_item.processing_time if menu_item else 5
                self.queue.enqueue(KitchenRequest(
                    order_id=active_order.order_id,
                    item_code=item.code,
                    item_name=item.name,
                    quantity=quantity,
                    processing_time=proc_time,
                    created_at=active_order.created_at,
                ))

            self.save()
            return active_order

        # TRƯỜNG HỢP 2: Bàn trống -> TẠO ĐƠN MỚI HOÀN TOÀN
        if self.table_service is not None and not self.table_service.is_available(table_id):
            raise ValueError("Bàn không tồn tại hoặc đang được phục vụ")

        if self.table_service is not None:
            self.table_service.reserve(table_id)

        order_id = "DH" + str(self.next_no).zfill(3)
        order = Order(order_id, table_id)
        self.orders[order_id] = order
        try:
            for item, quantity in resolved_items.values():
                order.add_line(item.code, item.name, quantity, item.price)
            self.save()

            for item, quantity in resolved_items.values():
                menu_item = self.menu.get_item(item.code)
                proc_time = menu_item.processing_time if menu_item else 5
                self.queue.enqueue(KitchenRequest(
                    order_id=order.order_id,
                    item_code=item.code,
                    item_name=item.name,
                    quantity=quantity,
                    processing_time=proc_time,
                    created_at=order.created_at,
                ))
            order.status = "IN_PROGRESS"
            self.save()
            self.next_no += 1
        except Exception:
            self.queue.remove_by_order(order.order_id)
            self.orders.pop(order.order_id, None)
            self.save()
            if self.table_service is not None:
                self.table_service.release(table_id)
            raise
        return order

    def send_to_kitchen(self, order_id: str) -> Order:
        order = self.get_order(order_id)

        if order.status != "NEW" or len(order.items) == 0:
            raise ValueError("Đơn phải có món và đang ở trạng thái NEW")

        if self.queue is None:
            raise ValueError("Chưa kết nối hàng đợi bếp")

        for item in order.items:
            menu_item = self.menu.get_item(item.item_code) if self.menu else None
            proc_time = menu_item.processing_time if menu_item else 5
            request = KitchenRequest(
                order_id=order.order_id,
                item_code=item.item_code,
                item_name=item.item_name,
                quantity=item.quantity,
                processing_time=proc_time,
                created_at=order.created_at,
            )
            self.queue.enqueue(request)

        order.status = "IN_PROGRESS"
        self.save()
        return order

    def mark_completed(self, order_id: str) -> Order:
        order = self.get_order(order_id)

        if order.status in {"PAID", "CANCELLED"}:
            raise ValueError("Đơn đã thanh toán hoặc đã hủy, không thể hoàn thành")

        previous_status = order.status
        order.status = "COMPLETED"
        try:
            self.save()
        except Exception:
            order.status = previous_status
            raise
        return order

    def edit_order(
        self,
        order_id: str,
        items: List[Dict[str, Any]],
        user: Any,
        note: Optional[str] = None,
        table_id: Optional[str] = None,
    ) -> Order:
        order = self.get_order(order_id)
        if not can_edit_order(user, order):
            raise ValueError("Bạn không có quyền sửa đơn hàng này")
        if order.status not in {"NEW", "IN_PROGRESS", "COMPLETED"}:
            raise ValueError("Không thể sửa đơn hàng ở trạng thái hiện tại")
        if not isinstance(items, list):
            raise ValueError("Danh sách món không hợp lệ")
        if note is not None and not isinstance(note, str):
            raise ValueError("Ghi chú phải là văn bản")

        existing = {item.item_code: item for item in order.items}
        updated_items: list[OrderItem] = []
        seen_codes: set[str] = set()
        for line in items:
            if not isinstance(line, dict):
                raise ValueError("Thông tin món ăn không hợp lệ")
            code = line.get("code", line.get("item_code", ""))
            quantity = line.get("quantity")
            if not isinstance(code, str) or not code.strip():
                raise ValueError("Mã món không được để trống")
            code = code.strip().upper()
            if code in seen_codes:
                raise ValueError("Mỗi món chỉ được xuất hiện một lần trong đơn")
            seen_codes.add(code)
            self._validate_quantity(quantity)

            previous = existing.get(code)
            if previous is not None:
                updated_items.append(OrderItem(
                    code,
                    previous.item_name,
                    quantity,
                    previous.unit_price,
                ))
                continue
            if self.menu is None:
                raise ValueError("Chưa kết nối thực đơn")
            menu_item = self.menu.get_item(code)
            if menu_item is None:
                raise ValueError(f"Không tìm thấy món ăn '{code}'")
            if not menu_item.is_active:
                raise ValueError("Món ăn đã ngừng kinh doanh")
            updated_items.append(OrderItem(
                menu_item.code,
                menu_item.name,
                quantity,
                menu_item.price,
            ))

        if order.status != "NEW" and not updated_items:
            raise ValueError("Đơn đã gửi bếp phải có ít nhất một món")
        if table_id is not None and not isinstance(table_id, str):
            raise ValueError("Bàn không hợp lệ")
        new_table_id = table_id if table_id is not None else order.table_id
        if new_table_id != order.table_id and self.table_service is None:
            raise ValueError("Chưa kết nối dịch vụ bàn")
        if (
            new_table_id != order.table_id
            and self.table_service is not None
            and not self.table_service.is_available(new_table_id)
        ):
            raise ValueError("Bàn mới không tồn tại hoặc đang được phục vụ")

        kitchen_snapshot = None
        desired_requests: list[KitchenRequest] = []
        new_item_codes = set()
        if order.status in {"IN_PROGRESS", "COMPLETED"}:
            if self.kitchen_service is None:
                raise ValueError("Chưa kết nối dịch vụ bếp để sửa đơn đã gửi")
            kitchen_snapshot = self.kitchen_service.snapshot_order_state()
            new_item_codes = set(seen_codes) - set(existing)
            desired_requests = []
            for item in updated_items:
                menu_item = self.menu.get_item(item.item_code) if self.menu else None
                proc_time = menu_item.processing_time if menu_item else 5
                desired_requests.append(
                    KitchenRequest(
                        order_id=order.order_id,
                        item_code=item.item_code,
                        item_name=item.item_name,
                        quantity=item.quantity,
                        processing_time=proc_time,
                        created_at=order.created_at,
                    )
                )

        old_items = order.items
        old_note = order.note
        old_table_id = order.table_id
        old_status = order.status
        table_snapshot = (
            self.table_service.list_tables()
            if self.table_service is not None and new_table_id != old_table_id
            else None
        )
        try:
            if kitchen_snapshot is not None:
                self.kitchen_service.replace_order_requests(
                    order.order_id,
                    desired_requests,
                )
            if table_snapshot is not None:
                self.table_service.move_reservation(old_table_id, new_table_id)
            order.items = updated_items
            order.note = order.note if note is None else note.strip()
            order.table_id = new_table_id
            if order.status == "COMPLETED" and new_item_codes:
                order.status = "IN_PROGRESS"
            self.save()
        except Exception as error:
            order.items = old_items
            order.note = old_note
            order.table_id = old_table_id
            order.status = old_status
            rollback_errors = []
            if table_snapshot is not None:
                try:
                    self.table_service.restore_statuses(table_snapshot)
                except Exception as rollback_error:
                    rollback_errors.append(rollback_error)
            if kitchen_snapshot is not None:
                try:
                    self.kitchen_service.restore_order_state(kitchen_snapshot)
                except Exception as rollback_error:
                    rollback_errors.append(rollback_error)
            if rollback_errors:
                details = "; ".join(str(failure) for failure in rollback_errors)
                raise OrderOperationRollbackError(
                    f"Sửa đơn thất bại và không thể khôi phục đầy đủ trạng thái: {details}"
                ) from error
            raise
        return order

    def cancel_order(
        self,
        order_id: str,
        reason: Optional[str] = None,
        user: Any = None,
    ) -> Order:
        order = self.get_order(order_id)
        if order.status == "PAID":
            raise ValueError("Không thể hủy đơn đã thanh toán")
        if order.status == "CANCELLED":
            raise ValueError("Đơn hàng đã được huỷ")
        if not can_cancel_order(user, order):
            raise ValueError("Bạn không có quyền huỷ đơn hàng này")
        if not isinstance(reason, str) or not reason.strip():
            raise ValueError("Vui lòng nhập lý do huỷ đơn")
        if order.status not in {"NEW", "IN_PROGRESS", "COMPLETED"}:
            raise ValueError("Không thể huỷ đơn ở trạng thái hiện tại")

        kitchen_snapshot = (
            self.kitchen_service.snapshot_order_state()
            if self.kitchen_service is not None
            else None
        )
        table_snapshot = (
            self.table_service.list_tables()
            if self.table_service is not None and order.table_id is not None
            else None
        )
        old_status = order.status
        old_cancelled_at = order.cancelled_at
        old_cancel_reason = order.cancel_reason
        try:
            if self.queue is not None:
                self.queue.remove_by_order(order_id)
            if table_snapshot is not None:
                self.table_service.release(order.table_id)
            order.status = "CANCELLED"
            order.cancelled_at = datetime.now().astimezone().isoformat()
            order.cancel_reason = reason.strip()
            self.save()
        except Exception as error:
            order.status = old_status
            order.cancelled_at = old_cancelled_at
            order.cancel_reason = old_cancel_reason
            rollback_errors = []
            if table_snapshot is not None:
                try:
                    self.table_service.restore_statuses(table_snapshot)
                except Exception as rollback_error:
                    rollback_errors.append(rollback_error)
            if kitchen_snapshot is not None:
                try:
                    self.kitchen_service.restore_order_state(kitchen_snapshot)
                except Exception as rollback_error:
                    rollback_errors.append(rollback_error)
            if rollback_errors:
                details = "; ".join(str(failure) for failure in rollback_errors)
                raise OrderOperationRollbackError(
                    f"Huỷ đơn thất bại và không thể khôi phục đầy đủ trạng thái: {details}"
                ) from error
            raise
        return order

    def used_codes(self) -> Set[str]:
        codes = set()
        for order in self.orders.values():
            for item in order.items:
                codes.add(item.item_code)
        return codes