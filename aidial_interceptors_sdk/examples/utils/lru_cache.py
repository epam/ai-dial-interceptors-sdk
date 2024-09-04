from collections import OrderedDict
from typing import Generic, Hashable, Optional, TypeVar

_K = TypeVar("_K", bound=Hashable)
_V = TypeVar("_V")


class LRUCache(Generic[_K, _V]):
    def __init__(self, maxsize: int = 128) -> None:
        self.cache: OrderedDict[_K, _V] = OrderedDict()
        self.maxsize: int = maxsize

    def lookup(self, key: _K) -> Optional[_V]:
        if key in self.cache:
            self.cache.move_to_end(key)
            return self.cache[key]
        else:
            return None

    def save(self, key: _K, value: _V) -> None:
        if key in self.cache:
            self.cache.move_to_end(key)
        self.cache[key] = value
        if len(self.cache) > self.maxsize:
            self.cache.popitem(last=False)
