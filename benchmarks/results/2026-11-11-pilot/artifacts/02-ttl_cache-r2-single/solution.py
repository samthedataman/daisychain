import math
from fractions import Fraction


class TTLCache:
    def __init__(self, capacity, clock):
        if isinstance(capacity, bool) or not isinstance(capacity, int) or capacity <= 0:
            raise ValueError("capacity must be a positive integer")
        self.capacity = capacity
        self.clock = clock
        self.items = {}

    def _discard_expired(self, now):
        expired = [key for key, (_, deadline) in self.items.items() if now >= deadline]
        for key in expired:
            del self.items[key]

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
        try:
            deadline = now + ttl
        except OverflowError:
            # Very large integers are finite even when float conversion fails.
            deadline = Fraction(now) + Fraction(ttl)
        self.items[key] = (value, deadline)
        if len(self.items) > self.capacity:
            del self.items[next(iter(self.items))]

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
