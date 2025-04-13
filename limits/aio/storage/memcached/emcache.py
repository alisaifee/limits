from __future__ import annotations

import time
from math import ceil
from types import ModuleType

from limits.typing import TYPE_CHECKING, Iterable

from .bridge import MemcachedBridge

if TYPE_CHECKING:
    import emcache


class EmcacheBridge(MemcachedBridge):
    def __init__(
        self,
        uri: str,
        dependency: ModuleType,
        **options: float | str | bool,
    ) -> None:
        super().__init__(uri, dependency, **options)
        self._storage = None

    async def get_storage(self) -> emcache.Client:
        if not self._storage:
            self._storage = await self.dependency.create_client(
                [self.dependency.MemcachedHostAddress(h, p) for h, p in self.hosts],
                **self.options,
            )
        assert self._storage
        return self._storage

    async def get(self, key: str) -> int:
        item = await (await self.get_storage()).get(key.encode("utf-8"))
        return item and int(item.value) or 0

    async def get_many(self, keys: Iterable[str]) -> dict[bytes, int]:
        results = await (await self.get_storage()).get_many(
            [k.encode("utf-8") for k in keys]
        )
        return {k: int(item.value) if item else 0 for k, item in results.items()}

    async def clear(self, key: str) -> None:
        try:
            await (await self.get_storage()).delete(key.encode("utf-8"))
        except self.dependency.NotFoundCommandError:
            pass

    async def decr(self, key: str, amount: int = 1, noreply: bool = False) -> int:
        storage = await self.get_storage()
        limit_key = key.encode("utf-8")
        try:
            value = await storage.decrement(limit_key, amount, noreply=noreply) or 0
        except self.dependency.NotFoundCommandError:
            value = 0
        return value

    async def incr(
        self, key: str, expiry: float, amount: int = 1, set_expiration_key: bool = True
    ) -> int:
        storage = await self.get_storage()
        limit_key = key.encode("utf-8")
        expire_key = self._expiration_key(key).encode()
        try:
            return await storage.increment(limit_key, amount) or amount
        except self.dependency.NotFoundCommandError:
            storage = await self.get_storage()
            try:
                await storage.add(limit_key, f"{amount}".encode(), exptime=ceil(expiry))
                if set_expiration_key:
                    await storage.set(
                        expire_key,
                        str(expiry + time.time()).encode("utf-8"),
                        exptime=ceil(expiry),
                        noreply=False,
                    )
                value = amount
            except self.dependency.NotStoredStorageCommandError:
                # Coult not add the key, probably because a concurrent call has added it
                storage = await self.get_storage()
                value = await storage.increment(limit_key, amount) or amount
            return value

    async def get_expiry(self, key: str) -> float:
        storage = await self.get_storage()
        item = await storage.get(self._expiration_key(key).encode("utf-8"))

        return item and float(item.value) or time.time()
        pass

    @property
    def base_exceptions(
        self,
    ) -> type[Exception] | tuple[type[Exception], ...]:  # pragma: no cover
        return (
            self.dependency.ClusterNoAvailableNodes,
            self.dependency.CommandError,
        )

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
