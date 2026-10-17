class Node:
  """Lớp đại diện cho mỗi phần tử (Node) trong hàng đợi"""

  def __init__(self, data):
    self.data = data  # Dữ liệu của node
    self.next = None  # Con trỏ trỏ đến node tiếp theo


class Queue:
  """Lớp cài đặt cấu trúc dữ liệu Queue (FIFO) dùng Linked List"""

  def __init__(self):
    self.front = None  # Node ở đầu hàng đợi (dùng để lấy ra - Dequeue)
    self.rear = None  # Node ở cuối hàng đợi (dùng để thêm vào - Enqueue)
    self._size = 0  # Biến đếm số lượng phần tử

  def is_empty(self):
    """Kiểm tra hàng đợi có trống không"""
    return self.front is None

  def enqueue(self, data):
    """Thêm một phần tử vào cuối hàng đợi (O(1))"""
    new_node = Node(data)
    if self.rear is None:  # Nếu hàng đợi đang trống
      self.front = self.rear = new_node
    else:
      self.rear.next = new_node  # Nối node mới vào sau rear hiện tại
      self.rear = new_node  # Cập nhật rear thành node mới
    self._size += 1

  def dequeue(self):
    """Lấy và xóa phần tử ở đầu hàng đợi (O(1))"""
    if self.is_empty():
      raise IndexError("Hàng đợi đang trống! Không thể lấy phần tử.")

    temp = self.front  # Lưu lại node đầu
    self.front = temp.next  # Dời front sang node tiếp theo

    if self.front is None:  # Nếu sau khi lấy mà hàng đợi hết sạch
      self.rear = None  # Cập nhật lại rear về None

    self._size -= 1
    return temp.data

  def peek(self):
    """Xem giá trị của phần tử ở đầu hàng đợi mà không xóa"""
    if self.is_empty():
      raise IndexError("Hàng đợi đang trống!")
    return self.front.data

  def size(self):
    """Trả về số lượng phần tử hiện có trong hàng đợi"""
    return self._size

  def __iter__(self):
    current = self.front
    while current is not None:
      yield current.data
      current = current.next

  def display(self):
    """In ra các phần tử trong hàng đợi từ đầu đến cuối (hữu ích để debug)"""
    if self.is_empty():
      print("Hàng đợi trống!")
      return

    current = self.front
    elements = []
    while current:
      elements.append(str(current.data))
      current = current.next
    print(" -> ".join(elements))


# ==========================================
# TEST THỬ CHƯƠNG TRÌNH
# ==========================================
if __name__ == "__main__":
  q = Queue()

  print("1. Thêm phần tử vào hàng đợi: A, B, C")
  q.enqueue("A")
  q.enqueue("B")
  q.enqueue("C")
  q.display()  # Output: A -> B -> C

  print("\n2. Xem phần tử ở đầu hàng đợi (Peek):", q.peek())  # Output: A

  print("\n3. Lấy phần tử ra khỏi hàng đợi (Dequeue):", q.dequeue())  # Output: A
  print("Hàng đợi sau khi Dequeue:")
  q.display()  # Output: B -> C

  print("\n4. Kích thước hiện tại của hàng đợi:", q.size())  # Output: 2