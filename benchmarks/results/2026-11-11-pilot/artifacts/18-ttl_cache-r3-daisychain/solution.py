import math


class TTLCache:
    def __init__(self, capacity, clock):
        if isinstance(capacity, bool) or not isinstance(capacity, int) or capacity <= 0:
            raise ValueError("capacity must be a positive integer")
        self.capacity = capacity
        self.clock = clock
        self.items = {}

    def set(self, key, value, ttl):
        if (
            isinstance(ttl, bool)
            or not isinstance(ttl, (int, float))
            or ttl < 0
            or (isinstance(ttl, float) and not math.isfinite(ttl))
        ):
            raise ValueError("ttl must be a finite nonnegative int or float")
        now = self.clock()
        self._discard_expired(now)
        self.items.pop(key, None)
        if ttl == 0:
            return
        if len(self.items) >= self.capacity:
            self.items.pop(next(iter(self.items)))
        self.items[key] = (value, now + ttl)

    def _discard_expired(self, now):
        expired = [key for key, (_, deadline) in self.items.items() if now >= deadline]
        for key in expired:
            del self.items[key]

    def get(self, key, default=None):
        self._discard_expired(self.clock())
        if key not in self.items:
            return default
        item = self.items.pop(key)
        self.items[key] = item
        return item[0]

    def __len__(self):
        self._discard_expired(self.clock())
        return len(self.items)
