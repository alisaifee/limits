from __future__ import annotations

import time
from typing import TYPE_CHECKING, cast

from deprecated.sphinx import versionchanged
from packaging.version import Version

from limits.typing import Literal, RedisClient

from ..util import get_package_data
from .base import MovingWindowSupport, SlidingWindowCounterSupport, Storage

if TYPE_CHECKING:
    import redis


@versionchanged(
    version="4.3",
    reason=(
        "Added support for using the redis client from :pypi:`valkey`"
        " if :paramref:`uri` has the ``valkey://`` schema"
    ),
)
class RedisStorage(Storage, MovingWindowSupport, SlidingWindowCounterSupport):
    """
    Rate limit storage with redis as backend.

    Depends on :pypi:`redis` (or :pypi:`valkey` if :paramref:`uri` starts with
    ``valkey://``)
    """

    STORAGE_SCHEME = [
        "redis",
        "rediss",
        "redis+unix",
        "valkey",
        "valkeys",
        "valkey+unix",
    ]
    """The storage scheme for redis"""

    DEPENDENCIES = {"redis": Version("3.0"), "valkey": Version("6.0")}

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

    PREFIX = "LIMITS"
    target_server: Literal["redis", "valkey"]

    def __init__(
        self,
        uri: str,
        connection_pool: redis.connection.ConnectionPool | None = None,
        key_prefix: str = PREFIX,
        wrap_exceptions: bool = False,
        **options: float | str | bool,
    ) -> None:
        """
        :param uri: uri of the form ``redis://[:password]@host:port``,
         ``redis://[:password]@host:port/db``,
         ``rediss://[:password]@host:port``, ``redis+unix:///path/to/sock`` etc.
         This uri is passed directly to :func:`redis.from_url` except for the
         case of ``redis+unix://`` where it is replaced with ``unix://``.

         If the uri scheme is ``valkey`` the implementation used will be from
         :pypi:`valkey`.
        :param connection_pool: if provided, the redis client is initialized with
         the connection pool and any other params passed as :paramref:`options`
        :param key_prefix: the prefix for each key created in redis
        :param wrap_exceptions: Whether to wrap storage exceptions in
         :exc:`limits.errors.StorageError` before raising it.
        :param options: all remaining keyword arguments are passed
         directly to the constructor of :class:`redis.Redis`
        :raise ConfigurationError: when the :pypi:`redis` library is not available
        """
        super().__init__(uri, wrap_exceptions=wrap_exceptions, **options)
        self.key_prefix = key_prefix
        self.target_server = "valkey" if uri.startswith("valkey") else "redis"
        self.dependency = self.dependencies[self.target_server].module

        uri = uri.replace(f"{self.target_server}+unix", "unix")

        if not connection_pool:
            self.storage = self.dependency.from_url(uri, **options)
        else:
            if self.target_server == "redis":
                self.storage = self.dependency.Redis(
                    connection_pool=connection_pool, **options
                )
            else:
                self.storage = self.dependency.Valkey(
                    connection_pool=connection_pool, **options
                )
        self.initialize_storage(uri)

    @property
    def base_exceptions(
        self,
    ) -> type[Exception] | tuple[type[Exception], ...]:  # pragma: no cover
        return (  # type: ignore[no-any-return]
            self.dependency.RedisError
            if self.target_server == "redis"
            else self.dependency.ValkeyError
        )

    def initialize_storage(self, _uri: str) -> None:
        self.lua_moving_window = self.get_connection().register_script(
            self.SCRIPT_MOVING_WINDOW
        )
        self.lua_acquire_moving_window = self.get_connection().register_script(
            self.SCRIPT_ACQUIRE_MOVING_WINDOW
        )
        self.lua_clear_keys = self.get_connection().register_script(
            self.SCRIPT_CLEAR_KEYS
        )
        self.lua_incr_expire = self.get_connection().register_script(
            self.SCRIPT_INCR_EXPIRE
        )
        self.lua_sliding_window = self.get_connection().register_script(
            self.SCRIPT_SLIDING_WINDOW
        )
        self.lua_acquire_sliding_window = self.get_connection().register_script(
            self.SCRIPT_ACQUIRE_SLIDING_WINDOW
        )

    def get_connection(self, readonly: bool = False) -> RedisClient:
        return cast(RedisClient, self.storage)

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

    def prefixed_key(self, key: str) -> str:
        return f"{self.key_prefix}:{key}"

    def get_moving_window(self, key: str, limit: int, expiry: int) -> tuple[float, int]:
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
        self, key: str, expiry: int
    ) -> tuple[int, float, int, float]:
        previous_key = self.prefixed_key(self._previous_window_key(key))
        current_key = self.prefixed_key(self._current_window_key(key))
        if window := self.lua_sliding_window([previous_key, current_key], [expiry]):
            return (
                int(window[0] or 0),
                max(0, float(window[1] or 0)) / 1000,
                int(window[2] or 0),
                max(0, float(window[3] or 0)) / 1000,
            )
        return 0, 0.0, 0, 0.0

    def incr(
        self,
        key: str,
        expiry: int,
        amount: int = 1,
    ) -> int:
        """
        increments the counter for a given rate limit key


        :param key: the key to increment
        :param expiry: amount in seconds for the key to expire in
        :param amount: the number to increment by
        """
        key = self.prefixed_key(key)
        return int(self.lua_incr_expire([key], [expiry, amount]))

    def get(self, key: str) -> int:
        """

        :param key: the key to get the counter value for
        """

        key = self.prefixed_key(key)
        return int(self.get_connection(True).get(key) or 0)

    def clear(self, key: str) -> None:
        """
        :param key: the key to clear rate limits for
        """
        key = self.prefixed_key(key)
        self.get_connection().delete(key)

    def acquire_entry(
        self,
        key: str,
        limit: int,
        expiry: int,
        amount: int = 1,
    ) -> bool:
        """
        :param key: rate limit key to acquire an entry in
        :param limit: amount of entries allowed
        :param expiry: expiry of the entry

        :param amount: the number of entries to acquire
        """
        key = self.prefixed_key(key)
        timestamp = time.time()
        acquired = self.lua_acquire_moving_window(
            [key], [timestamp, limit, expiry, amount]
        )

        return bool(acquired)

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

    def get_expiry(self, key: str) -> float:
        """
        :param key: the key to get the expiry for

        """

        key = self.prefixed_key(key)
        return max(self.get_connection(True).ttl(key), 0) + time.time()

    def check(self) -> bool:
        """
        check if storage is healthy
        """
        try:
            return self.get_connection().ping()
        except:  # noqa
            return False

    def reset(self) -> int | None:
        """
        This function calls a Lua Script to delete keys prefixed with
        :paramref:`RedisStorage.key_prefix` in blocks of 5000.

        .. warning::
           This operation was designed to be fast, but was not tested
           on a large production based system. Be careful with its usage as it
           could be slow on very large data sets.

        """

        prefix = self.prefixed_key("*")
        return int(self.lua_clear_keys([prefix]))
