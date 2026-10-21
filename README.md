# F&B Order Management

Ứng dụng Streamlit quản lý thực đơn, bàn ăn, đơn hàng, hàng đợi bếp, hóa đơn và thanh toán. Dự án phù hợp để thực hành OOP, cấu trúc dữ liệu và kiểm thử Python.

## Cấu trúc thư mục

```text
fnb-order-management/
├── data/
│   ├── menu_seed.json
│   └── menu.json (được tạo khi chạy, không commit)
├── src/
│   ├── __init__.py
│   ├── app.py
│   ├── menu/          # model, repository, service, page, editor
│   ├── orders/        # model, repository, service, page
│   ├── kitchen/       # queue, repository, service, page, panel
│   ├── tables/        # model, repository, service, dashboard page
│   ├── payments/      # payment/invoice models, repositories, services, UI
│   ├── users/         # model, repository, authentication service and UI
│   ├── reports/       # cross-domain reporting calculations
│   ├── shared/        # reusable data structures, money and repository base
│   ├── storage/       # shared JSON storage
│   └── ui/            # Streamlit bootstrap and shared UI helpers
├── tests/
├── .gitignore
├── pyproject.toml
├── requirements.txt
└── README.md
```

## Phân công gợi ý

- Có thể chia thành viên theo package nghiệp vụ: `menu`, `orders`, `kitchen`,
  `tables`, `payments` hoặc `users`.
- `shared`, `storage`, `reports` và `ui/bootstrap.py` là thành phần dùng chung;
  nên thống nhất thay đổi qua pull request khi nhiều module cùng phụ thuộc.

## Cài đặt và chạy

Ở lần chạy đầu, thực đơn chạy được khởi tạo từ `data/menu_seed.json` vào `data/menu.json`.

Cần cài Python 3.10 trở lên và [uv](https://docs.astral.sh/uv/).

```powershell
uv sync
uv run streamlit run src/app.py
```

Chạy kiểm thử:

```powershell
uv run pytest
```

Có thể cài dependency kiểm thử bằng `python -m pip install -r requirements.txt` nếu không dùng uv.

## Chức năng dự kiến

- Quản lý thực đơn và tra cứu món theo mã.
- Quản lý có thể thêm bàn và xoá bàn trống không có đơn chưa thanh toán.
- Tạo đơn hàng, sửa món/ghi chú/bàn và huỷ đơn có lý do theo phân quyền.
- Đưa món vào hàng đợi bếp theo FIFO.
- Theo dõi trạng thái bàn và tính tổng hóa đơn.
- Đơn đã huỷ không thể thanh toán và không được tính vào thống kê bán hàng.

`src/app.py` là entry point Streamlit duy nhất. Dữ liệu JSON tiếp tục nằm trong
thư mục `data/`; cấu trúc thư mục mã nguồn không làm thay đổi vị trí hay định dạng
các tệp dữ liệu hiện có.

Danh sách bàn mặc định được khởi tạo khi `data/tables.json` chưa tồn tại. Nếu
toàn bộ bàn bị xoá, tệp vẫn được giữ với danh sách rỗng nên các bàn mặc định
không tự xuất hiện lại.
