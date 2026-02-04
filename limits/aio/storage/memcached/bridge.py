from __future__ import annotations

from abc import ABC, abstractmethod
from types import ModuleType

from limits._storage_scheme import parse_storage_uri
from limits.typing import Iterable


class MemcachedBridge(ABC):
    def __init__(
        self,
        uri: str,
        dependency: ModuleType,
        **options: float | str | bool,
    ) -> None:
        self.uri = uri
        self.parsed_uri = parse_storage_uri(uri)
        self.dependency = dependency
        self.hosts = self.parsed_uri.locations
        self.options = options

        if self.parsed_uri.username:
            self.options["username"] = self.parsed_uri.username
        if self.parsed_uri.password:
            self.options["password"] = self.parsed_uri.password

    def _expiration_key(self, key: str) -> str:
        """
        Return the expiration key for the given counter key.

        Memcached doesn't natively return the expiration time or TTL for a given key,
        so we implement the expiration time on a separate key.
        """
        return key + "/expires"

    @property
    @abstractmethod
    def base_exceptions(
        self,
    ) -> type[Exception] | tuple[type[Exception], ...]: ...

    @abstractmethod
    async def get(self, key: str) -> int: ...

    @abstractmethod
    async def get_many(self, keys: Iterable[str]) -> dict[bytes, int]: ...

    @abstractmethod
    async def clear(self, key: str) -> None: ...

    @abstractmethod
    async def decr(self, key: str, amount: int = 1, noreply: bool = False) -> int: ...

    @abstractmethod
    async def incr(
        self,
        key: str,
        expiry: float,
        amount: int = 1,
        set_expiration_key: bool = True,
    ) -> int: ...

    @abstractmethod
    async def get_expiry(self, key: str) -> float: ...

    @abstractmethod
    async def check(self) -> bool: ...
