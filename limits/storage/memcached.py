from __future__ import annotations

import inspect
import threading
import time
import urllib.parse
from collections.abc import Iterable
from math import ceil, floor
from types import ModuleType

from limits.errors import ConfigurationError
from limits.storage.base import (
    SlidingWindowCounterSupport,
    Storage,
    TimestampedSlidingWindow,
)
from limits.typing import (
    Any,
    Callable,
    MemcachedClientP,
    P,
    R,
    cast,
)
from limits.util import get_dependency


class MemcachedStorage(Storage, SlidingWindowCounterSupport, TimestampedSlidingWindow):
    """
    Rate limit storage with memcached as backend.

    Depends on :pypi:`pymemcache`.
    """

    STORAGE_SCHEME = ["memcached"]
    """The storage scheme for memcached"""
    DEPENDENCIES = ["pymemcache"]

    def __init__(
        self,
        uri: str,
        wrap_exceptions: bool = False,
        **options: str | Callable[[], MemcachedClientP],
    ) -> None:
        """
        :param uri: memcached location of the form
         ``memcached://host:port,host:port``,
         ``memcached:///var/tmp/path/to/sock``
        :param wrap_exceptions: Whether to wrap storage exceptions in
         :exc:`limits.errors.StorageError` before raising it.
        :param options: all remaining keyword arguments are passed
         directly to the constructor of :class:`pymemcache.client.base.PooledClient`
         or :class:`pymemcache.client.hash.HashClient` (if there are more than
         one hosts specified)
        :raise ConfigurationError: when :pypi:`pymemcache` is not available
        """
        parsed = urllib.parse.urlparse(uri)
        self.hosts = []

        for loc in parsed.netloc.strip().split(","):
            if not loc:
                continue
            host, port = loc.split(":")
            self.hosts.append((host, int(port)))
        else:
            # filesystem path to UDS

            if parsed.path and not parsed.netloc and not parsed.port:
                self.hosts = [parsed.path]  # type: ignore

        self.dependency = self.dependencies["pymemcache"].module
        self.library = str(options.pop("library", "pymemcache.client"))
        self.cluster_library = str(
            options.pop("cluster_library", "pymemcache.client.hash")
        )
        self.client_getter = cast(
            Callable[[ModuleType, list[tuple[str, int]]], MemcachedClientP],
            options.pop("client_getter", self.get_client),
        )
        self.options = options

        if not get_dependency(self.library):
            raise ConfigurationError(
                f"memcached prerequisite not available. please install {self.library}"
            )  # pragma: no cover
        self.local_storage = threading.local()
        self.local_storage.storage = None
        super().__init__(uri, wrap_exceptions=wrap_exceptions)

    @property
    def base_exceptions(
        self,
    ) -> type[Exception] | tuple[type[Exception], ...]:  # pragma: no cover
        return self.dependency.MemcacheError  # type: ignore[no-any-return]

    def get_client(
        self, module: ModuleType, hosts: list[tuple[str, int]], **kwargs: str
    ) -> MemcachedClientP:
        """
        returns a memcached client.

        :param module: the memcached module
        :param hosts: list of memcached hosts
        """

        return cast(
            MemcachedClientP,
            (
                module.HashClient(hosts, **kwargs)
                if len(hosts) > 1
                else module.PooledClient(*hosts, **kwargs)
            ),
        )

    def call_memcached_func(
        self, func: Callable[P, R], *args: P.args, **kwargs: P.kwargs
    ) -> R:
        if "noreply" in kwargs:
            argspec = inspect.getfullargspec(func)

            if not ("noreply" in argspec.args or argspec.varkw):
                kwargs.pop("noreply")

        return func(*args, **kwargs)

    @property
    def storage(self) -> MemcachedClientP:
        """
        lazily creates a memcached client instance using a thread local
        """

        if not (hasattr(self.local_storage, "storage") and self.local_storage.storage):
            dependency = get_dependency(
                self.cluster_library if len(self.hosts) > 1 else self.library
            )[0]

            if not dependency:
                raise ConfigurationError(f"Unable to import {self.cluster_library}")
            self.local_storage.storage = self.client_getter(
                dependency, self.hosts, **self.options
            )

        return cast(MemcachedClientP, self.local_storage.storage)

    def get(self, key: str) -> int:
        """
        :param key: the key to get the counter value for
        """
        return int(self.storage.get(key, "0"))

    def get_many(self, keys: Iterable[str]) -> dict[str, Any]:  # type:ignore[explicit-any]
        """
        Return multiple counters at once

        :param keys: the keys to get the counter values for

        :meta private:
        """
        return self.storage.get_many(keys)

    def clear(self, key: str) -> None:
        """
        :param key: the key to clear rate limits for
        """
        self.storage.delete(key)

    def incr(
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
        :param set_expiration_key: set the expiration key with the expiration time if needed. If set to False, the key will still expire, but memcached cannot provide the expiration time.
        """
        if (
            value := self.call_memcached_func(
                self.storage.incr, key, amount, noreply=False
            )
        ) is not None:
            return value
        else:
            if not self.call_memcached_func(
                self.storage.add, key, amount, ceil(expiry), noreply=False
            ):
                return self.storage.incr(key, amount) or amount
            else:
                if set_expiration_key:
                    self.call_memcached_func(
                        self.storage.set,
                        self._expiration_key(key),
                        expiry + time.time(),
                        expire=ceil(expiry),
                        noreply=False,
                    )

            return amount

    def get_expiry(self, key: str) -> float:
        """
        :param key: the key to get the expiry for
        """

        return float(self.storage.get(self._expiration_key(key)) or time.time())

    def _expiration_key(self, key: str) -> str:
        """
        Return the expiration key for the given counter key.

        Memcached doesn't natively return the expiration time or TTL for a given key,
        so we implement the expiration time on a separate key.
        """
        return key + "/expires"

    def check(self) -> bool:
        """
        Check if storage is healthy by calling the ``get`` command
        on the key ``limiter-check``
        """
        try:
            self.call_memcached_func(self.storage.get, "limiter-check")

            return True
        except:  # noqa
            return False

    def reset(self) -> int | None:
        raise NotImplementedError

    def acquire_sliding_window_entry(
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
        previous_count, previous_ttl, current_count, _ = self._get_sliding_window_info(
            previous_key, current_key, expiry, now=now
        )
        weighted_count = previous_count * previous_ttl / expiry + current_count
        if floor(weighted_count) + amount > limit:
            return False
        else:
            # Hit, increase the current counter.
            # If the counter doesn't exist yet, set twice the theorical expiry.
            # We don't need the expiration key as it is estimated with the timestamps directly.
            current_count = self.incr(
                current_key, 2 * expiry, amount=amount, set_expiration_key=False
            )
            actualised_previous_ttl = min(0, previous_ttl - (time.time() - now))
            weighted_count = (
                previous_count * actualised_previous_ttl / expiry + current_count
            )
            if floor(weighted_count) > limit:
                # Another hit won the race condition: revert the incrementation and refuse this hit
                # Limitation: during high concurrency at the end of the window,
                # the counter is shifted and cannot be decremented, so less requests than expected are allowed.
                self.call_memcached_func(
                    self.storage.decr,
                    current_key,
                    amount,
                    noreply=True,
                )
                return False
            return True

    def get_sliding_window(
        self, key: str, expiry: int
    ) -> tuple[int, float, int, float]:
        now = time.time()
        previous_key, current_key = self.sliding_window_keys(key, expiry, now)
        return self._get_sliding_window_info(previous_key, current_key, expiry, now)

    def _get_sliding_window_info(
        self, previous_key: str, current_key: str, expiry: int, now: float
    ) -> tuple[int, float, int, float]:
        result = self.get_many([previous_key, current_key])
        previous_count, current_count = (
            int(result.get(previous_key, 0)),
            int(result.get(current_key, 0)),
        )

        if previous_count == 0:
            previous_ttl = float(0)
        else:
            previous_ttl = (1 - (((now - expiry) / expiry) % 1)) * expiry
        current_ttl = (1 - ((now / expiry) % 1)) * expiry + expiry
        return previous_count, previous_ttl, current_count, current_ttl
