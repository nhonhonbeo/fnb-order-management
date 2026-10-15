"""Hash Map khởi đầu; hiện dùng dict làm nền để nhóm dễ tích hợp."""
class HashMap:
    def __init__(self):
        self._data = {}
    def put(self, key, value):
        self._data[key] = value
    def get(self, key):
        return self._data.get(key)
    def remove(self, key):
        if key not in self._data:
            raise KeyError(key)
        del self._data[key]
    def contains(self, key):
        return key in self._data
    def size(self):
        return len(self._data)
