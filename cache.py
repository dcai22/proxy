from collections import OrderedDict
import threading

class Cache:
    def __init__(self, maxObjectSize, maxCacheSize):
        self.cacheSize = 0
        self.cacheMap = OrderedDict()   # Maps target to response
        self.maxObjectSize = maxObjectSize
        self.maxCacheSize = maxCacheSize
        self.lock = threading.Lock()

    def _remove(self, target):
        try:
            response = self.cacheMap[target]
            del self.cacheMap[target]
            self.cacheSize -= len(response)
            return (target, response)
        except KeyError:
            return None

    def _pop(self):
        try:
            entry = self.cacheMap.popitem()
            self.cacheSize -= len(entry[1])
            return entry
        except KeyError:
            return None

    def lookup(self, target):
        with self.lock:
            try:
                self.cacheMap.move_to_end(target, False)
                return self.cacheMap[target]
            except KeyError:
                return None

    def cache(self, target, response):
        with self.lock:
            self._remove(target)
            if len(response) > self.maxObjectSize:
                return False
            while self.cacheSize + len(response) > self.maxCacheSize:
                self._pop()
            self.cacheMap[target] = response
            self.cacheSize += len(response)
            return True
