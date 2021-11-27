import threading
import time
from collections import Counter

from .base import Storage


class LockableEntry(threading._RLock):
    __slots__ = ["atime", "expiry"]

    def __init__(self, expiry):
        self.atime = time.time()
        self.expiry = self.atime + expiry
        super(LockableEntry, self).__init__()


class MemoryStorage(Storage):
    """
    rate limit storage using :class:`collections.Counter`
    as an in memory storage for fixed and elastic window strategies,
    and a simple list to implement moving window strategy.

    """

    STORAGE_SCHEME = ["memory"]

    def __init__(self, uri=None, **_):
        self.storage = Counter()
        self.expirations = {}
        self.events = {}
        self.timer = threading.Timer(0.01, self.__expire_events)
        self.timer.start()
        super(MemoryStorage, self).__init__(uri)

    def __expire_events(self):
        for key in self.events.keys():
            for event in list(self.events[key]):
                with event:
                    if event.expiry <= time.time() and event in self.events[key]:
                        self.events[key].remove(event)
        for key in list(self.expirations.keys()):
            if self.expirations[key] <= time.time():
                self.storage.pop(key, None)
                self.expirations.pop(key, None)

    def __schedule_expiry(self):
        if not self.timer.is_alive():
            self.timer = threading.Timer(0.01, self.__expire_events)
            self.timer.start()

    def incr(self, key, expiry, elastic_expiry=False):
        """
        increments the counter for a given rate limit key

        :param str key: the key to increment
        :param int expiry: amount in seconds for the key to expire in
        :param bool elastic_expiry: whether to keep extending the rate limit
         window every hit.
        """
        self.get(key)
        self.__schedule_expiry()
        self.storage[key] += 1
        if elastic_expiry or self.storage[key] == 1:
            self.expirations[key] = time.time() + expiry
        return self.storage.get(key, 0)

    def get(self, key):
        """
        :param str key: the key to get the counter value for
        """
        if self.expirations.get(key, 0) <= time.time():
            self.storage.pop(key, None)
            self.expirations.pop(key, None)
        return self.storage.get(key, 0)

    def clear(self, key):
        """
        :param str key: the key to clear rate limits for
        """
        self.storage.pop(key, None)
        self.expirations.pop(key, None)
        self.events.pop(key, None)

    def acquire_entry(self, key, limit, expiry, no_add=False):
        """
        :param str key: rate limit key to acquire an entry in
        :param int limit: amount of entries allowed
        :param int expiry: expiry of the entry
        :param bool no_add: if False an entry is not actually acquired
         but instead serves as a 'check'
        :rtype: bool
        """
        self.events.setdefault(key, [])
        self.__schedule_expiry()
        timestamp = time.time()
        try:
            entry = self.events[key][limit - 1]
        except IndexError:
            entry = None
        if entry and entry.atime >= timestamp - expiry:
            return False
        else:
            if not no_add:
                self.events[key].insert(0, LockableEntry(expiry))
            return True

    def get_expiry(self, key):
        """
        :param str key: the key to get the expiry for
        """
        return int(self.expirations.get(key, -1))

    def get_num_acquired(self, key, expiry):
        """
        returns the number of entries already acquired

        :param str key: rate limit key to acquire an entry in
        :param int expiry: expiry of the entry
        """
        timestamp = time.time()
        return (
            len([k for k in self.events[key] if k.atime >= timestamp - expiry])
            if self.events.get(key)
            else 0
        )

    def get_moving_window(self, key, limit, expiry):
        """
        returns the starting point and the number of entries in the moving
        window

        :param str key: rate limit key
        :param int expiry: expiry of entry
        :return: (start of window, number of acquired entries)
        """
        timestamp = time.time()
        acquired = self.get_num_acquired(key, expiry)
        for item in self.events.get(key, []):
            if item.atime >= timestamp - expiry:
                return int(item.atime), acquired
        return int(timestamp), acquired

    def check(self):
        """
        check if storage is healthy
        """
        return True

    def reset(self):
        self.storage.clear()
        self.expirations.clear()
        self.events.clear()
