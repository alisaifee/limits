import time

from .memcached import MemcachedStorage


class GAEMemcachedStorage(MemcachedStorage):  # noqa
    """
    rate limit storage with GAE memcache as backend
    """

    MAX_CAS_RETRIES = 10
    STORAGE_SCHEME = ["gaememcached"]

    def __init__(self, uri: str, **options):
        options["library"] = "google.appengine.api.memcache"
        super().__init__(uri, **options)

    def incr(
        self, key: str, expiry: int, elastic_expiry: bool = False, amount: int = 1
    ):
        """
        increments the counter for a given rate limit key

        :param key: the key to increment
        :param expiry: amount in seconds for the key to expire in
        :param elastic_expiry: whether to keep extending the rate limit
         window every hit.
        :param amount: the number to increment by
        """

        if not self.call_memcached_func(self.storage.add, key, amount, expiry):
            if elastic_expiry:
                # CAS id is set as state on the client object in GAE memcache
                value = self.storage.gets(key)
                retry = 0

                while (
                    not self.call_memcached_func(
                        self.storage.cas, key, int(value or 0) + amount, expiry
                    )
                    and retry < self.MAX_CAS_RETRIES
                ):
                    value = self.storage.gets(key)
                    retry += 1
                self.call_memcached_func(
                    self.storage.set, key + "/expires", expiry + time.time(), expiry
                )

                return int(value or 0) + amount
            else:
                return self.storage.incr(key, amount)
        self.call_memcached_func(
            self.storage.set, key + "/expires", expiry + time.time(), expiry
        )

        return 1

    def check(self) -> bool:
        """
        check if storage is healthy
        """
        try:
            self.call_memcached_func(self.storage.get_stats)

            return True
        except:  # noqa
            return False
