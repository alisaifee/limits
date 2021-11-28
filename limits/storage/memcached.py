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

    Depends on the `pymemcache` library.
    """

    MAX_CAS_RETRIES = 10
    STORAGE_SCHEME = ["memcached"]

    def __init__(self, uri: str, **options):
        """
        :param uri: memcached location of the form
         `memcached://host:port,host:port`, `memcached:///var/tmp/path/to/sock`
        :param options: all remaining keyword arguments are passed
         directly to the constructor of :class:`pymemcache.client.base.Client`
        :raise ConfigurationError: when `pymemcache` is not available
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
        self.cluster_library = options.pop("library", "pymemcache.client.hash")
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
        :return:
        """
        return (
            module.HashClient(hosts, **kwargs)
            if len(hosts) > 1
            else module.Client(*hosts, **kwargs)
        )

    def call_memcached_func(self, func, *args, **kwargs):
        if "noreply" in kwargs:
            argspec = inspect.getargspec(func)
            if not ("noreply" in argspec.args or argspec.keywords):
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

    def incr(self, key: str, expiry: int, elastic_expiry=False) -> int:
        """
        increments the counter for a given rate limit key

        :param key: the key to increment
        :param expiry: amount in seconds for the key to expire in
        :param elastic_expiry: whether to keep extending the rate limit
         window every hit.
        """
        if not self.call_memcached_func(
            self.storage.add, key, 1, expiry, noreply=False
        ):
            if elastic_expiry:
                value, cas = self.storage.gets(key)
                retry = 0
                while (
                    not self.call_memcached_func(
                        self.storage.cas, key, int(value or 0) + 1, cas, expiry
                    )
                    and retry < self.MAX_CAS_RETRIES
                ):
                    value, cas = self.storage.gets(key)
                    retry += 1
                self.call_memcached_func(
                    self.storage.set,
                    key + "/expires",
                    expiry + time.time(),
                    expire=expiry,
                    noreply=False,
                )
                return int(value or 0) + 1
            else:
                return self.storage.incr(key, 1) or 1
        self.call_memcached_func(
            self.storage.set,
            key + "/expires",
            expiry + time.time(),
            expire=expiry,
            noreply=False,
        )
        return 1

    def get_expiry(self, key: str) -> int:
        """
        :param key: the key to get the expiry for
        """
        return int(float(self.storage.get(key + "/expires") or time.time()))

    def check(self) -> bool:
        """
        check if storage is healthy
        """
        try:
            self.call_memcached_func(self.storage.get, "limiter-check")
            return True
        except:  # noqa
            return False

    def reset(self):
        raise NotImplementedError
