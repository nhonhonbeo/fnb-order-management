class HashNode:
  """Lớp đại diện cho một nút chứa cặp (Key, Value) trong Danh sách liên kết"""

  def __init__(self, key, value):
    self.key = key  # Khóa (ví dụ: "MSSV01", "username")
    self.value = value  # Giá trị (ví dụ: "Nguyễn Văn A", "thong_tin_user")
    self.next = None  # Con trỏ trỏ đến nút tiếp theo nếu bị đụng độ (collision)


class HashTable:
  """Lớp cài đặt Bảng băm (Hash Table) dùng phương pháp Separate Chaining"""

  def __init__(self, capacity=10):
    self.capacity = capacity  # Sức chứa của mảng (số lượng buckets)
    self.size = 0  # Số lượng cặp (key, value) thực tế đang lưu
    # Tạo mảng chứa các Bucket, ban đầu tất cả là None
    self.buckets = [None] * self.capacity

  def _hash_function(self, key):
    """Hàm băm tự viết dựa trên mã ASCII của chuỗi (Polynomial Rolling Hash)

    Giúp chuyển mọi loại Key (String/Int) thành một chỉ số Index hợp lệ trong mảng.
    """
    hash_value = 0
    key_str = str(key)  # Ép kiểu Key về dạng chuỗi để xử lý

    # Duyệt qua từng ký tự và tính giá trị băm theo mã ASCII
    for char in key_str:
      # Nhân với 31 (một số nguyên tố thường dùng trong hàm băm)
      hash_value = (hash_value * 31 + ord(char)) % self.capacity

    return hash_value

  def insert(self, key, value):
    """Thêm mới hoặc cập nhật giá trị của một Key vào Hash Table"""
    index = self._hash_function(key)  # Tính vị trí bucket
    head = self.buckets[index]  # Lấy Node đầu tiên tại bucket đó

    # 1. Kiểm tra xem Key này đã tồn tại trong bucket chưa (Nếu có thì CẬP NHẬT)
    current = head
    while current is not None:
      if current.key == key:
        current.value = value  # Cập nhật giá trị mới
        return
      current = current.next

    # 2. Nếu Key chưa tồn tại, tạo Node mới và THÊM VÀO ĐẦU Danh sách liên kết
    new_node = HashNode(key, value)
    new_node.next = head
    self.buckets[index] = new_node  # Cập nhật Node đầu mới của bucket
    self.size += 1

  def get(self, key):
    """Tìm kiếm và trả về giá trị (Value) tương ứng với Key.

    Trả về None nếu không tìm thấy.
    """
    index = self._hash_function(key)
    current = self.buckets[index]

    # Duyệt qua danh sách liên kết tại bucket đó để tìm Key
    while current is not None:
      if current.key == key:
        return current.value
      current = current.next

    return None  # Không tìm thấy Key

  def remove(self, key):
    """Xóa cặp (Key, Value) ra khỏi Hash Table.

    Trả về True nếu xóa thành công, False nếu không tìm thấy.
    """
    index = self._hash_function(key)
    current = self.buckets[index]
    prev = None  # Con trỏ giữ vị trí nút phía trước

    # Duyệt danh sách liên kết để tìm nút cần xóa
    while current is not None:
      if current.key == key:
        if prev is None:
          # Nút cần xóa nằm ngay đầu Bucket
          self.buckets[index] = current.next
        else:
          # Nút cần xóa nằm ở giữa hoặc cuối danh sách liên kết
          prev.next = current.next

        self.size -= 1
        return True  # Xóa thành công

      prev = current
      current = current.next

    return False  # Không tìm thấy để xóa

  def display(self):
    """In ra cấu trúc Hash Table để kiểm tra và báo cáo PBL1"""
    print(f"\n================ HASH TABLE (Size: {self.size}) ================")
    for i in range(self.capacity):
      print(f"Bucket {i}: ", end="")
      current = self.buckets[i]
      if current is None:
        print("Empty")
      else:
        chain = []
        while current:
          chain.append(f"[{current.key}: {current.value}]")
          current = current.next
        print(" -> ".join(chain))
    print("==============================================================")


# ==========================================
# CHẠY THỬ CHƯƠNG TRÌNH (TEST CODE)
# ==========================================
if __name__ == "__main__":
  # Khởi tạo bảng băm với 5 bucket (cố tình để nhỏ để dễ quan sát đụng độ)
  ht = HashTable(capacity=5)

  print("1. Thêm các sinh viên vào Hash Table:")
  ht.insert("SV01", "Nguyễn Văn An")
  ht.insert("SV02", "Trần Thị Bích")
  ht.insert("SV03", "Lê Hoàng Cường")
  ht.insert("SV04", "Phạm Đăng Khoa")
  ht.display()

  print("\n2. Cập nhật tên của SV01:")
  ht.insert("SV01", "Nguyễn Văn An (Đã đổi tên)")
  print("Tên mới của SV01:", ht.get("SV01"))

  print("\n3. Tìm kiếm sinh viên:")
  print("Tìm SV03:", ht.get("SV03"))
  print("Tìm SV99 (không tồn tại):", ht.get("SV99"))

  print("\n4. Xóa SV02 ra khỏi Hash Table:")
  ht.remove("SV02")
  ht.display()