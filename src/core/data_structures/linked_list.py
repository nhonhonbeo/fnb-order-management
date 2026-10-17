class Node:
  """Lớp đại diện cho một nút (Node) trong Danh sách liên kết"""

  def __init__(self, data):
    self.data = data  # Chứa giá trị của nút
    self.next = None  # Con trỏ trỏ đến nút kế tiếp (mặc định ban đầu là None)


class LinkedList:
  """Lớp quản lý Danh sách liên kết đơn"""

  def __init__(self):
    self.head = None  # Giữ vị trí nút đầu tiên của danh sách
    self._size = 0  # Đếm số phần tử hiện có

  def is_empty(self):
    """Kiểm tra danh sách có trống hay không"""
    return self.head is None

  def append(self, data):
    """Thêm một nút mới vào CUỐI danh sách - Độ phức tạp O(n)"""
    new_node = Node(data)
    if self.is_empty():
      self.head = new_node
    else:
      current = self.head
      # Duyệt tới nút cuối cùng (nút có next = None)
      while current.next:
        current = current.next
      current.next = new_node
    self._size += 1

  def prepend(self, data):
    """Thêm một nút mới vào ĐẦU danh sách - Độ phức tạp O(1)"""
    new_node = Node(data)
    new_node.next = self.head
    self.head = new_node
    self._size += 1

  def delete(self, data):
    """Xóa nút đầu tiên tìm thấy có giá trị bằng data - Độ phức tạp O(n)"""
    if self.is_empty():
      print("Danh sách đang trống!")
      return False

    # TH1: Nút cần xóa ngay tại đầu (head)
    if self.head.data == data:
      self.head = self.head.next
      self._size -= 1
      return True

    # TH2: Nút cần xóa nằm ở giữa hoặc cuối
    current = self.head
    prev = None
    while current and current.data != data:
      prev = current
      current = current.next

    # Nếu duyệt đến cuối mà không tìm thấy giá trị
    if current is None:
      print(f"Không tìm thấy '{data}' trong danh sách.")
      return False

    # Bỏ qua nút current bằng cách nối prev.next trực tiếp tới current.next
    prev.next = current.next
    self._size -= 1
    return True

  def search(self, data):
    """Tìm kiếm vị trí (index) của giá trị trong danh sách - Độ phức tạp O(n)"""
    current = self.head
    index = 0
    while current:
      if current.data == data:
        return index  # Trả về chỉ số vị trí tìm thấy
      current = current.next
      index += 1
    return -1  # Trả về -1 nếu không tìm thấy

  def display(self):
    """In ra toàn bộ danh sách dưới dạng chuỗi nối nhau"""
    if self.is_empty():
      print("Danh sách trống!")
      return

    current = self.head
    elements = []
    while current:
      elements.append(str(current.data))
      current = current.next
    print(" -> ".join(elements) + " -> None")

  def size(self):
    """Trả về số lượng phần tử"""
    return self._size


# ==========================================
# TEST CHƯƠNG TRÌNH (DEMO CÁC THAO TÁC)
# ==========================================
if __name__ == "__main__":
  ll = LinkedList()

  print("1. Thêm các phần tử vào cuối (append): 10, 20, 30")
  ll.append(10)
  ll.append(20)
  ll.append(30)
  ll.display()  # Kết quả: 10 -> 20 -> 30 -> None

  print("\n2. Thêm vào đầu (prepend): 5")
  ll.prepend(5)
  ll.display()  # Kết quả: 5 -> 10 -> 20 -> 30 -> None

  print("\n3. Tìm kiếm vị trí của phần tử 20:")
  index = ll.search(20)
  print(f"Giá trị 20 ở vị trí index: {index}")  # Kết quả: 2

  print("\n4. Xóa phần tử 10:")
  ll.delete(10)
  ll.display()  # Kết quả: 5 -> 20 -> 30 -> None

  print("\n5. Kích thước hiện tại:", ll.size())  # Kết quả: 3