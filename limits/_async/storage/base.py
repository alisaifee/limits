import threading
from abc import abstractmethod
from typing import Dict, Optional

from limits.storage.registry import StorageRegistry


class AsyncStorage(metaclass=StorageRegistry):
    """
    Base class to extend when implementing an async storage backend.
    """

    def __init__(self, uri: Optional[str] = None, **options: Dict) -> None:
        self.lock = threading.RLock()

    @abstractmethod
    async def incr(self, key: str, expiry: int, elastic_expiry: bool = False) -> int:
        """
        increments the counter for a given rate limit key

        :param str key: the key to increment
        :param int expiry: amount in seconds for the key to expire in
        :param bool elastic_expiry: whether to keep extending the rate limit
         window every hit.
        """
        raise NotImplementedError

    @abstractmethod
    async def get(self, key: str) -> int:
        """
        :param str key: the key to get the counter value for
        """
        raise NotImplementedError

    @abstractmethod
    async def get_expiry(self, key: str) -> int:
        """
        :param str key: the key to get the expiry for
        """
        raise NotImplementedError

    @abstractmethod
    async def check(self) -> bool:
        """
        check if storage is healthy
        """
        raise NotImplementedError

    @abstractmethod
    async def reset(self) -> Optional[int]:
        """
        reset storage to clear limits
        """
        raise NotImplementedError

    @abstractmethod
    async def clear(self, key: str) -> int:
        """
        resets the rate limit key
        :param str key: the key to clear rate limits for
        """
        raise NotImplementedError
