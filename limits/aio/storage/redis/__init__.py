from __future__ import annotations

from typing import Optional, Type, Union

from deprecated.sphinx import versionadded, versionchanged
from packaging.version import Version

from limits.aio.storage import MovingWindowSupport, SlidingWindowCounterSupport, Storage
from limits.aio.storage.redis.bridge import RedisBridge
from limits.aio.storage.redis.coredis import CoredisBridge
from limits.aio.storage.redis.redispy import RedispyBridge
from limits.typing import Literal


@versionadded(version="2.1")
@versionchanged(
    version="4.2",
    reason=(
        "Added support for using the asyncio redis client from :pypi:`redis`"
        " through :paramref:`implementation`"
    ),
)
class RedisStorage(Storage, MovingWindowSupport, SlidingWindowCounterSupport):
    """
    Rate limit storage with redis as backend.

    Depends on :pypi:`coredis` or :pypi:`redis`
    """

    STORAGE_SCHEME = ["async+redis", "async+rediss", "async+redis+unix"]
    """
    The storage schemes for redis to be used in an async context
    """
    DEPENDENCIES = {"redis": Version("5.2.0"), "coredis": Version("3.4.0")}
    MODE: Literal["BASIC", "CLUSTER", "SENTINEL"] = "BASIC"
    bridge: RedisBridge
    storage_exceptions: tuple[Exception, ...]

    def __init__(
        self,
        uri: str,
        wrap_exceptions: bool = False,
        implementation: Literal["redispy", "coredis"] = "coredis",
        **options: Union[float, str, bool],
    ) -> None:
        """
        :param uri: uri of the form:

         - ``async+redis://[:password]@host:port``
         - ``async+redis://[:password]@host:port/db``
         - ``async+rediss://[:password]@host:port``
         - ``async+redis+unix:///path/to/sock?db=0`` etc...

         This uri is passed directly to :meth:`coredis.Redis.from_url` or
          :meth:`redis.asyncio.client.Redis.from_url` with the initial ``async`` removed,
          except for the case of ``async+redis+unix`` where it is replaced with ``unix``.
        :param connection_pool: if provided, the redis client is initialized with
         the connection pool and any other params passed as :paramref:`options`
        :param wrap_exceptions: Whether to wrap storage exceptions in
         :exc:`limits.errors.StorageError` before raising it.
        :param implementation: Whether to use the client implementation from
         :class:`coredis.Redis` (``coredis``) or :class:`redis.asyncio.client.Redis` (``redispy``).
        :param options: all remaining keyword arguments are passed
         directly to the constructor of :class:`coredis.Redis` or :class:`redis.asyncio.client.Redis`
        :raise ConfigurationError: when the redis library is not available
        """
        uri = uri.replace("async+redis", "redis", 1)
        uri = uri.replace("redis+unix", "unix")

        super().__init__(uri, wrap_exceptions=wrap_exceptions)
        self.options = options
        if implementation == "redispy":
            self.bridge = RedispyBridge(uri, self.dependencies["redis"].module)
        else:
            self.bridge = CoredisBridge(uri, self.dependencies["coredis"].module)
        self.configure_bridge()
        self.bridge.register_scripts()

    def _current_window_key(self, key: str) -> str:
        """
        Return the current window's storage key (Sliding window strategy)

        Contrary to other strategies that have one key per rate limit item,
        this strategy has two keys per rate limit item than must be on the same machine.
        To keep the current key and the previous key on the same Redis cluster node,
        curly braces are added.

        Eg: "{constructed_key}"
        """
        return f"{{{key}}}"

    def _previous_window_key(self, key: str) -> str:
        """
        Return the previous window's storage key (Sliding window strategy).

        Curvy braces are added on the common pattern with the current window's key,
        so the current and the previous key are stored on the same Redis cluster node.

        Eg: "{constructed_key}/-1"
        """
        return f"{self._current_window_key(key)}/-1"

    def configure_bridge(self) -> None:
        self.bridge.use_basic(**self.options)

    @property
    def base_exceptions(
        self,
    ) -> Union[Type[Exception], tuple[Type[Exception], ...]]:  # pragma: no cover
        return self.bridge.base_exceptions

    async def incr(
        self, key: str, expiry: int, elastic_expiry: bool = False, amount: int = 1
    ) -> int:
        """
        increments the counter for a given rate limit key

        :param key: the key to increment
        :param expiry: amount in seconds for the key to expire in
        :param amount: the number to increment by
        """

        return await self.bridge.incr(key, expiry, elastic_expiry, amount)

    async def get(self, key: str) -> int:
        """
        :param key: the key to get the counter value for
        """

        return await self.bridge.get(key)

    async def clear(self, key: str) -> None:
        """
        :param key: the key to clear rate limits for
        """

        return await self.bridge.clear(key)

    async def acquire_entry(
        self, key: str, limit: int, expiry: int, amount: int = 1
    ) -> bool:
        """
        :param key: rate limit key to acquire an entry in
        :param limit: amount of entries allowed
        :param expiry: expiry of the entry
        :param amount: the number of entries to acquire
        """

        return await self.bridge.acquire_entry(key, limit, expiry, amount)

    async def get_moving_window(
        self, key: str, limit: int, expiry: int
    ) -> tuple[float, int]:
        """
        returns the starting point and the number of entries in the moving
        window

        :param key: rate limit key
        :param expiry: expiry of entry
        :return: (previous count, previous TTL, current count, current TTL)
        """
        return await self.bridge.get_moving_window(key, limit, expiry)

    async def acquire_sliding_window_entry(
        self,
        key: str,
        limit: int,
        expiry: int,
        amount: int = 1,
    ) -> bool:
        current_key = self._current_window_key(key)
        previous_key = self._previous_window_key(key)
        return await self.bridge.acquire_sliding_window_entry(
            previous_key, current_key, limit, expiry, amount
        )

    async def get_sliding_window(
        self, key: str, expiry: int
    ) -> tuple[int, float, int, float]:
        previous_key = self._previous_window_key(key)
        current_key = self._current_window_key(key)
        return await self.bridge.get_sliding_window(previous_key, current_key, expiry)

    async def get_expiry(self, key: str) -> float:
        """
        :param key: the key to get the expiry for
        """

        return await self.bridge.get_expiry(key)

    async def check(self) -> bool:
        """
        Check if storage is healthy by calling ``PING``
        """

        return await self.bridge.check()

    async def reset(self) -> Optional[int]:
        """
        This function calls a Lua Script to delete keys prefixed with
        ``self.PREFIX`` in blocks of 5000.

        .. warning:: This operation was designed to be fast, but was not tested
           on a large production based system. Be careful with its usage as it
           could be slow on very large data sets.
        """

        return await self.bridge.lua_reset()


@versionadded(version="2.1")
@versionchanged(
    version="4.2",
    reason="Added support for using the asyncio redis client from :pypi:`redis` ",
)
class RedisClusterStorage(RedisStorage):
    """
    Rate limit storage with redis cluster as backend

    Depends on :pypi:`coredis` or :pypi:`redis`
    """

    STORAGE_SCHEME = ["async+redis+cluster"]
    """
    The storage schemes for redis cluster to be used in an async context
    """

    MODE = "CLUSTER"

    def __init__(
        self,
        uri: str,
        wrap_exceptions: bool = False,
        implementation: Literal["redispy", "coredis"] = "coredis",
        **options: Union[float, str, bool],
    ) -> None:
        """
        :param uri: url of the form
         ``async+redis+cluster://[:password]@host:port,host:port``
        :param wrap_exceptions: Whether to wrap storage exceptions in
         :exc:`limits.errors.StorageError` before raising it.
        :param implementation: Whether to use the client implementation from
         :class:`coredis.RedisCluster` (``coredis``) or :class:`redis.asyncio.cluster.RedisCluster` (``redispy``).
        :param options: all remaining keyword arguments are passed
         directly to the constructor of :class:`coredis.RedisCluster` or
         :class:`redis.asyncio.RedisCluster`
        :raise ConfigurationError: when the redis library is not
         available or if the redis host cannot be pinged.
        """
        super().__init__(
            uri,
            wrap_exceptions=wrap_exceptions,
            implementation=implementation,
            **options,
        )

    def configure_bridge(self) -> None:
        self.bridge.use_cluster(**self.options)

    async def reset(self) -> Optional[int]:
        """
        Redis Clusters are sharded and deleting across shards
        can't be done atomically. Because of this, this reset loops over all
        keys that are prefixed with ``self.PREFIX`` and calls delete on them,
        one at a time.

        .. warning:: This operation was not tested with extremely large data sets.
           On a large production based system, care should be taken with its
           usage as it could be slow on very large data sets
        """

        return await self.bridge.reset()


@versionadded(version="2.1")
@versionchanged(
    version="4.2",
    reason="Added support for using the asyncio redis client from :pypi:`redis` ",
)
class RedisSentinelStorage(RedisStorage):
    """
    Rate limit storage with redis sentinel as backend

    Depends on :pypi:`coredis` or :pypi:`redis`
    """

    STORAGE_SCHEME = ["async+redis+sentinel"]
    """The storage scheme for redis accessed via a redis sentinel installation"""

    MODE = "SENTINEL"

    DEPENDENCIES = {
        "redis": Version("5.2.0"),
        "coredis": Version("3.4.0"),
        "coredis.sentinel": Version("3.4.0"),
    }

    def __init__(
        self,
        uri: str,
        wrap_exceptions: bool = False,
        implementation: Literal["redispy", "coredis"] = "coredis",
        service_name: Optional[str] = None,
        use_replicas: bool = True,
        sentinel_kwargs: Optional[dict[str, Union[float, str, bool]]] = None,
        **options: Union[float, str, bool],
    ):
        """
        :param uri: url of the form
         ``async+redis+sentinel://host:port,host:port/service_name``
        :param wrap_exceptions: Whether to wrap storage exceptions in
         :exc:`limits.errors.StorageError` before raising it.
        :param implementation: Whether to use the client implementation from
         :class:`coredis.sentinel.Sentinel` (``coredis``) or
         :class:`redis.asyncio.sentinel.Sentinel` (``redispy``)
        :param service_name: sentinel service name (if not provided in `uri`)
        :param use_replicas: Whether to use replicas for read only operations
        :param sentinel_kwargs: optional arguments to pass as
         `sentinel_kwargs`` to :class:`coredis.sentinel.Sentinel` or
         :class:`redis.asyncio.Sentinel`
        :param options: all remaining keyword arguments are passed
         directly to the constructor of :class:`coredis.sentinel.Sentinel` or
         :class:`redis.asyncio.sentinel.Sentinel`
        :raise ConfigurationError: when the redis library is not available
         or if the redis primary host cannot be pinged.
        """

        self.service_name = service_name
        self.use_replicas = use_replicas
        self.sentinel_kwargs = sentinel_kwargs
        super().__init__(
            uri,
            wrap_exceptions=wrap_exceptions,
            implementation=implementation,
            **options,
        )

    def configure_bridge(self) -> None:
        self.bridge.use_sentinel(
            self.service_name, self.use_replicas, self.sentinel_kwargs, **self.options
        )
