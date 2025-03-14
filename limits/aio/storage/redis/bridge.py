from __future__ import annotations

import urllib
from abc import ABC, abstractmethod
from types import ModuleType

from limits.util import get_package_data


class RedisBridge(ABC):
    PREFIX = "LIMITS"
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

    def __init__(
        self,
        uri: str,
        dependency: ModuleType,
    ) -> None:
        self.uri = uri
        self.parsed_uri = urllib.parse.urlparse(self.uri)
        self.dependency = dependency
        self.parsed_auth = {}
        if self.parsed_uri.username:
            self.parsed_auth["username"] = self.parsed_uri.username
        if self.parsed_uri.password:
            self.parsed_auth["password"] = self.parsed_uri.password

    def prefixed_key(self, key: str) -> str:
        return f"{self.PREFIX}:{key}"

    @abstractmethod
    def register_scripts(self) -> None: ...

    @abstractmethod
    def use_sentinel(
        self,
        service_name: str | None,
        use_replicas: bool,
        sentinel_kwargs: dict[str, str | float | bool] | None,
        **options: str | float | bool,
    ) -> None: ...

    @abstractmethod
    def use_basic(self, **options: str | float | bool) -> None: ...

    @abstractmethod
    def use_cluster(self, **options: str | float | bool) -> None: ...

    @property
    @abstractmethod
    def base_exceptions(
        self,
    ) -> type[Exception] | tuple[type[Exception], ...]: ...

    @abstractmethod
    async def incr(
        self,
        key: str,
        expiry: int,
        amount: int = 1,
    ) -> int: ...

    @abstractmethod
    async def get(self, key: str) -> int: ...

    @abstractmethod
    async def clear(self, key: str) -> None: ...

    @abstractmethod
    async def get_moving_window(
        self, key: str, limit: int, expiry: int
    ) -> tuple[float, int]: ...

    @abstractmethod
    async def get_sliding_window(
        self, previous_key: str, current_key: str, expiry: int
    ) -> tuple[int, float, int, float]: ...

    @abstractmethod
    async def acquire_entry(
        self,
        key: str,
        limit: int,
        expiry: int,
        amount: int = 1,
    ) -> bool: ...

    @abstractmethod
    async def acquire_sliding_window_entry(
        self,
        previous_key: str,
        current_key: str,
        limit: int,
        expiry: int,
        amount: int = 1,
    ) -> bool: ...

    @abstractmethod
    async def get_expiry(self, key: str) -> float: ...

    @abstractmethod
    async def check(self) -> bool: ...

    @abstractmethod
    async def reset(self) -> int | None: ...

    @abstractmethod
    async def lua_reset(self) -> int | None: ...
