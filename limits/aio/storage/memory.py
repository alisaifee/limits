import threading
import time
from typing import Dict, Tuple, List, Optional
from collections import Counter

from .base import Storage


class LockableEntry(threading._RLock):
    __slots__ = ["atime", "expiry"]

    def __init__(self, expiry: int) -> None:
        self.atime = time.time()
        self.expiry = self.atime + expiry
        super(LockableEntry, self).__init__()


class MemoryStorage(Storage):
    """
    rate limit storage using :class:`collections.Counter`
    as an in memory storage for fixed and elastic window strategies,
    and a simple list to implement moving window strategy.

    """

    STORAGE_SCHEME = ["amemory"]

    def __init__(self, uri: Optional[str] = None, **_: Dict) -> None:
        self.storage: Counter = Counter()
        self.expirations: Dict = {}
        self.events: Dict[str, List[LockableEntry]] = {}
        self.timer = threading.Timer(0.01, self.__expire_events)
        self.timer.start()
        super(MemoryStorage, self).__init__(uri)  # type: ignore

    def __expire_events(self) -> None:
        # this remains a sync function so we can pass it to
        # threading.Timer
        # TODO: can we replace threading.Timer with asyncio.sleep?

        for key in self.events.keys():
            for event in list(self.events[key]):
                with event:
                    if event.expiry <= time.time() and event in self.events[key]:
                        self.events[key].remove(event)

        for key in list(self.expirations.keys()):
            if self.expirations[key] <= time.time():
                self.storage.pop(key, None)
                self.expirations.pop(key, None)

    async def __schedule_expiry(self) -> None:
        if not self.timer.is_alive():
            self.timer = threading.Timer(0.01, self.__expire_events)
            self.timer.start()

    async def incr(self, key: str, expiry: int, elastic_expiry: bool = False) -> int:
        """
        increments the counter for a given rate limit key

        :param key: the key to increment
        :param expiry: amount in seconds for the key to expire in
        :param elastic_expiry: whether to keep extending the rate limit
         window every hit.
        """
        await self.get(key)
        await self.__schedule_expiry()
        self.storage[key] += 1

        if elastic_expiry or self.storage[key] == 1:
            self.expirations[key] = time.time() + expiry

        return self.storage.get(key, 0)

    async def get(self, key: str) -> int:
        """
        :param key: the key to get the counter value for
        """

        if self.expirations.get(key, 0) <= time.time():
            self.storage.pop(key, None)
            self.expirations.pop(key, None)

        return self.storage.get(key, 0)

    async def clear(self, key: str) -> None:
        """
        :param key: the key to clear rate limits for
        """
        self.storage.pop(key, None)
        self.expirations.pop(key, None)
        self.events.pop(key, None)

    async def acquire_entry(
        self, key: str, limit: int, expiry: int, no_add: bool = False
    ) -> bool:
        """
        :param key: rate limit key to acquire an entry in
        :param limit: amount of entries allowed
        :param expiry: expiry of the entry
        :param no_add: if False an entry is not actually acquired
         but instead serves as a 'check'
        :rtype: bool
        """
        self.events.setdefault(key, [])
        await self.__schedule_expiry()
        timestamp = time.time()
        try:
            entry: Optional[LockableEntry] = self.events[key][limit - 1]
        except IndexError:
            entry = None

        if entry and entry.atime >= timestamp - expiry:
            return False
        else:
            if not no_add:
                self.events[key].insert(0, LockableEntry(expiry))

            return True

    async def get_expiry(self, key: str) -> int:
        """
        :param key: the key to get the expiry for
        """

        return int(self.expirations.get(key, -1))

    async def get_num_acquired(self, key: str, expiry: int) -> int:
        """
        returns the number of entries already acquired

        :param key: rate limit key to acquire an entry in
        :param expiry: expiry of the entry
        """
        timestamp = time.time()

        return (
            len([k for k in self.events[key] if k.atime >= timestamp - expiry])
            if self.events.get(key)
            else 0
        )

    # FIXME: arg limit is not used
    async def get_moving_window(
        self, key: str, limit: int, expiry: int
    ) -> Tuple[int, int]:
        """
        returns the starting point and the number of entries in the moving
        window

        :param key: rate limit key
        :param expiry: expiry of entry
        :return: (start of window, number of acquired entries)
        """
        timestamp = time.time()
        acquired = await self.get_num_acquired(key, expiry)

        for item in self.events.get(key, []):
            if item.atime >= timestamp - expiry:
                return int(item.atime), acquired

        return int(timestamp), acquired

    async def check(self) -> bool:
        """
        check if storage is healthy
        """

        return True

    async def reset(self) -> Optional[int]:
        num_items = len(self.storage)
        self.storage.clear()
        self.expirations.clear()
        self.events.clear()
        return num_items
