from collections.abc import Iterator, Mapping
from typing import Any


class KeyValuePair:
  """Lớp đại diện cho một cặp (Key, Value)"""

  def __init__(self, key, value):
    self.key = key
    self.value = value


class HashMap(Mapping[Any, Any]):
  """Cài đặt HashMap sử dụng Địa chỉ mở (Open Addressing - Linear Probing)

  Tích hợp cơ chế tự động mở rộng mảng (Rehashing) khi đụng độ tăng cao.
  """

  # Nút đánh dấu ô đã bị xóa (Tombstone) để không làm đứt chuỗi dò tìm
  DELETED = KeyValuePair(None, None)

  def __init__(self, initial_capacity=8):
    self.capacity = initial_capacity  # Sức chứa ban đầu của mảng
    self.size = 0  # Số lượng phần tử thực tế đang lưu
    self.buckets = [None] * self.capacity
    self.load_factor_threshold = 0.7  # Ngưỡng co giãn mảng (70%)

  def _hash(self, key):
    """Hàm băm chuyển Key thành chỉ số Index trong mảng"""
    hash_val = 0
    key_str = str(key)
    for char in key_str:
      hash_val = (hash_val * 31 + ord(char)) % self.capacity
    return hash_val

  def _resize(self, new_capacity):
    """Tự động tăng kích thước mảng và băm lại (Rehash) toàn bộ dữ liệu cũ"""
    old_buckets = self.buckets
    self.capacity = new_capacity
    self.buckets = [None] * self.capacity
    self.size = 0  # Reset size để hàm put tính lại từ đầu

    # Băm lại tất cả các phần tử hợp lệ sang mảng mới
    for item in old_buckets:
      if item is not None and item is not HashMap.DELETED:
        self.put(item.key, item.value)

  def put(self, key, value):
    """Thêm mới hoặc cập nhật cặp (Key, Value)"""
    # 1. Kiểm tra hệ số nạp (Load Factor), nếu > 70% thì mở rộng mảng gấp đôi
    if self.size / self.capacity >= self.load_factor_threshold:
      self._resize(self.capacity * 2)

    index = self._hash(key)
    first_deleted_index = -1  # Lưu lại vị trí ô DELETED đầu tiên để tái sử dụng

    # 2. Dò tuyến tính (Linear Probing) tìm ô trống hoặc trùng Key
    for _ in range(self.capacity):
      item = self.buckets[index]

      if item is None:
        # Gặp ô trống -> Tái sử dụng ô DELETED nếu có, nếu không chèn vào ô trống
        target_index = (
            first_deleted_index if first_deleted_index != -1 else index
        )
        self.buckets[target_index] = KeyValuePair(key, value)
        self.size += 1
        return

      if item is HashMap.DELETED:
        if first_deleted_index == -1:
          first_deleted_index = index
      elif item.key == key:
        # Key đã tồn tại -> Cập nhật giá trị
        item.value = value
        return

      # Nhích sang ô tiếp theo (dạng vòng tròn nhờ phép %)
      index = (index + 1) % self.capacity

  def get(self, key, default=None):
    """Tìm giá trị theo Key, trả về default nếu không tìm thấy."""
    index = self._hash(key)

    for _ in range(self.capacity):
      item = self.buckets[index]

      if item is None:
        return default  # Gặp ô None nghĩa là Key chắc chắn không tồn tại

      if item is not HashMap.DELETED and item.key == key:
        return item.value

      index = (index + 1) % self.capacity

    return default

  def __getitem__(self, key):
    """Truy cập giá trị theo cú pháp mapping."""
    missing = object()
    value = self.get(key, missing)
    if value is missing:
      raise KeyError(key)
    return value

  def __iter__(self) -> Iterator[Any]:
    for item in self.buckets:
      if item is not None and item is not HashMap.DELETED:
        yield item.key

  def __len__(self) -> int:
    return self.size

  def __eq__(self, other: object) -> bool:
    if not isinstance(other, Mapping) or len(self) != len(other):
      return False
    return all(key in other and value == other[key] for key, value in self.items())

  def remove(self, key):
    """Xóa Key khỏi HashMap. Trả về True nếu xóa thành công."""
    index = self._hash(key)

    for _ in range(self.capacity):
      item = self.buckets[index]

      if item is None:
        return False  # Không tìm thấy

      if item is not HashMap.DELETED and item.key == key:
        # Đánh dấu ô bằng DELETED (Tombstone) chứ KHÔNG gán về None
        self.buckets[index] = HashMap.DELETED
        self.size -= 1
        return True

      index = (index + 1) % self.capacity

    return False

  def display(self):
    """In cấu trúc thực tế của mảng HashMap"""
    print(f"\n--- HASHMAP (Size: {self.size}/{self.capacity}) ---")
    for i, item in enumerate(self.buckets):
      if item is None:
        print(f"Index {i}: [ EMPTY ]")
      elif item is HashMap.DELETED:
        print(f"Index {i}: [ DELETED (Tombstone) ]")
      else:
        print(f"Index {i}: [{item.key} : {item.value}]")


# ==========================================
# CHẠY THỬ CHƯƠNG TRÌNH
# ==========================================
if __name__ == "__main__":
  # Khởi tạo HashMap với kích thước ban đầu chỉ là 4 để dễ quan sát việc tự mở rộng
  hmap = HashMap(initial_capacity=4)

  print("1. Thêm 3 phần tử ban đầu:")
  hmap.put("ID_01", "Nguyễn Văn A")
  hmap.put("ID_02", "Trần Thị B")
  hmap.put("ID_03", "Lê Văn C")
  hmap.display()

  print("\n2. Thêm phần tử thứ 4 (Kích hoạt Tự động nhân đôi mảng lên 8):")
  hmap.put("ID_04", "Phạm Văn D")
  hmap.display()

  print("\n3. Lấy dữ liệu ID_02:", hmap.get("ID_02"))

  print("\n4. Xóa ID_02:")
  hmap.remove("ID_02")
  hmap.display()

  print("\n5. Thêm phần tử mới ID_05 (Sẽ lấp vào vị trí DELETED vừa xóa):")
  hmap.put("ID_05", "Hoàng Văn E")
  hmap.display()