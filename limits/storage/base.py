from abc import abstractmethod
import threading

from limits.storage.registry import StorageRegistry


class Storage(metaclass=StorageRegistry):
    """
    Base class to extend when implementing a storage backend.
    """

    def __init__(self, uri: str = None, **options):
        self.lock = threading.RLock()

    @abstractmethod
    def incr(self, key: str, expiry: int, elastic_expiry: bool = False) -> int:
        """
        increments the counter for a given rate limit key

        :param key: the key to increment
        :param expiry: amount in seconds for the key to expire in
        :param elastic_expiry: whether to keep extending the rate limit
         window every hit.
        """
        raise NotImplementedError

    @abstractmethod
    def get(self, key: str) -> int:
        """
        :param key: the key to get the counter value for
        """
        raise NotImplementedError

    @abstractmethod
    def get_expiry(self, key: str) -> int:
        """
        :param key: the key to get the expiry for
        """
        raise NotImplementedError

    @abstractmethod
    def check(self) -> bool:
        """
        check if storage is healthy
        """
        raise NotImplementedError

    @abstractmethod
    def reset(self):
        """
        reset storage to clear limits
        """
        raise NotImplementedError

    @abstractmethod
    def clear(self, key: str):
        """
        resets the rate limit key
        :param key: the key to clear rate limits for
        """
        raise NotImplementedError
