from __future__ import annotations

import time
from math import ceil
from types import ModuleType
from typing import TYPE_CHECKING, Iterable

from .bridge import MemcachedBridge

if TYPE_CHECKING:
    import memcachio


class MemcachioBridge(MemcachedBridge):
    def __init__(
        self,
        uri: str,
        dependency: ModuleType,
        **options: float | str | bool,
    ) -> None:
        super().__init__(uri, dependency, **options)
        self._storage: memcachio.Client[bytes] | None = None

    @property
    def base_exceptions(
        self,
    ) -> type[Exception] | tuple[type[Exception], ...]:
        return (
            self.dependency.errors.NoAvailableNodes,
            self.dependency.errors.MemcachioConnectionError,
        )

    async def get_storage(self) -> memcachio.Client[bytes]:
        if not self._storage:
            self._storage = self.dependency.Client(
                [(h, p) for h, p in self.hosts],
                **self.options,
            )
        assert self._storage
        return self._storage

    async def get(self, key: str) -> int:
        return (await self.get_many([key])).get(key.encode("utf-8"), 0)

    async def get_many(self, keys: Iterable[str]) -> dict[bytes, int]:
        """
        Return multiple counters at once

        :param keys: the keys to get the counter values for
        """
        results = await (await self.get_storage()).get(
            *[k.encode("utf-8") for k in keys]
        )
        return {k: int(v.value) for k, v in results.items()}

    async def clear(self, key: str) -> None:
        await (await self.get_storage()).delete(key.encode("utf-8"))

    async def decr(self, key: str, amount: int = 1, noreply: bool = False) -> int:
        storage = await self.get_storage()
        limit_key = key.encode("utf-8")
        return await storage.decr(limit_key, amount, noreply=noreply) or 0

    async def incr(
        self, key: str, expiry: float, amount: int = 1, set_expiration_key: bool = True
    ) -> int:
        storage = await self.get_storage()
        limit_key = key.encode("utf-8")
        expire_key = self._expiration_key(key).encode()
        if (value := (await storage.incr(limit_key, amount))) is None:
            storage = await self.get_storage()
            if await storage.add(limit_key, f"{amount}".encode(), expiry=ceil(expiry)):
                if set_expiration_key:
                    await storage.set(
                        expire_key,
                        str(expiry + time.time()).encode("utf-8"),
                        expiry=ceil(expiry),
                        noreply=False,
                    )
                return amount
            else:
                storage = await self.get_storage()
                return await storage.incr(limit_key, amount) or amount
        return value

    async def get_expiry(self, key: str) -> float:
        storage = await self.get_storage()
        expiration_key = self._expiration_key(key).encode("utf-8")
        item = (await storage.get(expiration_key)).get(expiration_key, None)

        return item and float(item.value) or time.time()

    async def check(self) -> bool:
        """
        Check if storage is healthy by calling the ``get`` command
        on the key ``limiter-check``
        """
        try:
            storage = await self.get_storage()
            await storage.get(b"limiter-check")

            return True
        except:  # noqa
            return False
