"""Quy tắc chuyển giá trị tiền sang đồng Việt Nam nguyên."""
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any


def to_vnd(value: Any) -> int:
    """Chuẩn hóa đầu vào tiền tệ thành số nguyên đồng, làm tròn half-up."""
    if isinstance(value, bool):
        raise ValueError("Giá trị tiền tệ không hợp lệ")

    try:
        amount = Decimal(str(value))
        if not amount.is_finite():
            raise ValueError("Giá trị tiền tệ không hữu hạn")
        return int(amount.quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    except (InvalidOperation, TypeError, ValueError) as error:
        raise ValueError("Giá trị tiền tệ không hợp lệ") from error


def to_whole_vnd(value: Any) -> int:
    """Chuẩn hóa tiền đầu vào và từ chối giá trị có phần lẻ của đồng."""
    normalized = to_vnd(value)
    amount = Decimal(str(value))
    if amount != normalized:
        raise ValueError("Số tiền phải là số nguyên đồng")
    return normalized