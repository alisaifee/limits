import urllib.parse

from ..errors import ConfigurationError
from ..util import get_dependency
from .redis import RedisStorage


class RedisSentinelStorage(RedisStorage):
    """
    Rate limit storage with redis sentinel as backend

    Depends on `redis-py` library
    """

    STORAGE_SCHEME = ["redis+sentinel"]

    def __init__(self, uri: str, service_name: str = None, **options):
        """
        :param uri: url of the form
         `redis+sentinel://host:port,host:port/service_name`
        :param service_name, optional: sentinel service name
         (if not provided in `uri`)
        :param options: all remaining keyword arguments are passed
         directly to the constructor of :class:`redis.sentinel.Sentinel`
        :raise ConfigurationError: when the redis library is not available
         or if the redis master host cannot be pinged.
        """

        if not get_dependency("redis"):
            raise ConfigurationError(
                "redis prerequisite not available"
            )  # pragma: no cover

        parsed = urllib.parse.urlparse(uri)
        sentinel_configuration = []
        password = None

        if parsed.password:
            password = parsed.password

        for loc in parsed.netloc[parsed.netloc.find("@") + 1:].split(","):
            host, port = loc.split(":")
            sentinel_configuration.append((host, int(port)))
        self.service_name = (
            parsed.path.replace("/", "") if parsed.path else service_name
        )

        if self.service_name is None:
            raise ConfigurationError("'service_name' not provided")

        options.setdefault("socket_timeout", 0.2)

        self.sentinel = get_dependency("redis.sentinel").Sentinel(
            sentinel_configuration, password=password, **options
        )
        self.storage = self.sentinel.master_for(self.service_name)
        self.storage_slave = self.sentinel.slave_for(self.service_name)
        self.initialize_storage(uri)
        super(RedisStorage, self).__init__()

    def get(self, key: str) -> int:
        """
        :param key: the key to get the counter value for
        """

        return super(RedisStorage, self)._get(key, self.storage_slave)

    def get_expiry(self, key: str) -> int:
        """
        :param key: the key to get the expiry for
        """

        return super(RedisStorage, self)._get_expiry(key, self.storage_slave)

    def check(self) -> bool:
        """
        check if storage is healthy
        """

        return super(RedisStorage, self)._check(self.storage_slave)
