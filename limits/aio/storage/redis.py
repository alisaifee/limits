import time
import urllib
from types import ModuleType
from typing import TYPE_CHECKING, cast

import redis.asyncio.cluster
from deprecated.sphinx import versionadded
from packaging.version import Version

from limits.aio.storage.base import (
    MovingWindowSupport,
    SlidingWindowCounterSupport,
    Storage,
)
from limits.errors import ConfigurationError
from limits.typing import AsyncRedisClient, Optional, Type, Union
from limits.util import get_package_data

if TYPE_CHECKING:
    import redis
    import redis.asyncio.connection
    import redis.commands.core


class RedisInteractor:
    RES_DIR = "resources/redis/lua_scripts"

    SCRIPT_MOVING_WINDOW = get_package_data(f"{RES_DIR}/moving_window.lua")
    SCRIPT_ACQUIRE_MOVING_WINDOW = get_package_data(
        f"{RES_DIR}/acquire_moving_window.lua"
    )
    SCRIPT_CLEAR_KEYS = get_package_data(f"{RES_DIR}/clear_keys.lua")
    SCRIPT_INCR_EXPIRE = get_package_data(f"{RES_DIR}/incr_expire.lua")
    SCRIPT_SLIDING_WINDOW = get_package_data(f"{RES_DIR}/sliding_window.lua")
    SCRIPT_ACQUIRE_SLIDING_WINDOW = get_package_data(
        f"{RES_DIR}/acquire_sliding_window.lua"
    )

    lua_moving_window: redis.commands.core.Script
    lua_acquire_moving_window: redis.commands.core.Script
    lua_sliding_window: redis.commands.core.Script
    lua_acquire_sliding_window: redis.commands.core.Script
    lua_clear_keys: redis.commands.core.Script
    lua_incr_expire: redis.commands.core.Script

    PREFIX = "LIMITS"

    def prefixed_key(self, key: str) -> str:
        return f"{self.PREFIX}:{key}"

    async def _incr(
        self,
        key: str,
        expiry: int,
        connection: AsyncRedisClient,
        elastic_expiry: bool = False,
        amount: int = 1,
    ) -> int:
        """
        increments the counter for a given rate limit key

        :param connection: Redis connection
        :param key: the key to increment
        :param expiry: amount in seconds for the key to expire in
        :param amount: the number to increment by
        """
        key = self.prefixed_key(key)
        value: int = await connection.execute_command("INCRBY", key, amount)

        if elastic_expiry or value == amount:
            await connection.execute_command("EXPIRE", key, expiry)

        return value

    async def _get(self, key: str, connection: AsyncRedisClient) -> int:
        """
        :param connection: Redis connection
        :param key: the key to get the counter value for
        """

        key = self.prefixed_key(key)
        return int(await connection.execute_command("GET", key) or 0)

    async def _clear(self, key: str, connection: AsyncRedisClient) -> None:
        """
        :param key: the key to clear rate limits for
        :param connection: Redis connection
        """
        key = self.prefixed_key(key)
        await connection.execute_command("DEL", key)

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
        key = self.prefixed_key(key)
        timestamp = time.time()
        window = await self.lua_moving_window([key], [timestamp - expiry, limit])
        if window:
            return float(window[0]), window[1]
        return timestamp, 0

    async def get_sliding_window(
        self, key: str, expiry: int
    ) -> tuple[int, float, int, float]:
        previous_key = self.prefixed_key(self._previous_window_key(key))
        current_key = self.prefixed_key(self._current_window_key(key))

        if window := await self.lua_sliding_window(
            [previous_key, current_key], [expiry]
        ):
            return (
                int(window[0] or 0),
                max(0, float(window[1] or 0)) / 1000,
                int(window[2] or 0),
                max(0, float(window[3] or 0)) / 1000,
            )
        return 0, 0.0, 0, 0.0

    async def _acquire_entry(
        self,
        key: str,
        limit: int,
        expiry: int,
        connection: AsyncRedisClient,
        amount: int = 1,
    ) -> bool:
        """
        :param key: rate limit key to acquire an entry in
        :param limit: amount of entries allowed
        :param expiry: expiry of the entry
        :param connection: Redis connection
        """
        key = self.prefixed_key(key)
        timestamp = time.time()
        acquired = await self.lua_acquire_moving_window(
            [key], [timestamp, limit, expiry, amount]
        )

        return bool(acquired)

    async def _acquire_sliding_window_entry(
        self,
        previous_key: str,
        current_key: str,
        limit: int,
        expiry: int,
        amount: int = 1,
    ) -> bool:
        previous_key = self.prefixed_key(previous_key)
        current_key = self.prefixed_key(current_key)
        acquired = await self.lua_acquire_sliding_window(
            [previous_key, current_key], [limit, expiry, amount]
        )
        return bool(acquired)

    async def _get_expiry(self, key: str, connection: AsyncRedisClient) -> float:
        """
        :param key: the key to get the expiry for
        :param connection: Redis connection
        """

        key = self.prefixed_key(key)
        ttl: int = await connection.execute_command("TTL", key)
        return max(ttl, 0) + time.time()

    async def _check(self, connection: AsyncRedisClient) -> bool:
        """
        check if storage is healthy

        :param connection: Redis connection
        """
        try:
            await connection.execute_command("PING")

            return True
        except:  # noqa
            return False

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


@versionadded(version="2.1")
class RedisStorage(
    RedisInteractor, Storage, MovingWindowSupport, SlidingWindowCounterSupport
):
    """
    Rate limit storage with redis as backend.

    Depends on :pypi:`redis`
    """

    STORAGE_SCHEME = ["async+redis", "async+rediss", "async+redis+unix"]
    """
    The storage schemes for redis to be used in an async context
    """
    DEPENDENCIES = {"redis": Version("4.2.0")}

    def __init__(
        self,
        uri: str,
        connection_pool: Optional[redis.asyncio.connection.ConnectionPool] = None,  # type: ignore
        wrap_exceptions: bool = False,
        **options: Union[float, str, bool],
    ) -> None:
        """
        :param uri: uri of the form:

         - ``async+redis://[:password]@host:port``
         - ``async+redis://[:password]@host:port/db``
         - ``async+rediss://[:password]@host:port``
         - ``async+redis+unix:///path/to/sock?db=0`` etc...

         This uri is passed directly to :meth:`redis.asyncio.Redis.from_url` with
         the initial ``async`` removed, except for the case of ``async+redis+unix``
         where it is replaced with ``unix``.
        :param connection_pool: if provided, the redis client is initialized with
         the connection pool and any other params passed as :paramref:`options`
        :param wrap_exceptions: Whether to wrap storage exceptions in
         :exc:`limits.errors.StorageError` before raising it.
        :param options: all remaining keyword arguments are passed
         directly to the constructor of :class:`redis.asyncio.Redis`
        :raise ConfigurationError: when the redis library is not available
        """
        uri = uri.replace("async+redis", "redis", 1)
        uri = uri.replace("redis+unix", "unix")

        super().__init__(uri, wrap_exceptions=wrap_exceptions, **options)

        self.dependency: ModuleType = self.dependencies["redis"].module

        if connection_pool:
            self.storage = self.dependency.asyncio.Redis(
                connection_pool=connection_pool, **options
            )
        else:
            self.storage = self.dependency.asyncio.Redis.from_url(uri, **options)

        self.initialize_storage(uri)

    @property
    def base_exceptions(
        self,
    ) -> Union[Type[Exception], tuple[Type[Exception], ...]]:  # pragma: no cover
        return self.dependency.RedisError  # type: ignore[no-any-return]

    def initialize_storage(self, _uri: str) -> None:
        # Redis-py uses a slightly different script registration
        self.lua_moving_window = self.storage.register_script(self.SCRIPT_MOVING_WINDOW)
        self.lua_acquire_moving_window = self.storage.register_script(
            self.SCRIPT_ACQUIRE_MOVING_WINDOW
        )
        self.lua_clear_keys = self.storage.register_script(self.SCRIPT_CLEAR_KEYS)
        self.lua_incr_expire = self.storage.register_script(self.SCRIPT_INCR_EXPIRE)
        self.lua_sliding_window = self.storage.register_script(
            self.SCRIPT_SLIDING_WINDOW
        )
        self.lua_acquire_sliding_window = self.storage.register_script(
            self.SCRIPT_ACQUIRE_SLIDING_WINDOW
        )

    async def incr(
        self, key: str, expiry: int, elastic_expiry: bool = False, amount: int = 1
    ) -> int:
        """
        increments the counter for a given rate limit key

        :param key: the key to increment
        :param expiry: amount in seconds for the key to expire in
        :param amount: the number to increment by
        """

        if elastic_expiry:
            return await super()._incr(
                key, expiry, self.storage, elastic_expiry, amount
            )
        else:
            key = self.prefixed_key(key)
            return cast(int, await self.lua_incr_expire([key], [expiry, amount]))

    async def get(self, key: str) -> int:
        """
        :param key: the key to get the counter value for
        """

        return await super()._get(key, self.storage)

    async def clear(self, key: str) -> None:
        """
        :param key: the key to clear rate limits for
        """

        return await super()._clear(key, self.storage)

    async def acquire_entry(
        self, key: str, limit: int, expiry: int, amount: int = 1
    ) -> bool:
        """
        :param key: rate limit key to acquire an entry in
        :param limit: amount of entries allowed
        :param expiry: expiry of the entry
        :param amount: the number of entries to acquire
        """

        return await super()._acquire_entry(key, limit, expiry, self.storage, amount)

    async def acquire_sliding_window_entry(
        self,
        key: str,
        limit: int,
        expiry: int,
        amount: int = 1,
    ) -> bool:
        current_key = self._current_window_key(key)
        previous_key = self._previous_window_key(key)
        return await super()._acquire_sliding_window_entry(
            previous_key, current_key, limit, expiry, amount
        )

    async def get_expiry(self, key: str) -> float:
        """
        :param key: the key to get the expiry for
        """

        return await super()._get_expiry(key, self.storage)

    async def check(self) -> bool:
        """
        Check if storage is healthy by calling :meth:`redis.asyncio.Redis.ping`
        """

        return await super()._check(self.storage)

    async def reset(self) -> Optional[int]:
        """
        This function calls a Lua Script to delete keys prefixed with
        ``self.PREFIX`` in blocks of 5000.

        .. warning:: This operation was designed to be fast, but was not tested
           on a large production based system. Be careful with its usage as it
           could be slow on very large data sets.
        """

        prefix = self.prefixed_key("*")
        return cast(int, await self.lua_clear_keys([prefix]))


@versionadded(version="2.1")
class RedisClusterStorage(RedisStorage):
    """
    Rate limit storage with redis cluster as backend

    Depends on :pypi:`redis`
    """

    STORAGE_SCHEME = ["async+redis+cluster"]
    """
    The storage schemes for redis cluster to be used in an async context
    """

    DEFAULT_OPTIONS: dict[str, Union[float, str, bool]] = {
        "max_connections": 1000,
    }
    "Default options passed to :class:`redis.asyncio.RedisCluster`"

    def __init__(
        self,
        uri: str,
        wrap_exceptions: bool = False,
        **options: Union[float, str, bool],
    ) -> None:
        """
        :param uri: url of the form
         ``async+redis+cluster://[:password]@host:port,host:port``
        :param options: all remaining keyword arguments are passed
         directly to the constructor of :class:`redis.asyncio.RedisCluster`
        :raise ConfigurationError: when the redis library is not
         available or if the redis host cannot be pinged.
        """
        parsed = urllib.parse.urlparse(uri)
        parsed_auth: dict[str, Union[float, str, bool]] = {}

        if parsed.username:
            parsed_auth["username"] = parsed.username
        if parsed.password:
            parsed_auth["password"] = parsed.password

        sep = parsed.netloc.find("@") + 1
        cluster_hosts = []

        super(RedisStorage, self).__init__(
            uri, wrap_exceptions=wrap_exceptions, **options
        )

        self.dependency: ModuleType = self.dependencies["redis"].module

        for loc in parsed.netloc[sep:].split(","):
            host, port = loc.split(":")
            # Create a dict with host and port keys as expected by RedisCluster
            cluster_hosts.append(
                self.dependency.asyncio.cluster.ClusterNode(host=host, port=int(port))
            )

        self.storage = self.dependency.asyncio.RedisCluster(
            startup_nodes=cluster_hosts,
            **{**self.DEFAULT_OPTIONS, **parsed_auth, **options},
        )
        self.initialize_storage(uri)

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

        prefix = self.prefixed_key("*")
        keys = await self.storage.keys(
            prefix, target_nodes=self.dependency.asyncio.cluster.RedisCluster.ALL_NODES
        )
        count = 0
        for key in keys:
            count += await self.storage.delete(key)
        return count


@versionadded(version="2.1")
class RedisSentinelStorage(RedisStorage):
    """
    Rate limit storage with redis sentinel as backend

    Depends on :pypi:`redis`
    """

    STORAGE_SCHEME = ["async+redis+sentinel"]
    """The storage scheme for redis accessed via a redis sentinel installation"""

    DEPENDENCIES = {"redis": Version("4.2.0")}

    def __init__(
        self,
        uri: str,
        service_name: Optional[str] = None,
        use_replicas: bool = True,
        sentinel_kwargs: Optional[dict[str, Union[float, str, bool]]] = None,
        **options: Union[float, str, bool],
    ):
        """
        :param uri: url of the form
         ``async+redis+sentinel://host:port,host:port/service_name``
        :param service_name, optional: sentinel service name
         (if not provided in `uri`)
        :param use_replicas: Whether to use replicas for read only operations
        :param sentinel_kwargs, optional: kwargs to pass as
         ``sentinel_kwargs`` to :class:`redis.asyncio.Sentinel`
        :param options: all remaining keyword arguments are passed
         directly to the constructor of :class:`redis.asyncio.Sentinel`
        :raise ConfigurationError: when the redis library is not available
         or if the redis primary host cannot be pinged.
        """

        parsed = urllib.parse.urlparse(uri)
        sentinel_configuration = []
        connection_options = options.copy()
        sentinel_options = sentinel_kwargs.copy() if sentinel_kwargs else {}
        parsed_auth: dict[str, Union[float, str, bool]] = {}

        if parsed.username:
            parsed_auth["username"] = parsed.username

        if parsed.password:
            parsed_auth["password"] = parsed.password

        sep = parsed.netloc.find("@") + 1

        for loc in parsed.netloc[sep:].split(","):
            host, port = loc.split(":")
            sentinel_configuration.append((host, int(port)))
        self.service_name = (
            parsed.path.replace("/", "") if parsed.path else service_name
        )

        if self.service_name is None:
            raise ConfigurationError("'service_name' not provided")

        super(RedisStorage, self).__init__()

        self.dependency = self.dependencies["redis"].module

        self.sentinel = self.dependency.asyncio.Sentinel(
            sentinel_configuration,
            sentinel_kwargs={**parsed_auth, **sentinel_options},
            **{**parsed_auth, **connection_options},
        )
        self.storage = self.sentinel.master_for(self.service_name)
        self.storage_replica = self.sentinel.slave_for(self.service_name)
        self.use_replicas = use_replicas
        self.initialize_storage(uri)

    async def get(self, key: str) -> int:
        """
        :param key: the key to get the counter value for
        """

        return await super()._get(
            key, self.storage_replica if self.use_replicas else self.storage
        )

    async def get_expiry(self, key: str) -> float:
        """
        :param key: the key to get the expiry for
        """

        return await super()._get_expiry(
            key, self.storage_replica if self.use_replicas else self.storage
        )

    async def check(self) -> bool:
        """
        Check if storage is healthy by calling :meth:`redis.asyncio.Redis.ping`
        on the replica.
        """

        return await super()._check(
            self.storage_replica if self.use_replicas else self.storage
        )
