from __future__ import annotations

import time
from typing import TYPE_CHECKING, cast

from limits.aio.storage.redis.bridge import RedisBridge
from limits.errors import ConfigurationError
from limits.typing import AsyncRedisClient, Callable

if TYPE_CHECKING:
    import redis.commands


class RedispyBridge(RedisBridge):
    DEFAULT_CLUSTER_OPTIONS: dict[str, float | str | bool] = {
        "max_connections": 1000,
    }
    "Default options passed to :class:`redis.asyncio.RedisCluster`"

    @property
    def base_exceptions(self) -> type[Exception] | tuple[type[Exception], ...]:
        return (self.dependency.RedisError,)

    def use_sentinel(
        self,
        service_name: str | None,
        use_replicas: bool,
        sentinel_kwargs: dict[str, str | float | bool] | None,
        **options: str | float | bool,
    ) -> None:
        sentinel_configuration = []

        connection_options = options.copy()

        sep = self.parsed_uri.netloc.find("@") + 1

        for loc in self.parsed_uri.netloc[sep:].split(","):
            host, port = loc.split(":")
            sentinel_configuration.append((host, int(port)))
        service_name = (
            self.parsed_uri.path.replace("/", "")
            if self.parsed_uri.path
            else service_name
        )

        if service_name is None:
            raise ConfigurationError("'service_name' not provided")

        self.sentinel = self.dependency.asyncio.Sentinel(
            sentinel_configuration,
            sentinel_kwargs={**self.parsed_auth, **(sentinel_kwargs or {})},
            **{**self.parsed_auth, **connection_options},
        )
        self.storage = self.sentinel.master_for(service_name)
        self.storage_replica = self.sentinel.slave_for(service_name)
        self.connection_getter = lambda readonly: (
            self.storage_replica if readonly and use_replicas else self.storage
        )

    def use_basic(self, **options: str | float | bool) -> None:
        if connection_pool := options.pop("connection_pool", None):
            self.storage = self.dependency.asyncio.Redis(
                connection_pool=connection_pool, **options
            )
        else:
            self.storage = self.dependency.asyncio.Redis.from_url(self.uri, **options)

        self.connection_getter = lambda _: self.storage

    def use_cluster(self, **options: str | float | bool) -> None:
        sep = self.parsed_uri.netloc.find("@") + 1
        cluster_hosts = []

        for loc in self.parsed_uri.netloc[sep:].split(","):
            host, port = loc.split(":")
            cluster_hosts.append(
                self.dependency.asyncio.cluster.ClusterNode(host=host, port=int(port))
            )

        self.storage = self.dependency.asyncio.RedisCluster(
            startup_nodes=cluster_hosts,
            **{**self.DEFAULT_CLUSTER_OPTIONS, **self.parsed_auth, **options},
        )
        self.connection_getter = lambda _: self.storage

    lua_moving_window: redis.commands.core.Script
    lua_acquire_moving_window: redis.commands.core.Script
    lua_sliding_window: redis.commands.core.Script
    lua_acquire_sliding_window: redis.commands.core.Script
    lua_clear_keys: redis.commands.core.Script
    lua_incr_expire: redis.commands.core.Script
    connection_getter: Callable[[bool], AsyncRedisClient]

    def get_connection(self, readonly: bool = False) -> AsyncRedisClient:
        return self.connection_getter(readonly)

    def register_scripts(self) -> None:
        # Redis-py uses a slightly different script registration
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

    async def incr(
        self,
        key: str,
        expiry: int,
        elastic_expiry: bool = False,
        amount: int = 1,
    ) -> int:
        """
        increments the counter for a given rate limit key


        :param key: the key to increment
        :param expiry: amount in seconds for the key to expire in
        :param amount: the number to increment by
        """
        key = self.prefixed_key(key)

        if elastic_expiry:
            value = await self.get_connection().incrby(key, amount)
            await self.get_connection().expire(key, expiry)
            return value
        else:
            return cast(int, await self.lua_incr_expire([key], [expiry, amount]))

    async def get(self, key: str) -> int:
        """

        :param key: the key to get the counter value for
        """

        key = self.prefixed_key(key)
        return int(await self.get_connection(readonly=True).get(key) or 0)

    async def clear(self, key: str) -> None:
        """
        :param key: the key to clear rate limits for

        """
        key = self.prefixed_key(key)
        await self.get_connection().delete(key)

    async def lua_reset(self) -> int | None:
        return cast(int, await self.lua_clear_keys([self.prefixed_key("*")]))

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
        self, previous_key: str, current_key: str, expiry: int
    ) -> tuple[int, float, int, float]:
        if window := await self.lua_sliding_window(
            [self.prefixed_key(previous_key), self.prefixed_key(current_key)], [expiry]
        ):
            return (
                int(window[0] or 0),
                max(0, float(window[1] or 0)) / 1000,
                int(window[2] or 0),
                max(0, float(window[3] or 0)) / 1000,
            )
        return 0, 0.0, 0, 0.0

    async def acquire_entry(
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

        """
        key = self.prefixed_key(key)
        timestamp = time.time()
        acquired = await self.lua_acquire_moving_window(
            [key], [timestamp, limit, expiry, amount]
        )

        return bool(acquired)

    async def acquire_sliding_window_entry(
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

    async def get_expiry(self, key: str) -> float:
        """
        :param key: the key to get the expiry for
        """

        key = self.prefixed_key(key)
        return max(await self.get_connection().ttl(key), 0) + time.time()

    async def check(self) -> bool:
        """
        check if storage is healthy
        """
        try:
            await self.get_connection().ping()

            return True
        except:  # noqa
            return False

    async def reset(self) -> int | None:
        prefix = self.prefixed_key("*")
        keys = await self.storage.keys(
            prefix, target_nodes=self.dependency.asyncio.cluster.RedisCluster.ALL_NODES
        )
        count = 0
        for key in keys:
            count += await self.storage.delete(key)
        return count
