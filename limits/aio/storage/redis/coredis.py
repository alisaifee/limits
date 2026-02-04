from __future__ import annotations

import time
from typing import TYPE_CHECKING, cast

from limits.aio.storage.redis.bridge import RedisBridge
from limits.errors import ConfigurationError
from limits.typing import AsyncCoRedisClient, Callable

if TYPE_CHECKING:
    import coredis


class CoredisBridge(RedisBridge):
    DEFAULT_CLUSTER_OPTIONS: dict[str, float | str | bool] = {
        "max_connections": 1000,
    }
    "Default options passed to :class:`coredis.RedisCluster`"

    @property
    def base_exceptions(self) -> type[Exception] | tuple[type[Exception], ...]:
        return (self.dependency.exceptions.RedisError,)

    def use_sentinel(
        self,
        service_name: str | None,
        use_replicas: bool,
        sentinel_kwargs: dict[str, str | float | bool] | None,
        **options: str | float | bool,
    ) -> None:
        sentinel_configuration = []
        connection_options = options.copy()

        sentinel_configuration.extend(self.options_from_uri.locations)
        service_name = (
            self.options_from_uri.path.replace("/", "")
            if self.options_from_uri.path
            else service_name
        )

        if service_name is None:
            raise ConfigurationError("'service_name' not provided")

        self.sentinel = self.dependency.sentinel.Sentinel(
            sentinel_configuration,
            sentinel_kwargs={**self.parsed_auth, **(sentinel_kwargs or {})},
            **{**self.parsed_auth, **connection_options},
        )
        self.storage = self.sentinel.primary_for(service_name)
        self.storage_replica = self.sentinel.replica_for(service_name)
        self.connection_getter = lambda readonly: (
            self.storage_replica if readonly and use_replicas else self.storage
        )

    def use_basic(self, **options: str | float | bool) -> None:
        if connection_pool := options.pop("connection_pool", None):
            self.storage = self.dependency.Redis(
                connection_pool=connection_pool, **options
            )
        else:
            if self.options_from_uri.empty:
                self.storage = self.dependency.Redis(**options)
            else:
                self.storage = self.dependency.Redis.from_url(self.uri, **options)

        self.connection_getter = lambda _: self.storage

    def use_cluster(self, **options: str | float | bool) -> None:
        cluster_hosts: list[dict[str, int | str]] = []
        cluster_hosts.extend(
            {"host": host, "port": int(port)}
            for host, port in self.options_from_uri.locations
        )
        self.storage = self.dependency.RedisCluster(
            **{
                **self.DEFAULT_CLUSTER_OPTIONS,
                **{"startup_nodes": cluster_hosts},
                **self.parsed_auth,
                **options,
            },
        )
        self.connection_getter = lambda _: self.storage

    lua_moving_window: coredis.commands.Script[bytes]
    lua_acquire_moving_window: coredis.commands.Script[bytes]
    lua_sliding_window: coredis.commands.Script[bytes]
    lua_acquire_sliding_window: coredis.commands.Script[bytes]
    lua_clear_keys: coredis.commands.Script[bytes]
    lua_incr_expire: coredis.commands.Script[bytes]
    connection_getter: Callable[[bool], AsyncCoRedisClient]

    def get_connection(self, readonly: bool = False) -> AsyncCoRedisClient:
        return self.connection_getter(readonly)

    def register_scripts(self) -> None:
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

    async def incr(self, key: str, expiry: int, amount: int = 1) -> int:
        key = self.prefixed_key(key)
        if (value := await self.get_connection().incrby(key, amount)) == amount:
            await self.get_connection().expire(key, expiry)
        return value

    async def get(self, key: str) -> int:
        key = self.prefixed_key(key)
        return int(await self.get_connection(readonly=True).get(key) or 0)

    async def clear(self, key: str) -> None:
        key = self.prefixed_key(key)
        await self.get_connection().delete([key])

    async def lua_reset(self) -> int | None:
        return cast(int, await self.lua_clear_keys.execute([self.prefixed_key("*")]))

    async def get_moving_window(
        self, key: str, limit: int, expiry: int
    ) -> tuple[float, int]:
        key = self.prefixed_key(key)
        timestamp = time.time()
        window = await self.lua_moving_window.execute(
            [key], [timestamp - expiry, limit]
        )
        if window:
            return float(window[0]), window[1]  # type: ignore
        return timestamp, 0

    async def get_sliding_window(
        self, previous_key: str, current_key: str, expiry: int
    ) -> tuple[int, float, int, float]:
        previous_key = self.prefixed_key(previous_key)
        current_key = self.prefixed_key(current_key)

        if window := await self.lua_sliding_window.execute(
            [previous_key, current_key], [expiry]
        ):
            return (
                int(window[0] or 0),  # type: ignore
                max(0, float(window[1] or 0)) / 1000,  # type: ignore
                int(window[2] or 0),  # type: ignore
                max(0, float(window[3] or 0)) / 1000,  # type: ignore
            )
        return 0, 0.0, 0, 0.0

    async def acquire_entry(
        self, key: str, limit: int, expiry: int, amount: int = 1
    ) -> bool:
        key = self.prefixed_key(key)
        timestamp = time.time()
        acquired = await self.lua_acquire_moving_window.execute(
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
        acquired = await self.lua_acquire_sliding_window.execute(
            [previous_key, current_key], [limit, expiry, amount]
        )
        return bool(acquired)

    async def get_expiry(self, key: str) -> float:
        key = self.prefixed_key(key)
        return max(await self.get_connection().ttl(key), 0) + time.time()

    async def check(self) -> bool:
        try:
            await self.get_connection().ping()

            return True
        except:  # noqa
            return False

    async def reset(self) -> int | None:
        prefix = self.prefixed_key("*")
        keys = await self.storage.keys(prefix)
        count = 0
        for key in keys:
            count += await self.storage.delete([key])
        return count
