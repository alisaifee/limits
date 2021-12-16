import time
import urllib.parse

from ...errors import ConfigurationError
from ...util import get_dependency
from .base import Storage


class MemcachedStorage(Storage):
    """
    Rate limit storage with memcached as backend.

    Depends on the `emcache` library.
    """

    STORAGE_SCHEME = ["async+memcached"]

    def __init__(self, uri: str, **options):
        """
        :param uri: memcached location of the form
         `amemcached://host:port,host:port`
        :param options: all remaining keyword arguments are passed
         directly to the constructor of :class:`emcache.Client`
        :raise ConfigurationError: when `aiomcache` is not available
        """
        parsed = urllib.parse.urlparse(uri)
        self.hosts = []

        for loc in parsed.netloc.strip().split(","):
            if not loc:
                continue
            host, port = loc.split(":")
            self.hosts.append((host, int(port)))

        self.dependency = get_dependency("emcache")

        if not self.dependency:
            raise ConfigurationError(
                "memcached prerequisite not available." " please install emcache"
            )  # pragma: no cover
        self._options = options
        self._storage = None

    async def get_storage(self):
        if not self._storage:
            self._storage = await self.dependency.create_client(
                [self.dependency.MemcachedHostAddress(h, p) for h, p in self.hosts],
                **self._options,
            )

        return self._storage

    async def get(self, key: str) -> int:
        """
        :param key: the key to get the counter value for
        """

        item = await (await self.get_storage()).get(key.encode("utf-8"))

        return item and int(item.value) or 0

    async def clear(self, key: str) -> None:
        """
        :param key: the key to clear rate limits for
        """
        await (await self.get_storage()).delete(key.encode("utf-8"))

    async def incr(self, key: str, expiry: int, elastic_expiry=False) -> int:
        """
        increments the counter for a given rate limit key

        :param key: the key to increment
        :param expiry: amount in seconds for the key to expire in
        :param elastic_expiry: whether to keep extending the rate limit
         window every hit.
        """
        storage = await self.get_storage()
        limit_key = key.encode("utf-8")
        expire_key = f"{key}/expires".encode("utf-8")
        added = True
        try:
            await storage.add(limit_key, b"1", exptime=expiry)
        except self.dependency.NotStoredStorageCommandError:
            added = False
            storage = await self.get_storage()

        if not added:
            value = await storage.increment(limit_key, 1) or 1
            if elastic_expiry:
                await storage.touch(limit_key, exptime=expiry)
            await storage.set(
                expire_key,
                str(expiry + time.time()).encode("utf-8"),
                exptime=expiry,
                noreply=False,
            )
            return value

        return 1

    async def get_expiry(self, key: str) -> int:
        """
        :param key: the key to get the expiry for
        """
        storage = await self.get_storage()

        return int(
            float(await storage.get(f"{key}/expires".encode("utf-8")) or time.time())
        )

    async def check(self) -> bool:
        """
        check if storage is healthy
        """
        try:
            storage = await self.get_storage()
            await storage.get(b"limiter-check")

            return True
        except:  # noqa
            return False

    async def reset(self):
        raise NotImplementedError
