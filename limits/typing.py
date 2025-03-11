from __future__ import annotations

from collections import Counter
from collections.abc import Awaitable, Callable, Iterable
from typing import (
    TYPE_CHECKING,
    Any,
    ClassVar,
    Literal,
    NamedTuple,
    ParamSpec,
    Protocol,
    TypeAlias,
    TypeVar,
    cast,
)

Serializable = int | str | float

R = TypeVar("R")
R_co = TypeVar("R_co", covariant=True)
P = ParamSpec("P")


if TYPE_CHECKING:
    import coredis
    import pymongo.collection
    import pymongo.database
    import pymongo.mongo_client
    import redis


class ItemP(Protocol):
    value: bytes
    flags: int | None
    cas: int | None


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

    async def get(self, key: bytes, return_flags: bool = False) -> ItemP | None: ...

    async def get_many(self, keys: Iterable[bytes]) -> dict[bytes, ItemP]: ...

    async def gets(self, key: bytes, return_flags: bool = False) -> ItemP | None: ...

    async def increment(
        self, key: bytes, value: int, *, noreply: bool = False
    ) -> int | None: ...

    async def decrement(
        self, key: bytes, value: int, *, noreply: bool = False
    ) -> int | None: ...

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
        expire: int | None = 0,
        noreply: bool | None = None,
        flags: int | None = None,
    ) -> bool: ...

    def get(self, key: str, default: str | None = None) -> bytes: ...

    def get_many(self, keys: Iterable[str]) -> dict[str, Any]: ...  # type:ignore[explicit-any]

    def incr(
        self, key: str, value: int, noreply: bool | None = False
    ) -> int | None: ...

    def decr(
        self,
        key: str,
        value: int,
        noreply: bool | None = False,
    ) -> int | None: ...

    def delete(self, key: str, noreply: bool | None = None) -> bool | None: ...

    def set(
        self,
        key: str,
        value: Serializable,
        expire: int = 0,
        noreply: bool | None = None,
        flags: int | None = None,
    ) -> bool: ...

    def touch(
        self, key: str, expire: int | None = 0, noreply: bool | None = None
    ) -> bool: ...


class RedisClientP(Protocol):
    def incrby(self, key: str, amount: int) -> int: ...
    def get(self, key: str) -> bytes | None: ...
    def delete(self, key: str) -> int: ...
    def ttl(self, key: str) -> int: ...
    def expire(self, key: str, seconds: int) -> bool: ...
    def ping(self) -> bool: ...
    def register_script(self, script: bytes) -> redis.commands.core.Script: ...


class AsyncRedisClientP(Protocol):
    async def incrby(self, key: str, amount: int) -> int: ...
    async def get(self, key: str) -> bytes | None: ...
    async def delete(self, key: str) -> int: ...
    async def ttl(self, key: str) -> int: ...
    async def expire(self, key: str, seconds: int) -> bool: ...
    async def ping(self) -> bool: ...
    def register_script(self, script: bytes) -> redis.commands.core.Script: ...


RedisClient: TypeAlias = RedisClientP
AsyncRedisClient: TypeAlias = AsyncRedisClientP
AsyncCoRedisClient: TypeAlias = "coredis.Redis[bytes] | coredis.RedisCluster[bytes]"

MongoClient: TypeAlias = "pymongo.mongo_client.MongoClient[dict[str, Any]]"  # type:ignore[explicit-any]
MongoDatabase: TypeAlias = "pymongo.database.Database[dict[str, Any]]"  # type:ignore[explicit-any]
MongoCollection: TypeAlias = "pymongo.collection.Collection[dict[str, Any]]"  # type:ignore[explicit-any]

__all__ = [
    "TYPE_CHECKING",
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
    "P",
    "ParamSpec",
    "Protocol",
    "R",
    "R_co",
    "RedisClient",
    "Serializable",
    "TypeAlias",
    "TypeVar",
    "cast",
]
