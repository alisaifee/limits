from __future__ import annotations

import time
import urllib.parse
from collections.abc import Iterable
from math import ceil, floor

from deprecated.sphinx import versionadded

from limits.aio.storage.base import SlidingWindowCounterSupport, Storage
from limits.storage.base import TimestampedSlidingWindow
from limits.typing import EmcacheClientP, ItemP, Optional, Type, Union


@versionadded(version="2.1")
class MemcachedStorage(Storage, SlidingWindowCounterSupport, TimestampedSlidingWindow):
    """
    Rate limit storage with memcached as backend.

    Depends on :pypi:`emcache`
    """

    STORAGE_SCHEME = ["async+memcached"]
    """The storage scheme for memcached to be used in an async context"""

    DEPENDENCIES = ["emcache"]

    def __init__(
        self,
        uri: str,
        wrap_exceptions: bool = False,
        **options: Union[float, str, bool],
    ) -> None:
        """
        :param uri: memcached location of the form
         ``async+memcached://host:port,host:port``
        :param wrap_exceptions: Whether to wrap storage exceptions in
         :exc:`limits.errors.StorageError` before raising it.
        :param options: all remaining keyword arguments are passed
         directly to the constructor of :class:`emcache.Client`
        :raise ConfigurationError: when :pypi:`emcache` is not available
        """
        parsed = urllib.parse.urlparse(uri)
        self.hosts = []

        for host, port in (
            loc.split(":") for loc in parsed.netloc.strip().split(",") if loc.strip()
        ):
            self.hosts.append((host, int(port)))

        self._options = options
        self._storage = None
        super().__init__(uri, wrap_exceptions=wrap_exceptions, **options)
        self.dependency = self.dependencies["emcache"].module

    @property
    def base_exceptions(
        self,
    ) -> Union[Type[Exception], tuple[Type[Exception], ...]]:  # pragma: no cover
        return (
            self.dependency.ClusterNoAvailableNodes,
            self.dependency.CommandError,
        )

    async def get_storage(self) -> EmcacheClientP:
        if not self._storage:
            self._storage = await self.dependency.create_client(
                [self.dependency.MemcachedHostAddress(h, p) for h, p in self.hosts],
                **self._options,
            )
        assert self._storage
        return self._storage

    async def get(self, key: str) -> int:
        """
        :param key: the key to get the counter value for
        """
        item = await (await self.get_storage()).get(key.encode("utf-8"))

        return item and int(item.value) or 0

    async def get_many(self, keys: Iterable[str]) -> dict[bytes, ItemP]:
        """
        Return multiple counters at once

        :param keys: the keys to get the counter values for
        """
        return await (await self.get_storage()).get_many(
            [k.encode("utf-8") for k in keys]
        )

    async def clear(self, key: str) -> None:
        """
        :param key: the key to clear rate limits for
        """
        await (await self.get_storage()).delete(key.encode("utf-8"))

    async def decr(self, key: str, amount: int = 1, noreply: bool = False) -> int:
        """
        decrements the counter for a given rate limit key

        retursn 0 if the key doesn't exist or if noreply is set to True

        :param key: the key to decrement
        :param amount: the number to decrement by
        :param noreply: set to True to ignore the memcached response
        """
        storage = await self.get_storage()
        limit_key = key.encode("utf-8")
        try:
            value = await storage.decrement(limit_key, amount, noreply=noreply) or 0
        except self.dependency.NotFoundCommandError:
            value = 0
        return value

    async def incr(
        self,
        key: str,
        expiry: float,
        elastic_expiry: bool = False,
        amount: int = 1,
        set_expiration_key: bool = True,
    ) -> int:
        """
        increments the counter for a given rate limit key

        :param key: the key to increment
        :param expiry: amount in seconds for the key to expire in
        :param elastic_expiry: whether to keep extending the rate limit
         window every hit.
        :param amount: the number to increment by
        :param set_expiration_key: if set to False, the expiration time won't be stored but the key will still expire
        """
        storage = await self.get_storage()
        limit_key = key.encode("utf-8")
        expire_key = self._expiration_key(key).encode()
        value = None
        try:
            value = await storage.increment(limit_key, amount) or amount
            if elastic_expiry:
                await storage.touch(limit_key, exptime=ceil(expiry))
                if set_expiration_key:
                    await storage.set(
                        expire_key,
                        str(expiry + time.time()).encode("utf-8"),
                        exptime=ceil(expiry),
                        noreply=False,
                    )
            return value
        except self.dependency.NotFoundCommandError:
            # Incrementation failed because the key doesn't exist
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
                if elastic_expiry:
                    await storage.touch(limit_key, exptime=ceil(expiry))
                    if set_expiration_key:
                        await storage.set(
                            expire_key,
                            str(expiry + time.time()).encode("utf-8"),
                            exptime=ceil(expiry),
                            noreply=False,
                        )
            return value

    async def get_expiry(self, key: str) -> float:
        """
        :param key: the key to get the expiry for
        """
        storage = await self.get_storage()
        item = await storage.get(self._expiration_key(key).encode("utf-8"))

        return item and float(item.value) or time.time()

    def _expiration_key(self, key: str) -> str:
        """
        Return the expiration key for the given counter key.

        Memcached doesn't natively return the expiration time or TTL for a given key,
        so we implement the expiration time on a separate key.
        """
        return key + "/expires"

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

    async def reset(self) -> Optional[int]:
        raise NotImplementedError

    async def acquire_sliding_window_entry(
        self,
        key: str,
        limit: int,
        expiry: int,
        amount: int = 1,
    ) -> bool:
        if amount > limit:
            return False
        now = time.time()
        previous_key, current_key = self.sliding_window_keys(key, expiry, now)
        (
            previous_count,
            previous_ttl,
            current_count,
            _,
        ) = await self._get_sliding_window_info(previous_key, current_key, expiry, now)
        t0 = time.time()
        weighted_count = previous_count * previous_ttl / expiry + current_count
        if floor(weighted_count) + amount > limit:
            return False
        else:
            # Hit, increase the current counter.
            # If the counter doesn't exist yet, set twice the theorical expiry.
            # We don't need the expiration key as it is estimated with the timestamps directly.
            current_count = await self.incr(
                current_key, 2 * expiry, amount=amount, set_expiration_key=False
            )
            t1 = time.time()
            actualised_previous_ttl = max(0, previous_ttl - (t1 - t0))
            weighted_count = (
                previous_count * actualised_previous_ttl / expiry + current_count
            )
            if floor(weighted_count) > limit:
                # Another hit won the race condition: revert the incrementation and refuse this hit
                # Limitation: during high concurrency at the end of the window,
                # the counter is shifted and cannot be decremented, so less requests than expected are allowed.
                await self.decr(current_key, amount, noreply=True)
                return False
            return True

    async def get_sliding_window(
        self, key: str, expiry: int
    ) -> tuple[int, float, int, float]:
        now = time.time()
        previous_key, current_key = self.sliding_window_keys(key, expiry, now)
        return await self._get_sliding_window_info(
            previous_key, current_key, expiry, now
        )

    async def _get_sliding_window_info(
        self, previous_key: str, current_key: str, expiry: int, now: float
    ) -> tuple[int, float, int, float]:
        result = await self.get_many([previous_key, current_key])

        raw_previous_count = result.get(previous_key.encode("utf-8"))
        raw_current_count = result.get(current_key.encode("utf-8"))

        current_count = raw_current_count and int(raw_current_count.value) or 0
        previous_count = raw_previous_count and int(raw_previous_count.value) or 0
        if previous_count == 0:
            previous_ttl = float(0)
        else:
            previous_ttl = (1 - (((now - expiry) / expiry) % 1)) * expiry
        current_ttl = (1 - ((now / expiry) % 1)) * expiry + expiry

        return previous_count, previous_ttl, current_count, current_ttl
