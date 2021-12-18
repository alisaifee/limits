from abc import abstractmethod
from abc import ABC
from typing import Any, Dict, List, Optional, Tuple


from limits.storage.registry import StorageRegistry
from limits.util import get_dependency
from limits.errors import ConfigurationError


class Storage(metaclass=StorageRegistry):
    """
    Base class to extend when implementing an async storage backend.

    .. danger:: Experimental
    .. versionadded:: 2.1
    """

    DEPENDENCIES: List[str] = []

    def __init__(self, uri: Optional[str] = None, **options: Dict) -> None:
        self._dependencies: Dict[str, Any] = {}

    @property
    def dependencies(self) -> Dict[str, Any]:
        if not self._dependencies:
            for name in self.DEPENDENCIES:
                dependency = get_dependency(name)

                if not dependency:
                    raise ConfigurationError(
                        f"{name} prerequisite not available"
                    )  # pragma: no cover
                self._dependencies[name] = dependency

        return self._dependencies

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


class MovingWindowSupport(ABC):
    """
    Abstract base for storages that intend to support
    the moving window strategy

    .. danger:: Experimental
    .. versionadded:: 2.1
    """

    async def acquire_entry(
        self, key: str, limit: int, expiry: int, no_add=False
    ) -> bool:
        """
        :param key: rate limit key to acquire an entry in
        :param limit: amount of entries allowed
        :param expiry: expiry of the entry
        :param no_add: if False an entry is not actually acquired
         but instead serves as a 'check'
        """
        raise NotImplementedError

    async def get_moving_window(self, key, limit, expiry) -> Tuple[int, int]:
        """
        returns the starting point and the number of entries in the moving
        window

        :param key: rate limit key
        :param expiry: expiry of entry
        :return: (start of window, number of acquired entries)
        """
        raise NotImplementedError
