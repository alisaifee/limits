from __future__ import annotations

import time
from math import floor

from deprecated.sphinx import versionadded, versionchanged
from packaging.version import Version

from limits.aio.storage import SlidingWindowCounterSupport, Storage
from limits.aio.storage.memcached.bridge import MemcachedBridge
from limits.aio.storage.memcached.emcache import EmcacheBridge
from limits.aio.storage.memcached.memcachio import MemcachioBridge
from limits.storage.base import TimestampedSlidingWindow
from limits.typing import Literal


@versionadded(version="2.1")
@versionchanged(
    version="5.0",
    reason="Switched default implementation to :pypi:`memcachio`",
)
class MemcachedStorage(Storage, SlidingWindowCounterSupport, TimestampedSlidingWindow):
    """
    Rate limit storage with memcached as backend.

    Depends on :pypi:`memcachio`
    """

    STORAGE_SCHEME = ["async+memcached"]
    """The storage scheme for memcached to be used in an async context"""

    DEPENDENCIES = {
        "memcachio": Version("0.3"),
        "emcache": Version("0.0"),
    }

    bridge: MemcachedBridge
    storage_exceptions: tuple[Exception, ...]

    def __init__(
        self,
        uri: str,
        wrap_exceptions: bool = False,
        implementation: Literal["memcachio", "emcache"] = "memcachio",
        **options: float | str | bool,
    ) -> None:
        """
        :param uri: memcached location of the form
         ``async+memcached://host:port,host:port``
        :param wrap_exceptions: Whether to wrap storage exceptions in
         :exc:`limits.errors.StorageError` before raising it.
        :param implementation: Whether to use the client implementation from

         - ``memcachio``: :class:`memcachio.Client`
         - ``emcache``: :class:`emcache.Client`
        :param options: all remaining keyword arguments are passed
         directly to the constructor of :class:`memcachio.Client`
        :raise ConfigurationError: when :pypi:`memcachio` is not available
        """
        if implementation == "emcache":
            self.bridge = EmcacheBridge(
                uri, self.dependencies["emcache"].module, **options
            )
        else:
            self.bridge = MemcachioBridge(
                uri, self.dependencies["memcachio"].module, **options
            )
        super().__init__(uri, wrap_exceptions=wrap_exceptions, **options)

    @property
    def base_exceptions(
        self,
    ) -> type[Exception] | tuple[type[Exception], ...]:  # pragma: no cover
        return self.bridge.base_exceptions

    async def get(self, key: str) -> int:
        """
        :param key: the key to get the counter value for
        """
        return await self.bridge.get(key)

    async def clear(self, key: str) -> None:
        """
        :param key: the key to clear rate limits for
        """
        await self.bridge.clear(key)

    async def incr(
        self,
        key: str,
        expiry: float,
        amount: int = 1,
        set_expiration_key: bool = True,
    ) -> int:
        """
        increments the counter for a given rate limit key

        :param key: the key to increment
        :param expiry: amount in seconds for the key to expire in
         window every hit.
        :param amount: the number to increment by
        :param set_expiration_key: if set to False, the expiration time won't be stored but the key will still expire
        """
        return await self.bridge.incr(
            key, expiry, amount, set_expiration_key=set_expiration_key
        )

    async def get_expiry(self, key: str) -> float:
        """
        :param key: the key to get the expiry for
        """
        return await self.bridge.get_expiry(key)

    async def reset(self) -> int | None:
        raise NotImplementedError

    async def check(self) -> bool:
        return await self.bridge.check()

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
                # Another hit won the race condition: revert the increment and refuse this hit
                # Limitation: during high concurrency at the end of the window,
                # the counter is shifted and cannot be decremented, so less requests than expected are allowed.
                await self.bridge.decr(current_key, amount, noreply=True)
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
        result = await self.bridge.get_many([previous_key, current_key])

        previous_count = result.get(previous_key.encode("utf-8"), 0)
        current_count = result.get(current_key.encode("utf-8"), 0)

        if previous_count == 0:
            previous_ttl = float(0)
        else:
            previous_ttl = (1 - (((now - expiry) / expiry) % 1)) * expiry
        current_ttl = (1 - ((now / expiry) % 1)) * expiry + expiry

        return previous_count, previous_ttl, current_count, current_ttl
