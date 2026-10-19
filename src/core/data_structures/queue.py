from src.core.data_structures.linked_list import LinkedList, Node


class Queue:
  """Lớp cài đặt cấu trúc dữ liệu Queue (FIFO) dùng Linked List"""

  def __init__(self):
    self._items = LinkedList()

  @property
  def front(self):
    return self._items.head

  @property
  def rear(self):
    return self._items.tail

  def is_empty(self):
    """Kiểm tra hàng đợi có trống không"""
    return self._items.is_empty()

  def enqueue(self, data):
    """Thêm một phần tử vào cuối hàng đợi (O(1))"""
    self._items.append(data)

  def dequeue(self):
    """Lấy và xóa phần tử ở đầu hàng đợi (O(1))"""
    if self.is_empty():
      raise IndexError("Hàng đợi đang trống! Không thể lấy phần tử.")
    return self._items.pop_front()

  def peek(self):
    """Xem giá trị của phần tử ở đầu hàng đợi mà không xóa"""
    if self.is_empty():
      raise IndexError("Hàng đợi đang trống!")
    return self._items.peek_front()

  def size(self):
    """Trả về số lượng phần tử hiện có trong hàng đợi"""
    return self._items.size()

  def __iter__(self):
    return iter(self._items)

  def display(self):
    """In ra các phần tử trong hàng đợi từ đầu đến cuối (hữu ích để debug)"""
    if self.is_empty():
      print("Hàng đợi trống!")
      return

    elements = []
    for item in self._items:
      elements.append(str(item))
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