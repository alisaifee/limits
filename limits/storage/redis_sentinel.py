import urllib.parse
from typing import Any, Dict, Optional

from ..errors import ConfigurationError
from .redis import RedisStorage


class RedisSentinelStorage(RedisStorage):
    """
    Rate limit storage with redis sentinel as backend

    Depends on :pypi:`redis` package
    """

    STORAGE_SCHEME = ["redis+sentinel"]
    """The storage scheme for redis accessed via a redis sentinel installation"""

    DEFAULT_OPTIONS = {
        "socket_timeout": 0.2,
    }
    "Default options passed to :class:`~redis.sentinel.Sentinel`"

    DEPENDENCIES = ["redis.sentinel"]

    def __init__(
        self,
        uri: str,
        service_name: str = None,
        sentinel_kwargs: Optional[Dict[str, Any]] = None,
        **options
    ):
        """
        :param uri: url of the form
         ``redis+sentinel://host:port,host:port/service_name``
        :param service_name: sentinel service name
         (if not provided in :attr:`uri`)
        :param sentinel_kwargs: kwargs to pass as
         :attr:`sentinel_kwargs` to :class:`redis.sentinel.Sentinel`
        :param options: all remaining keyword arguments are passed
         directly to the constructor of :class:`redis.sentinel.Sentinel`
        :raise ConfigurationError: when the redis library is not available
         or if the redis master host cannot be pinged.
        """

        super(RedisStorage, self).__init__()

        parsed = urllib.parse.urlparse(uri)
        sentinel_configuration = []
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

        self.sentinel = self.dependencies["redis.sentinel"].Sentinel(
            sentinel_configuration,
            sentinel_kwargs=sentinel_options,
            **{**self.DEFAULT_OPTIONS, **options}
        )
        self.storage = self.sentinel.master_for(self.service_name)
        self.storage_slave = self.sentinel.slave_for(self.service_name)
        self.initialize_storage(uri)

    def get(self, key: str) -> int:
        """
        :param key: the key to get the counter value for
        """

        return super()._get(key, self.storage_slave)

    def get_expiry(self, key: str) -> int:
        """
        :param key: the key to get the expiry for
        """

        return super()._get_expiry(key, self.storage_slave)

    def check(self) -> bool:
        """
        Check if storage is healthy by calling :class:`aredis.StrictRedis.ping`
        on the slave.
        """

        return super()._check(self.storage_slave)
