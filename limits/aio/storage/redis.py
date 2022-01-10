import time
import urllib
from typing import Any, Dict, Optional

from limits.errors import ConfigurationError
from limits.util import get_package_data

from .base import MovingWindowSupport, Storage


class RedisInteractor:
    RES_DIR = "resources/redis/lua_scripts"

    SCRIPT_MOVING_WINDOW = get_package_data(f"{RES_DIR}/moving_window.lua")
    SCRIPT_ACQUIRE_MOVING_WINDOW = get_package_data(
        f"{RES_DIR}/acquire_moving_window.lua"
    )
    SCRIPT_CLEAR_KEYS = get_package_data(f"{RES_DIR}/clear_keys.lua")
    SCRIPT_INCR_EXPIRE = get_package_data(f"{RES_DIR}/incr_expire.lua")

    lua_moving_window: Any
    lua_acquire_window: Any

    async def _incr(
        self,
        key: str,
        expiry: int,
        connection,
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
        value = await connection.incrby(key, amount)

        if elastic_expiry or value == amount:
            await connection.expire(key, expiry)

        return value

    async def _get(self, key: str, connection) -> int:
        """
        :param connection: Redis connection
        :param key: the key to get the counter value for
        """

        return int(await connection.get(key) or 0)

    async def _clear(self, key: str, connection) -> None:
        """
        :param key: the key to clear rate limits for
        :param connection: Redis connection
        """
        await connection.delete(key)

    async def get_moving_window(self, key, limit, expiry):
        """
        returns the starting point and the number of entries in the moving
        window

        :param key: rate limit key
        :param expiry: expiry of entry
        :return: (start of window, number of acquired entries)
        """
        timestamp = int(time.time())
        window = await self.lua_moving_window.execute(
            [key], [int(timestamp - expiry), limit]
        )

        return window or (timestamp, 0)

    async def _acquire_entry(
        self, key: str, limit: int, expiry: int, connection, amount: int = 1
    ) -> bool:
        """
        :param key: rate limit key to acquire an entry in
        :param limit: amount of entries allowed
        :param expiry: expiry of the entry
        :param connection: Redis connection
        """
        timestamp = time.time()
        acquired = await self.lua_acquire_window.execute(
            [key], [timestamp, limit, expiry, amount]
        )

        return bool(acquired)

    async def _get_expiry(self, key, connection=None):
        """
        :param key: the key to get the expiry for
        :param connection: Redis connection
        """

        return int(max(await connection.ttl(key), 0) + time.time())

    async def _check(self, connection) -> bool:
        """
        check if storage is healthy

        :param connection: Redis connection
        """
        try:
            await connection.ping()

            return True
        except:  # noqa
            return False


class RedisStorage(RedisInteractor, Storage, MovingWindowSupport):
    """
    Rate limit storage with redis as backend.

    Depends on :pypi:`coredis`

    .. warning:: This is a beta feature
    .. versionadded:: 2.1
    """

    STORAGE_SCHEME = ["async+redis", "async+rediss", "async+redis+unix"]
    """
    The storage schemes for redis to be used in an async context
    """
    DEPENDENCIES = ["coredis"]

    def __init__(self, uri: str, **options) -> None:
        """
        :param uri: uri of the form `async+redis://[:password]@host:port`,
         `async+redis://[:password]@host:port/db`,
         `async+rediss://[:password]@host:port`, `async+unix:///path/to/sock` etc.
         This uri is passed directly to :func:`coredis.StrictRedis.from_url` with
         the initial `a` removed, except for the case of `redis+unix` where it
         is replaced with `unix`.
        :param options: all remaining keyword arguments are passed
         directly to the constructor of :class:`coredis.StrictRedis`
        :raise ConfigurationError: when the redis library is not available
        """

        uri = uri.replace("async+redis", "redis", 1)
        uri = uri.replace("redis+unix", "unix")

        super().__init__()

        self.dependency = self.dependencies["coredis"]
        self.storage = self.dependency.StrictRedis.from_url(uri, **options)

        self.initialize_storage(uri)

    def initialize_storage(self, _uri: str) -> None:
        # all these methods are coroutines, so must be called with await
        self.lua_moving_window = self.storage.register_script(self.SCRIPT_MOVING_WINDOW)
        self.lua_acquire_window = self.storage.register_script(
            self.SCRIPT_ACQUIRE_MOVING_WINDOW
        )
        self.lua_clear_keys = self.storage.register_script(self.SCRIPT_CLEAR_KEYS)
        self.lua_incr_expire = self.storage.register_script(
            RedisStorage.SCRIPT_INCR_EXPIRE
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
            return await self.lua_incr_expire.execute([key], [expiry, amount])

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

    async def acquire_entry(self, key, limit, expiry, amount: int = 1) -> bool:
        """
        :param key: rate limit key to acquire an entry in
        :param limit: amount of entries allowed
        :param expiry: expiry of the entry
        :param amount: the number of entries to acquire
        """

        return await super()._acquire_entry(key, limit, expiry, self.storage, amount)

    async def get_expiry(self, key: str) -> int:
        """
        :param key: the key to get the expiry for
        """

        return await super()._get_expiry(key, self.storage)

    async def check(self) -> bool:
        """
        Check if storage is healthy by calling :meth:`coredis.StrictRedis.ping`
        """

        return await super()._check(self.storage)

    async def reset(self) -> Optional[int]:
        """
        This function calls a Lua Script to delete keys prefixed with 'LIMITER'
        in block of 5000.

        .. warning::
           This operation was designed to be fast, but was not tested
           on a large production based system. Be careful with its usage as it
           could be slow on very large data sets.

        """

        cleared = await self.lua_clear_keys.execute(["LIMITER*"])

        return cleared


class RedisClusterStorage(RedisStorage):
    """
    Rate limit storage with redis cluster as backend

    Depends on :pypi:`coredis`

    .. warning:: This is a beta feature
    .. versionadded:: 2.1
    """

    STORAGE_SCHEME = ["async+redis+cluster"]
    """
    The storage schemes for redis cluster to be used in an async context
    """

    DEFAULT_OPTIONS = {
        "max_connections": 1000,
    }
    "Default options passed to :class:`coredis.StrictRedisCluster`"

    def __init__(self, uri: str, **options):
        """
        :param uri: url of the form
         `async+redis+cluster://[:password]@host:port,host:port`
        :param options: all remaining keyword arguments are passed
         directly to the constructor of :class:`coredis.StrictRedisCluster`
        :raise ConfigurationError: when the coredis library is not
         available or if the redis host cannot be pinged.
        """
        parsed = urllib.parse.urlparse(uri)
        cluster_hosts = []

        for loc in parsed.netloc.split(","):
            host, port = loc.split(":")
            cluster_hosts.append({"host": host, "port": int(port)})

        super(RedisStorage, self).__init__()
        self.dependency = self.dependencies["coredis"]
        self.storage = self.dependency.StrictRedisCluster(
            startup_nodes=cluster_hosts, **{**self.DEFAULT_OPTIONS, **options}
        )
        self.initialize_storage(uri)

    async def reset(self):
        """
        Redis Clusters are sharded and deleting across shards
        can't be done atomically. Because of this, this reset loops over all
        keys that are prefixed with 'LIMITER' and calls delete on them, one at
        a time.

        .. warning::
         This operation was not tested with extremely large data sets.
         On a large production based system, care should be taken with its
         usage as it could be slow on very large data sets"""

        keys = await self.storage.keys("LIMITER*")

        return sum([await self.storage.delete(k.decode("utf-8")) for k in keys])


class RedisSentinelStorage(RedisStorage):
    """
    Rate limit storage with redis sentinel as backend

    Depends on :pypi:`coredis`

    .. warning:: This is a beta feature
    .. versionadded:: 2.1
    """

    STORAGE_SCHEME = ["async+redis+sentinel"]
    """The storage scheme for redis accessed via a redis sentinel installation"""

    DEFAULT_OPTIONS = {
        "stream_timeout": 0.2,
    }
    "Default options passed to :class:`~coredis.sentinel.Sentinel`"

    DEPENDENCIES = ["coredis.sentinel"]

    def __init__(
        self,
        uri: str,
        service_name: str = None,
        sentinel_kwargs: Optional[Dict[str, Any]] = None,
        **options,
    ):
        """
        :param uri: url of the form
         `async+redis+sentinel://host:port,host:port/service_name`
        :param service_name, optional: sentinel service name
         (if not provided in `uri`)
        :param sentinel_kwargs, optional: kwargs to pass as
         ``sentinel_kwargs`` to :class:`coredis.sentinel.Sentinel`
        :param options: all remaining keyword arguments are passed
         directly to the constructor of :class:`coredis.sentinel.Sentinel`
        :raise ConfigurationError: when the coredis library is not available
         or if the redis master host cannot be pinged.
        """

        parsed = urllib.parse.urlparse(uri)
        sentinel_configuration = []
        connection_options = options.copy()
        sentinel_options = sentinel_kwargs.copy() if sentinel_kwargs else {}

        if parsed.username:
            sentinel_options["username"] = parsed.username

        if parsed.password:
            sentinel_options["password"] = parsed.password

        sep = parsed.netloc.find("@") + 1

        for loc in parsed.netloc[sep:].split(","):
            host, port = loc.split(":")
            sentinel_configuration.append((host, int(port)))
        self.service_name = (
            parsed.path.replace("/", "") if parsed.path else service_name
        )

        if self.service_name is None:
            raise ConfigurationError("'service_name' not provided")

        connection_options.setdefault("stream_timeout", 0.2)

        super(RedisStorage, self).__init__()

        self.dependency = self.dependencies["coredis.sentinel"]

        self.sentinel = self.dependency.Sentinel(
            sentinel_configuration,
            sentinel_kwargs=sentinel_options,
            **connection_options,
        )
        self.storage = self.sentinel.master_for(self.service_name)
        self.storage_slave = self.sentinel.slave_for(self.service_name)
        self.initialize_storage(uri)

    async def get(self, key: str) -> int:
        """
        :param key: the key to get the counter value for
        """

        return await super()._get(key, self.storage_slave)

    async def get_expiry(self, key: str) -> int:
        """
        :param key: the key to get the expiry for
        """

        return await super()._get_expiry(key, self.storage_slave)

    async def check(self) -> bool:
        """
        Check if storage is healthy by calling :meth:`coredis.StrictRedis.ping`
        on the slave.
        """

        return await super()._check(self.storage_slave)
