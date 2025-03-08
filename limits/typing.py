from __future__ import annotations

from collections import Counter
from collections.abc import Awaitable, Iterable
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    ClassVar,
    Literal,
    NamedTuple,
    Optional,
    Type,
    TypeVar,
    Union,
    cast,
)

from typing_extensions import ParamSpec, Protocol, TypeAlias

Serializable = Union[int, str, float]

R = TypeVar("R")
R_co = TypeVar("R_co", covariant=True)
P = ParamSpec("P")


if TYPE_CHECKING:
    import coredis
    import pymongo.collection
    import pymongo.database
    import redis


class ItemP(Protocol):
    value: bytes
    flags: Optional[int]
    cas: Optional[int]


class EmcacheClientP(Protocol):
    async def add(
        self,
        key: bytes,
        value: bytes,
        *,
        flags: int = 0,
        exptime: int = 0,
        noreply: bool = False,
    ) -> None: ...

    async def get(self, key: bytes, return_flags: bool = False) -> Optional[ItemP]: ...

    async def get_many(self, keys: Iterable[bytes]) -> dict[bytes, ItemP]: ...

    async def gets(self, key: bytes, return_flags: bool = False) -> Optional[ItemP]: ...

    async def increment(
        self, key: bytes, value: int, *, noreply: bool = False
    ) -> Optional[int]: ...

    async def decrement(
        self, key: bytes, value: int, *, noreply: bool = False
    ) -> Optional[int]: ...

    async def delete(self, key: bytes, *, noreply: bool = False) -> None: ...

    async def set(
        self,
        key: bytes,
        value: bytes,
        *,
        flags: int = 0,
        exptime: int = 0,
        noreply: bool = False,
    ) -> None: ...

    async def touch(
        self, key: bytes, exptime: int, *, noreply: bool = False
    ) -> None: ...


class MemcachedClientP(Protocol):
    def add(
        self,
        key: str,
        value: Serializable,
        expire: Optional[int] = 0,
        noreply: Optional[bool] = None,
        flags: Optional[int] = None,
    ) -> bool: ...

    def get(self, key: str, default: Optional[str] = None) -> bytes: ...

    def get_many(self, keys: Iterable[str]) -> dict[str, Any]: ...  # type:ignore[explicit-any]

    def incr(
        self, key: str, value: int, noreply: Optional[bool] = False
    ) -> Optional[int]: ...

    def decr(
        self,
        key: str,
        value: int,
        noreply: Optional[bool] = False,
    ) -> Optional[int]: ...

    def delete(self, key: str, noreply: Optional[bool] = None) -> Optional[bool]: ...

    def set(
        self,
        key: str,
        value: Serializable,
        expire: int = 0,
        noreply: Optional[bool] = None,
        flags: Optional[int] = None,
    ) -> bool: ...

    def touch(
        self, key: str, expire: Optional[int] = 0, noreply: Optional[bool] = None
    ) -> bool: ...


class RedisClientP(Protocol):
    def incrby(self, key: str, amount: int) -> int: ...
    def get(self, key: str) -> Optional[bytes]: ...
    def delete(self, key: str) -> int: ...
    def ttl(self, key: str) -> int: ...
    def expire(self, key: str, seconds: int) -> bool: ...
    def ping(self) -> bool: ...
    def register_script(self, script: bytes) -> "redis.commands.core.Script": ...


class AsyncRedisClientP(Protocol):
    async def incrby(self, key: str, amount: int) -> int: ...
    async def get(self, key: str) -> Optional[bytes]: ...
    async def delete(self, key: str) -> int: ...
    async def ttl(self, key: str) -> int: ...
    async def expire(self, key: str, seconds: int) -> bool: ...
    async def ping(self) -> bool: ...
    def register_script(self, script: bytes) -> "redis.commands.core.Script": ...


RedisClient = RedisClientP
AsyncRedisClient = AsyncRedisClientP
AsyncCoRedisClient = Union["coredis.Redis[bytes]", "coredis.RedisCluster[bytes]"]

MongoClient: TypeAlias = "pymongo.MongoClient[dict[str, Any]]"  # type:ignore[explicit-any]
MongoDatabase: TypeAlias = "pymongo.database.Database[dict[str, Any]]"  # type:ignore[explicit-any]
MongoCollection: TypeAlias = "pymongo.collection.Collection[dict[str, Any]]"  # type:ignore[explicit-any]

__all__ = [
    "Any",
    "AsyncRedisClient",
    "Awaitable",
    "Callable",
    "ClassVar",
    "Counter",
    "EmcacheClientP",
    "ItemP",
    "Literal",
    "MemcachedClientP",
    "MongoClient",
    "MongoCollection",
    "MongoDatabase",
    "NamedTuple",
    "Optional",
    "P",
    "ParamSpec",
    "Protocol",
    "Serializable",
    "TypeVar",
    "R",
    "R_co",
    "RedisClient",
    "Type",
    "TypeVar",
    "TYPE_CHECKING",
    "Union",
    "cast",
]
