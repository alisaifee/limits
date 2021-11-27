import time

from .memcached import MemcachedStorage


class GAEMemcachedStorage(MemcachedStorage):
    """
    rate limit storage with GAE memcache as backend
    """

    MAX_CAS_RETRIES = 10
    STORAGE_SCHEME = ["gaememcached"]

    def __init__(self, uri, **options):
        options["library"] = "google.appengine.api.memcache"
        super(GAEMemcachedStorage, self).__init__(uri, **options)

    def incr(self, key, expiry, elastic_expiry=False):
        """
        increments the counter for a given rate limit key

        :param str key: the key to increment
        :param int expiry: amount in seconds for the key to expire in
        :param bool elastic_expiry: whether to keep extending the rate limit
         window every hit.
        """
        if not self.call_memcached_func(self.storage.add, key, 1, expiry):
            if elastic_expiry:
                # CAS id is set as state on the client object in GAE memcache
                value = self.storage.gets(key)
                retry = 0
                while (
                    not self.call_memcached_func(
                        self.storage.cas, key, int(value or 0) + 1, expiry
                    )
                    and retry < self.MAX_CAS_RETRIES
                ):
                    value = self.storage.gets(key)
                    retry += 1
                self.call_memcached_func(
                    self.storage.set, key + "/expires", expiry + time.time(), expiry
                )
                return int(value or 0) + 1
            else:
                return self.storage.incr(key, 1)
        self.call_memcached_func(
            self.storage.set, key + "/expires", expiry + time.time(), expiry
        )
        return 1

    def check(self):
        """
        check if storage is healthy
        """
        try:
            self.call_memcached_func(self.storage.get_stats)
            return True
        except:  # noqa
            return False
