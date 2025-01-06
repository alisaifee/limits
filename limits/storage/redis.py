from __future__ import annotations

import time
from typing import TYPE_CHECKING

from packaging.version import Version

from limits.typing import Optional, RedisClient, ScriptP, Tuple, Type, Union

from ..util import get_package_data
from .base import MovingWindowSupport, SlidingWindowCounterSupport, Storage

if TYPE_CHECKING:
    import redis


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

    lua_moving_window: ScriptP[Tuple[int, int]]
    lua_acquire_moving_window: ScriptP[bool]
    lua_sliding_window: ScriptP[Tuple[int, float, int, float]]
    lua_acquire_sliding_window: ScriptP[bool]

    PREFIX = "LIMITS"

    def prefixed_key(self, key: str) -> str:
        return f"{self.PREFIX}:{key}"

    def get_moving_window(self, key: str, limit: int, expiry: int) -> Tuple[float, int]:
        """
        returns the starting point and the number of entries in the moving
        window

        :param key: rate limit key
        :param expiry: expiry of entry
        :return: (start of window, number of acquired entries)
        """
        key = self.prefixed_key(key)
        timestamp = time.time()
        if window := self.lua_moving_window([key], [timestamp - expiry, limit]):
            return float(window[0]), window[1]

        return timestamp, 0

    def get_sliding_window(
        self, key: str, expiry: Optional[int] = None
    ) -> Tuple[int, float, int, float]:
        """
        returns the starting point and the number of entries in the moving
        window

        :param key: rate limit key
        :param expiry: expiry of entry
        :return: (start of window, number of acquired entries)
        """
        if expiry is None:
            raise ValueError("the expiry value is needed for this storage.")
        previous_key = self.prefixed_key(self._previous_window_key(key))
        current_key = self.prefixed_key(self._current_window_key(key))
        if window := self.lua_sliding_window([previous_key, current_key], [expiry]):
            previous_count, previous_expires_in, current_count, current_expires_in = (
                int(window[0] or 0),
                max(0, float(window[1] or 0)) / 1000,
                int(window[2] or 0),
                max(0, float(window[3] or 0)) / 1000,
            )
        return (
            previous_count,
            previous_expires_in,
            current_count,
            current_expires_in,
        )

    def _incr(
        self,
        key: str,
        expiry: int,
        connection: RedisClient,
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
        value = connection.incrby(key, amount)

        if elastic_expiry or value == amount:
            connection.expire(key, expiry)

        return value

    def _get(self, key: str, connection: RedisClient) -> int:
        """
        :param connection: Redis connection
        :param key: the key to get the counter value for
        """

        key = self.prefixed_key(key)
        return int(connection.get(key) or 0)

    def _clear(self, key: str, connection: RedisClient) -> None:
        """
        :param key: the key to clear rate limits for
        :param connection: Redis connection
        """
        key = self.prefixed_key(key)
        connection.delete(key)

    def _acquire_entry(
        self,
        key: str,
        limit: int,
        expiry: int,
        connection: RedisClient,
        amount: int = 1,
    ) -> bool:
        """
        :param key: rate limit key to acquire an entry in
        :param limit: amount of entries allowed
        :param expiry: expiry of the entry
        :param connection: Redis connection
        :param amount: the number of entries to acquire
        """
        key = self.prefixed_key(key)
        timestamp = time.time()
        acquired = self.lua_acquire_moving_window(
            [key], [timestamp, limit, expiry, amount]
        )

        return bool(acquired)

    def _acquire_sliding_window_entry(
        self,
        key: str,
        limit: int,
        expiry: int,
        amount: int = 1,
    ) -> bool:
        """
        Acquire an entry. Shift the current window to the previous window if it expired.
        :param current_window_key: current window key
        :param previous_window_key: previous window key
        :param limit: amount of entries allowed
        :param expiry: expiry of the entry
        :param amount: the number of entries to acquire
        """
        previous_key = self.prefixed_key(self._previous_window_key(key))
        current_key = self.prefixed_key(self._current_window_key(key))
        acquired = self.lua_acquire_sliding_window(
            [previous_key, current_key], [limit, expiry, amount]
        )
        return bool(acquired)

    def _get_expiry(self, key: str, connection: RedisClient) -> float:
        """
        :param key: the key to get the expiry for
        :param connection: Redis connection
        """

        key = self.prefixed_key(key)
        return max(connection.ttl(key), 0) + time.time()

    def _check(self, connection: RedisClient) -> bool:
        """
        :param connection: Redis connection
        check if storage is healthy
        """
        try:
            return connection.ping()
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


class RedisStorage(
    RedisInteractor, Storage, MovingWindowSupport, SlidingWindowCounterSupport
):
    """
    Rate limit storage with redis as backend.

    Depends on :pypi:`redis`.
    """

    STORAGE_SCHEME = ["redis", "rediss", "redis+unix"]
    """The storage scheme for redis"""

    DEPENDENCIES = {"redis": Version("3.0")}

    def __init__(
        self,
        uri: str,
        connection_pool: Optional[redis.connection.ConnectionPool] = None,
        wrap_exceptions: bool = False,
        **options: Union[float, str, bool],
    ) -> None:
        """
        :param uri: uri of the form ``redis://[:password]@host:port``,
         ``redis://[:password]@host:port/db``,
         ``rediss://[:password]@host:port``, ``redis+unix:///path/to/sock`` etc.
         This uri is passed directly to :func:`redis.from_url` except for the
         case of ``redis+unix://`` where it is replaced with ``unix://``.
        :param connection_pool: if provided, the redis client is initialized with
         the connection pool and any other params passed as :paramref:`options`
        :param wrap_exceptions: Whether to wrap storage exceptions in
         :exc:`limits.errors.StorageError` before raising it.
        :param options: all remaining keyword arguments are passed
         directly to the constructor of :class:`redis.Redis`
        :raise ConfigurationError: when the :pypi:`redis` library is not available
        """
        super().__init__(uri, wrap_exceptions=wrap_exceptions, **options)
        self.dependency = self.dependencies["redis"].module

        uri = uri.replace("redis+unix", "unix")

        if not connection_pool:
            self.storage = self.dependency.from_url(uri, **options)
        else:
            self.storage = self.dependency.Redis(
                connection_pool=connection_pool, **options
            )
        self.initialize_storage(uri)

    @property
    def base_exceptions(
        self,
    ) -> Union[Type[Exception], Tuple[Type[Exception], ...]]:  # pragma: no cover
        return self.dependency.RedisError  # type: ignore[no-any-return]

    def initialize_storage(self, _uri: str) -> None:
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

    def incr(
        self, key: str, expiry: int, elastic_expiry: bool = False, amount: int = 1
    ) -> int:
        """
        increments the counter for a given rate limit key

        :param key: the key to increment
        :param expiry: amount in seconds for the key to expire in
        :param amount: the number to increment by
        """

        if elastic_expiry:
            return super()._incr(key, expiry, self.storage, elastic_expiry, amount)
        else:
            key = self.prefixed_key(key)
            return int(self.lua_incr_expire([key], [expiry, amount]))

    def get(self, key: str) -> int:
        """
        :param key: the key to get the counter value for
        """

        return super()._get(key, self.storage)

    def clear(self, key: str) -> None:
        """
        :param key: the key to clear rate limits for
        """

        return super()._clear(key, self.storage)

    def acquire_entry(self, key: str, limit: int, expiry: int, amount: int = 1) -> bool:
        """
        :param key: rate limit key to acquire an entry in
        :param limit: amount of entries allowed
        :param expiry: expiry of the entry
        :param amount: the number to increment by
        """

        return super()._acquire_entry(key, limit, expiry, self.storage, amount)

    def acquire_sliding_window_entry(
        self,
        key: str,
        limit: int,
        expiry: int,
        amount: int = 1,
    ) -> bool:
        """
        Acquire an entry. Shift the current window to the previous window if it expired.
        :param key: rate limit key to acquire an entry in
        :param previous_window_key: previous window key
        :param limit: amount of entries allowed
        :param expiry: expiry of the entry
        :param amount: the number of entries to acquire
        """
        return super()._acquire_sliding_window_entry(key, limit, expiry, amount)

    def get_expiry(self, key: str) -> float:
        """
        :param key: the key to get the expiry for
        """

        return super()._get_expiry(key, self.storage)

    def check(self) -> bool:
        """
        check if storage is healthy
        """

        return super()._check(self.storage)

    def reset(self) -> Optional[int]:
        """
        This function calls a Lua Script to delete keys prefixed with
        ``self.PREFIX`` in blocks of 5000.

        .. warning::
           This operation was designed to be fast, but was not tested
           on a large production based system. Be careful with its usage as it
           could be slow on very large data sets.

        """

        prefix = self.prefixed_key("*")
        return int(self.lua_clear_keys([prefix]))
