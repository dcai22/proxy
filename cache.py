from collections import OrderedDict
import threading

class Cache:
    def __init__(self, maxObjectSize: int, maxCacheSize: int) -> None:
        self.cacheSize: int = 0
        self.cacheMap: OrderedDict[str, bytes] = OrderedDict()   # Maps target to response
        self.maxObjectSize: int = maxObjectSize
        self.maxCacheSize: int = maxCacheSize
        self.lock: threading.Lock = threading.Lock()

    def _remove(self, target: str) -> tuple[str, bytes] | None:
        try:
            response = self.cacheMap[target]
            del self.cacheMap[target]
            self.cacheSize -= len(response)
            return (target, response)
        except KeyError:
            return None

    def _pop(self) -> tuple[str, bytes] | None:
        try:
            entry = self.cacheMap.popitem()
            self.cacheSize -= len(entry[1])
            return entry
        except KeyError:
            return None

    def lookup(self, target: str) -> bytes | None:
        with self.lock:
            try:
                self.cacheMap.move_to_end(target, False)
                return self.cacheMap[target]
            except KeyError:
                return None

    def cache(self, target: str, response: bytes) -> bool:
        with self.lock:
            self._remove(target)
            if len(response) > self.maxObjectSize:
                return False
            while self.cacheSize + len(response) > self.maxCacheSize:
                self._pop()
            self.cacheMap[target] = response
            self.cacheSize += len(response)
            return True
