from __future__ import annotations

import urllib.parse
from typing import TYPE_CHECKING

from deprecated.sphinx import versionchanged
from packaging.version import Version

from limits.errors import ConfigurationError
from limits.storage.redis import RedisStorage
from limits.typing import RedisClient

if TYPE_CHECKING:
    pass


@versionchanged(
    version="4.3",
    reason=(
        "Added support for using the redis client from :pypi:`valkey`"
        " if :paramref:`uri` has the ``valkey+sentinel://`` schema"
    ),
)
class RedisSentinelStorage(RedisStorage):
    """
    Rate limit storage with redis sentinel as backend

    Depends on :pypi:`redis` package (or :pypi:`valkey` if :paramref:`uri` starts with
    ``valkey+sentinel://``)
    """

    STORAGE_SCHEME = ["redis+sentinel", "valkey+sentinel"]
    """The storage scheme for redis accessed via a redis sentinel installation"""

    DEPENDENCIES = {
        "redis": Version("3.0"),
        "redis.sentinel": Version("3.0"),
        "valkey": Version("6.0"),
        "valkey.sentinel": Version("6.0"),
    }

    def __init__(
        self,
        uri: str,
        service_name: str | None = None,
        use_replicas: bool = True,
        sentinel_kwargs: dict[str, float | str | bool] | None = None,
        key_prefix: str = RedisStorage.PREFIX,
        wrap_exceptions: bool = False,
        **options: float | str | bool,
    ) -> None:
        """
        :param uri: url of the form
         ``redis+sentinel://host:port,host:port/service_name``

         If the uri scheme is ``valkey+sentinel`` the implementation used will be from
         :pypi:`valkey`.
        :param service_name: sentinel service name
         (if not provided in :attr:`uri`)
        :param use_replicas: Whether to use replicas for read only operations
        :param sentinel_kwargs: kwargs to pass as
         :attr:`sentinel_kwargs` to :class:`redis.sentinel.Sentinel`
        :param key_prefix: the prefix for each key created in redis
        :param wrap_exceptions: Whether to wrap storage exceptions in
         :exc:`limits.errors.StorageError` before raising it.
        :param options: all remaining keyword arguments are passed
         directly to the constructor of :class:`redis.sentinel.Sentinel`
        :raise ConfigurationError: when the redis library is not available
         or if the redis master host cannot be pinged.
        """

        super(RedisStorage, self).__init__(
            uri, wrap_exceptions=wrap_exceptions, **options
        )

        parsed = urllib.parse.urlparse(uri)
        sentinel_configuration = []
        sentinel_options = sentinel_kwargs.copy() if sentinel_kwargs else {}

        parsed_auth: dict[str, float | str | bool] = {}

        if parsed.username:
            parsed_auth["username"] = parsed.username
        if parsed.password:
            parsed_auth["password"] = parsed.password

        sep = parsed.netloc.find("@") + 1

        for loc in parsed.netloc[sep:].split(","):
            host, port = loc.split(":")
            sentinel_configuration.append((host, int(port)))
        self.key_prefix = key_prefix
        self.service_name = (
            parsed.path.replace("/", "") if parsed.path else service_name
        )

        if self.service_name is None:
            raise ConfigurationError("'service_name' not provided")

        self.target_server = "valkey" if uri.startswith("valkey") else "redis"
        sentinel_dep = self.dependencies[f"{self.target_server}.sentinel"].module
        self.sentinel = sentinel_dep.Sentinel(
            sentinel_configuration,
            sentinel_kwargs={**parsed_auth, **sentinel_options},
            **{**parsed_auth, **options},
        )
        self.storage: RedisClient = self.sentinel.master_for(self.service_name)
        self.storage_slave: RedisClient = self.sentinel.slave_for(self.service_name)
        self.use_replicas = use_replicas
        self.initialize_storage(uri)

    @property
    def base_exceptions(
        self,
    ) -> type[Exception] | tuple[type[Exception], ...]:  # pragma: no cover
        return (  # type: ignore[no-any-return]
            self.dependencies["redis"].module.RedisError
            if self.target_server == "redis"
            else self.dependencies["valkey"].module.ValkeyError
        )

    def get_connection(self, readonly: bool = False) -> RedisClient:
        return self.storage_slave if (readonly and self.use_replicas) else self.storage
