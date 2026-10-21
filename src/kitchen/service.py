"""Nghiệp vụ điều phối hàng đợi bếp theo nguyên tắc FIFO."""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from src.kitchen.queue import KitchenRequest, OrderQueue
from src.kitchen.repository import KitchenRepository


class KitchenOperationRollbackError(RuntimeError):
    """Raised when a failed kitchen operation cannot be fully rolled back."""


class KitchenService:
    """Điều phối và lưu tiến độ chế biến từng món."""

    def __init__(
        self,
        kitchen_queue: Optional[Any] = None,
        storage_or_path: Optional[Any] = None,
        order_service: Optional[Any] = None,
    ):
        self.kitchen_queue = kitchen_queue if kitchen_queue is not None else OrderQueue()
        self.repository = (
            storage_or_path
            if isinstance(storage_or_path, KitchenRepository)
            else KitchenRepository(storage_or_path)
        )

        self.order_service = order_service
        self._requests: Dict[Tuple[str, str], KitchenRequest] = {}
        self._loading = False

        if self.repository.exists():
            self.load()
        else:
            for request in self.list_requests():
                self._requests[self._request_key(request)] = request

        if hasattr(self.kitchen_queue, "set_change_listener"):
            self.kitchen_queue.set_change_listener(self._on_queue_change)
        if self._requests and not self.repository.exists():
            self.save()

    @staticmethod
    def _request_key(request: KitchenRequest) -> Tuple[str, str]:
        return request.order_id, request.item_code

    def _on_queue_change(self, action: str, value: Any) -> None:
        if self._loading:
            return
        if action in {"enqueue", "dequeue"}:
            self._requests[self._request_key(value)] = value
        elif action == "remove_by_order":
            self._requests = {
                key: request
                for key, request in self._requests.items()
                if request.order_id != value
            }
        self.save()

    def set_order_service(self, order_service: Any) -> None:
        self.order_service = order_service

    def save(self) -> None:
        """Lưu trạng thái món và thứ tự hàng đợi."""
        self.repository.save_state(
            list(self._requests.values()),
            self.list_requests(),
        )

    def load(self) -> None:
        """Nạp trạng thái món và thứ tự hàng đợi từ JSON."""
        requests, queue_keys = self.repository.load_state()

        self._loading = True
        try:
            while not self.kitchen_queue.is_empty():
                self.kitchen_queue.dequeue()

            self._requests = {}
            for request in requests:
                self._requests[self._request_key(request)] = request

            for key in queue_keys:
                request = self._requests.get(key)
                if request is not None:
                    self.kitchen_queue.enqueue(request)
        finally:
            self._loading = False

    def send_to_kitchen(self, request_or_item: Any) -> None:
        """Đưa món ăn vào hàng đợi chờ bếp nấu."""
        if not hasattr(self.kitchen_queue, "enqueue"):
            raise ValueError("Hàng đợi bếp không hỗ trợ thêm yêu cầu")
        request_key = self._request_key(request_or_item)
        if request_key in self._requests:
            raise ValueError(
                f"Món '{request_or_item.item_code}' của đơn "
                f"'{request_or_item.order_id}' đã có trong hàng đợi"
            )
        self.kitchen_queue.enqueue(request_or_item)
        if not hasattr(self.kitchen_queue, "set_change_listener"):
            self._requests[request_key] = request_or_item
            self.save()

    def current(self) -> Optional[KitchenRequest]:
        """Trả về món ở đầu hàng đợi, hoặc None nếu hàng đợi trống."""
        if self.is_empty():
            return None
        return self.kitchen_queue.peek()

    def start(self, order_id: str, item_code: str) -> KitchenRequest:
        request = self.current()
        if request is None or (request.order_id, request.item_code) != (order_id, item_code):
            raise ValueError("Chỉ được bắt đầu món ở đầu hàng đợi bếp")
        if request.status != "NEW":
            raise ValueError("Món không ở trạng thái chờ nấu")

        previous_status = request.status
        request.status = "COOKING"
        self._requests[self._request_key(request)] = request
        try:
            self.save()
        except Exception:
            request.status = previous_status
            raise
        return request

    def complete(self, order_id: str, item_code: str) -> KitchenRequest:
        request = self.current()
        if request is None or (request.order_id, request.item_code) != (order_id, item_code):
            raise ValueError("Chỉ được hoàn thành món ở đầu hàng đợi bếp")
        if request.status != "COOKING":
            raise ValueError("Món chưa được bắt đầu chế biến")

        order = (
            self.order_service.get_order(order_id)
            if self.order_service is not None
            else None
        )
        queue_before = self.list_requests()
        request_status_before = request.status
        order_status_before = order.status if order is not None else None
        was_loading = self._loading
        self._loading = True
        try:
            request.status = "READY"
            self._requests[self._request_key(request)] = request
            self.kitchen_queue.dequeue()

            all_ready = (
                order is not None
                and bool(order.items)
                and all(
                    (self._requests.get((order_id, item.item_code)) is not None)
                    and self._requests[(order_id, item.item_code)].status == "READY"
                    for item in order.items
                )
            )
            if all_ready:
                self.order_service.mark_completed(order_id)
            self.save()
        except Exception as error:
            rollback_errors = []
            request.status = request_status_before
            self._requests[self._request_key(request)] = request
            try:
                self._restore_queue(queue_before)
            except Exception as rollback_error:
                rollback_errors.append(rollback_error)
            if order is not None and order.status != order_status_before:
                try:
                    order.status = order_status_before
                    self.order_service.save()
                except Exception as rollback_error:
                    rollback_errors.append(rollback_error)
            try:
                self.save()
            except Exception as rollback_error:
                rollback_errors.append(rollback_error)
            if rollback_errors:
                details = "; ".join(str(failure) for failure in rollback_errors)
                raise KitchenOperationRollbackError(
                    "Hoàn thành món thất bại và không thể khôi phục đầy đủ trạng thái: "
                    f"{details}"
                ) from error
            raise
        finally:
            self._loading = was_loading
        return request

    def _restore_queue(self, requests: List[KitchenRequest]) -> None:
        while not self.kitchen_queue.is_empty():
            self.kitchen_queue.dequeue()
        for request in requests:
            self.kitchen_queue.enqueue(request)

    def next_item(self) -> Any:
        """Lấy món tiếp theo theo thứ tự FIFO."""
        if hasattr(self.kitchen_queue, "dequeue"):
            return self.kitchen_queue.dequeue()
        return None

    def peek_next(self) -> Any:
        """Xem trước món tiếp theo mà không xóa khỏi hàng đợi."""
        if hasattr(self.kitchen_queue, "peek"):
            return self.kitchen_queue.peek()
        return None

    def list_requests(self) -> List[Any]:
        """Trả về toàn bộ danh sách món đang chờ trong hàng đợi."""
        if hasattr(self.kitchen_queue, "list_requests"):
            return self.kitchen_queue.list_requests()
        return []

    def remove_by_order(self, order_id: str) -> None:
        """Gỡ toàn bộ món của đơn hàng bị hủy ra khỏi hàng đợi."""
        if not hasattr(self.kitchen_queue, "remove_by_order"):
            return
        self.kitchen_queue.remove_by_order(order_id)
        if not hasattr(self.kitchen_queue, "set_change_listener"):
            self._requests = {
                key: request
                for key, request in self._requests.items()
                if request.order_id != order_id
            }
            self.save()

    def mark_order_done(self, order_id: str) -> None:
        """Mark all saved kitchen requests for a paid order as done."""
        changed = False
        for request in self._requests.values():
            if request.order_id == order_id and request.status != "DONE":
                request.status = "DONE"
                changed = True
        if changed:
            self.save()

    def snapshot_order_statuses(self, order_id: str) -> dict[str, str]:
        return {
            request.item_code: request.status
            for request in self._requests.values()
            if request.order_id == order_id
        }

    def restore_order_statuses(
        self,
        order_id: str,
        statuses: dict[str, str],
    ) -> None:
        for request in self._requests.values():
            if request.order_id == order_id and request.item_code in statuses:
                request.status = statuses[request.item_code]
        self.save()

    def snapshot_order_state(self) -> tuple[dict[Tuple[str, str], KitchenRequest], List[KitchenRequest]]:
        return dict(self._requests), self.list_requests()

    def restore_order_state(
        self,
        snapshot: tuple[dict[Tuple[str, str], KitchenRequest], List[KitchenRequest]],
    ) -> None:
        requests, queued = snapshot
        self._loading = True
        try:
            self._requests = dict(requests)
            self.kitchen_queue.replace_all(list(queued))
        finally:
            self._loading = False
        self.save()

    def replace_order_requests(
        self,
        order_id: str,
        desired_requests: List[KitchenRequest],
    ) -> None:
        desired = {request.item_code: request for request in desired_requests}
        if len(desired) != len(desired_requests):
            raise ValueError("Đơn hàng không được có món trùng")
        if any(request.order_id != order_id for request in desired_requests):
            raise ValueError("Yêu cầu bếp không khớp với đơn hàng")

        existing = {
            request.item_code: request
            for request in self._requests.values()
            if request.order_id == order_id
        }
        for item_code, request in existing.items():
            replacement = desired.get(item_code)
            if request.status != "NEW" and (
                replacement is None or replacement.quantity != request.quantity
            ):
                raise ValueError(
                    f"Món '{request.item_name}' đã bắt đầu chế biến, "
                    "không thể xóa hoặc đổi số lượng"
                )

        next_requests = {
            key: request
            for key, request in self._requests.items()
            if request.order_id != order_id
        }
        replacements: dict[str, KitchenRequest] = {}
        for item_code, requested in desired.items():
            previous = existing.get(item_code)
            if previous is None:
                replacement = KitchenRequest(
                    order_id=order_id,
                    item_code=item_code,
                    item_name=requested.item_name,
                    quantity=requested.quantity,
                )
            elif previous.status == "NEW":
                replacement = KitchenRequest(
                    order_id=order_id,
                    item_code=item_code,
                    item_name=requested.item_name,
                    quantity=requested.quantity,
                )
            else:
                replacement = KitchenRequest(
                    order_id=order_id,
                    item_code=item_code,
                    item_name=previous.item_name,
                    quantity=previous.quantity,
                    status=previous.status,
                )
            replacements[item_code] = replacement
            next_requests[(order_id, item_code)] = replacement

        current_queue = self.list_requests()
        next_queue: list[KitchenRequest] = []
        queued_codes: set[str] = set()
        for request in current_queue:
            if request.order_id != order_id:
                next_queue.append(request)
                continue
            replacement = replacements.get(request.item_code)
            if replacement is not None:
                next_queue.append(replacement)
                queued_codes.add(request.item_code)
        for item_code, replacement in replacements.items():
            if item_code not in queued_codes and item_code not in existing:
                next_queue.append(replacement)

        old_requests = self._requests
        old_queue = current_queue
        was_loading = self._loading
        self._loading = True
        try:
            self._requests = next_requests
            self.kitchen_queue.replace_all(next_queue)
            self.save()
        except Exception as error:
            self._requests = old_requests
            try:
                self.kitchen_queue.replace_all(old_queue)
                self.save()
            except Exception as rollback_error:
                raise KitchenOperationRollbackError(
                    "Không thể cập nhật yêu cầu bếp và hoàn tác đầy đủ: "
                    f"{rollback_error}"
                ) from error
            raise
        finally:
            self._loading = was_loading

    def update_status(self, order_id: str, item_code: str, status: str) -> None:
        """Cập nhật tiến độ chế biến của một yêu cầu trong hàng đợi."""
        if status not in {"NEW", "COOKING", "READY", "DONE"}:
            raise ValueError(f"Trạng thái món không hợp lệ: {status}")
        if status == "COOKING":
            self.start(order_id, item_code)
            return
        if status == "READY":
            self.complete(order_id, item_code)
            return

        for request in self.list_requests():
            if request.order_id == order_id and request.item_code == item_code:
                if self.current() != request:
                    raise ValueError("Chỉ được cập nhật món ở đầu hàng đợi bếp")
                request.status = status
                self._requests[self._request_key(request)] = request
                self.save()
                return
        raise ValueError("Không tìm thấy món trong hàng đợi bếp")

    def is_empty(self) -> bool:
        """Kiểm tra hàng đợi có trống không."""
        if hasattr(self.kitchen_queue, "is_empty"):
            return self.kitchen_queue.is_empty()
        return True

    def size(self) -> int:
        """Trả về số món đang chờ chế biến."""
        if hasattr(self.kitchen_queue, "size"):
            return self.kitchen_queue.size()
        return 0