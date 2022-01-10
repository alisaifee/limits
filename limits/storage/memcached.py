import inspect
import threading
import time
import urllib.parse

from ..errors import ConfigurationError
from ..util import get_dependency
from .base import Storage


class MemcachedStorage(Storage):
    """
    Rate limit storage with memcached as backend.

    Depends on :pypi:`pymemcache`.
    """

    STORAGE_SCHEME = ["memcached"]
    """The storage scheme for memcached"""

    def __init__(self, uri: str, **options):
        """
        :param uri: memcached location of the form
         ``memcached://host:port,host:port``,
         ``memcached:///var/tmp/path/to/sock``
        :param options: all remaining keyword arguments are passed
         directly to the constructor of :class:`pymemcache.client.base.PooledClient`
         or :class:`pymemcache.client.hash.HashClient` (if there are more than
         one hosts specified)
        :raise ConfigurationError: when :pypi:`pymemcache` is not available
        """
        parsed = urllib.parse.urlparse(uri)
        self.hosts = []

        for loc in parsed.netloc.strip().split(","):
            if not loc:
                continue
            host, port = loc.split(":")
            self.hosts.append((host, int(port)))
        else:
            # filesystem path to UDS

            if parsed.path and not parsed.netloc and not parsed.port:
                self.hosts = [parsed.path]  # type: ignore

        self.library = options.pop("library", "pymemcache.client")
        self.cluster_library = options.pop("cluster_library", "pymemcache.client.hash")
        self.client_getter = options.pop("client_getter", self.get_client)
        self.options = options

        if not get_dependency(self.library):
            raise ConfigurationError(
                "memcached prerequisite not available."
                " please install %s" % self.library
            )  # pragma: no cover
        self.local_storage = threading.local()
        self.local_storage.storage = None

    def get_client(self, module, hosts, **kwargs):
        """
        returns a memcached client.

        :param module: the memcached module
        :param hosts: list of memcached hosts
        """

        return (
            module.HashClient(hosts, **kwargs)
            if len(hosts) > 1
            else module.PooledClient(*hosts, **kwargs)
        )

    def call_memcached_func(self, func, *args, **kwargs):
        if "noreply" in kwargs:
            argspec = inspect.getfullargspec(func)

            if not ("noreply" in argspec.args or argspec.varkw):
                kwargs.pop("noreply")  # noqa

        return func(*args, **kwargs)

    @property
    def storage(self):
        """
        lazily creates a memcached client instance using a thread local
        """

        if not (hasattr(self.local_storage, "storage") and self.local_storage.storage):
            self.local_storage.storage = self.client_getter(
                get_dependency(
                    self.cluster_library if len(self.hosts) > 1 else self.library
                ),
                self.hosts,
                **self.options
            )

        return self.local_storage.storage

    def get(self, key: str) -> int:
        """
        :param key: the key to get the counter value for
        """

        return int(self.storage.get(key) or 0)

    def clear(self, key: str) -> None:
        """
        :param key: the key to clear rate limits for
        """
        self.storage.delete(key)

    def incr(self, key: str, expiry: int, elastic_expiry=False, amount: int = 1) -> int:
        """
        increments the counter for a given rate limit key

        :param key: the key to increment
        :param expiry: amount in seconds for the key to expire in
        :param elastic_expiry: whether to keep extending the rate limit
         window every hit.
        :param amount: the number to increment by
        """

        if not self.call_memcached_func(
            self.storage.add, key, amount, expiry, noreply=False
        ):
            value = self.storage.incr(key, amount) or amount

            if elastic_expiry:
                self.call_memcached_func(self.storage.touch, key, expiry)
                self.call_memcached_func(
                    self.storage.set,
                    key + "/expires",
                    expiry + time.time(),
                    expire=expiry,
                    noreply=False,
                )

            return value
        else:
            self.call_memcached_func(
                self.storage.set,
                key + "/expires",
                expiry + time.time(),
                expire=expiry,
                noreply=False,
            )

        return amount

    def get_expiry(self, key: str) -> int:
        """
        :param key: the key to get the expiry for
        """

        return int(float(self.storage.get(key + "/expires") or time.time()))

    def check(self) -> bool:
        """
        Check if storage is healthy by calling the ``get`` command
        on the key ``limiter-check``
        """
        try:
            self.call_memcached_func(self.storage.get, "limiter-check")

            return True
        except:  # noqa
            return False

    def reset(self):
        raise NotImplementedError
