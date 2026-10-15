# F&B Order Management

Ứng dụng dòng lệnh quản lý thực đơn, bàn ăn, đơn hàng, hàng đợi bếp và hóa đơn. Dự án phù hợp để thực hành OOP, cấu trúc dữ liệu và kiểm thử Python.

## Cấu trúc thư mục

```text
fnb-order-management/
├── data/
│   └── menu_sample.json
├── src/
│   ├── __init__.py
│   ├── app.py
│   ├── models/
│   │   ├── __init__.py
│   │   ├── dining_table.py
│   │   ├── invoice.py
│   │   ├── menu_item.py
│   │   └── order.py
│   └── core/
│       ├── __init__.py
│       ├── storage.py
│       ├── data_structures/
│       │   ├── __init__.py
│       │   ├── hash_map.py
│       │   └── queue.py
│       └── services/
│           ├── __init__.py
│           ├── billing_service.py
│           ├── kitchen_service.py
│           ├── menu_service.py
│           └── order_service.py
├── tests/
├── .gitignore
├── pyproject.toml
├── requirements.txt
└── README.md
```

## Phân công gợi ý

- Thành viên 1: model thực đơn, bàn ăn và dữ liệu mẫu.
- Thành viên 2: cấu trúc dữ liệu Queue và Hash Map.
- Thành viên 3: nghiệp vụ thực đơn, đơn hàng và bếp.
- Thành viên 4: hóa đơn, kiểm thử tích hợp và demo.

## Cài đặt và chạy

Cần cài Python 3.10 trở lên và [uv](https://docs.astral.sh/uv/).

```powershell
uv sync
uv run python -m src.app
```

Chạy kiểm thử:

```powershell
uv run pytest
```

Có thể cài dependency kiểm thử bằng `python -m pip install -r requirements.txt` nếu không dùng uv.

## Chức năng dự kiến

- Quản lý thực đơn và tra cứu món theo mã.
- Tạo đơn hàng, thêm món và gắn với bàn.
- Đưa món vào hàng đợi bếp theo FIFO.
- Theo dõi trạng thái bàn và tính tổng hóa đơn.

Đây là bộ khung khởi đầu; các thành viên có thể hoàn thiện nghiệp vụ và kiểm thử theo phân công.
