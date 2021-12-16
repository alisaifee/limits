import time

from typing import Any
from typing import Optional

from limits.util import get_dependency
from limits.errors import ConfigurationError
from .base import Storage
from .base import MovingWindowSupport


class RedisInteractor:
    SCRIPT_MOVING_WINDOW = """
        local items = redis.call('lrange', KEYS[1], 0, tonumber(ARGV[2]))
        local expiry = tonumber(ARGV[1])
        local a = 0
        local oldest = nil

        for idx=1,#items do
            if tonumber(items[idx]) >= expiry then
                a = a + 1

                if oldest == nil then
                    oldest = tonumber(items[idx])
                end
            else
                break
            end
        end

        return {oldest, a}
        """

    SCRIPT_ACQUIRE_MOVING_WINDOW = """
        local entry = redis.call('lindex', KEYS[1], tonumber(ARGV[2]) - 1)
        local timestamp = tonumber(ARGV[1])
        local expiry = tonumber(ARGV[3])

        if entry and tonumber(entry) >= timestamp - expiry then
            return false
        end
        local limit = tonumber(ARGV[2])
        local no_add = tonumber(ARGV[4])

        if 0 == no_add then
            redis.call('lpush', KEYS[1], timestamp)
            redis.call('ltrim', KEYS[1], 0, limit - 1)
            redis.call('expire', KEYS[1], expiry)
        end

        return true
        """

    SCRIPT_CLEAR_KEYS = """
        local keys = redis.call('keys', KEYS[1])
        local res = 0

        for i=1,#keys,5000 do
            res = res + redis.call(
                'del', unpack(keys, i, math.min(i+4999, #keys))
            )
        end

        return res
        """

    SCRIPT_INCR_EXPIRE = """
        local current
        current = redis.call("incr",KEYS[1])

        if tonumber(current) == 1 then
            redis.call("expire",KEYS[1],ARGV[1])
        end

        return current
    """

    lua_moving_window: Any
    lua_acquire_window: Any

    async def _incr(
        self, key: str, expiry: int, connection, elastic_expiry: bool = False
    ) -> int:
        """
        increments the counter for a given rate limit key

        :param connection: Redis connection
        :param key: the key to increment
        :param expiry: amount in seconds for the key to expire in
        """
        value = await connection.incr(key)
        if elastic_expiry or value == 1:
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
        timestamp = time.time()
        window = await self.lua_moving_window.execute(
            [key], [int(timestamp - expiry), limit]
        )
        return window or (timestamp, 0)

    async def _acquire_entry(
        self, key: str, limit: int, expiry: int, connection, no_add=False
    ) -> bool:
        """
        :param key: rate limit key to acquire an entry in
        :param limit: amount of entries allowed
        :param expiry: expiry of the entry
        :param no_add: if False an entry is not actually acquired but
         instead serves as a 'check'
        :param connection: Redis connection
        """
        timestamp = time.time()
        acquired = await self.lua_acquire_window.execute(
            [key], [timestamp, limit, expiry, int(no_add)]
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
        :param connection: Redis connection
        check if storage is healthy
        """
        try:
            return connection.ping()
        except:  # noqa
            return False


class RedisStorage(RedisInteractor, Storage, MovingWindowSupport):
    """
    Rate limit storage with redis as backend.

    Depends on the :mod:`aredis` package.

    .. danger:: Experimental
    .. versionadded:: 2.1
    """

    STORAGE_SCHEME = ["async+redis", "async+rediss", "async+redis+unix"]

    def __init__(self, uri: str, **options) -> None:
        """
        :param uri: uri of the form `async+redis://[:password]@host:port`,
         `async+redis://[:password]@host:port/db`,
         `async+rediss://[:password]@host:port`, `async+unix:///path/to/sock` etc.
         This uri is passed directly to :func:`aredis.StrictRedis.from_url` with
         the initial `a` removed, except for the case of `redis+unix` where it
         is replaced with `unix`.
        :param options: all remaining keyword arguments are passed
         directly to the constructor of :class:`redis.Redis`
        :raise ConfigurationError: when the redis library is not available
        """
        if not get_dependency("aredis"):
            raise ConfigurationError(
                "aredis prerequisite not available"
            )  # pragma: no cover

        uri = uri.replace("async+redis", "redis", 1)
        uri = uri.replace("redis+unix", "unix")

        self.storage = get_dependency("aredis").StrictRedis.from_url(uri, **options)
        self.initialize_storage(uri)
        super(RedisStorage, self).__init__()

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

    async def incr(self, key: str, expiry: int, elastic_expiry: bool = False) -> int:
        """
        increments the counter for a given rate limit key

        :param key: the key to increment
        :param expiry: amount in seconds for the key to expire in
        """
        if elastic_expiry:
            return await super(RedisStorage, self)._incr(
                key, expiry, self.storage, elastic_expiry
            )
        else:
            return await self.lua_incr_expire.execute([key], [expiry])

    async def get(self, key: str) -> int:
        """
        :param key: the key to get the counter value for
        """
        return await super(RedisStorage, self)._get(key, self.storage)

    async def clear(self, key: str) -> None:
        """
        :param key: the key to clear rate limits for
        """
        return await super(RedisStorage, self)._clear(key, self.storage)

    async def acquire_entry(self, key, limit, expiry, no_add=False) -> bool:
        """
        :param key: rate limit key to acquire an entry in
        :param limit: amount of entries allowed
        :param expiry: expiry of the entry
        :param no_add: if False an entry is not actually acquired but
         instead serves as a 'check'
        """
        return await super(RedisStorage, self)._acquire_entry(
            key, limit, expiry, self.storage, no_add=no_add
        )

    async def get_expiry(self, key: str) -> int:
        """
        :param key: the key to get the expiry for
        """
        return await super(RedisStorage, self)._get_expiry(key, self.storage)

    async def check(self) -> bool:
        """
        check if storage is healthy
        """
        return await super(RedisStorage, self)._check(self.storage)

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
