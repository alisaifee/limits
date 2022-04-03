import urllib

from .redis import RedisStorage


class RedisClusterStorage(RedisStorage):
    """
    Rate limit storage with redis cluster as backend

    Depends on :pypi:`redis-cluster-py`
    """

    STORAGE_SCHEME = ["redis+cluster"]
    """The storage scheme for redis cluster"""

    DEFAULT_OPTIONS = {
        "max_connections": 1000,
    }
    "Default options passed to the :class:`~rediscluster.RedisCluster`"

    DEPENDENCIES = ["rediscluster"]

    def __init__(self, uri: str, **options):
        """
        :param uri: url of the form
         ``redis+cluster://[:password]@host:port,host:port``
        :param options: all remaining keyword arguments are passed
         directly to the constructor of :class:`rediscluster.RedisCluster`
        :raise ConfigurationError: when the :pypi:`redis-cluster-py` library is not
         available or if the redis host cannot be pinged.
        """
        parsed = urllib.parse.urlparse(uri)
        cluster_hosts = []
        for loc in parsed.netloc.split(","):
            host, port = loc.split(":")
            cluster_hosts.append({"host": host, "port": int(port)})

        self.storage = self.dependencies["rediscluster"].RedisCluster(
            startup_nodes=cluster_hosts, **{**self.DEFAULT_OPTIONS, **options}
        )
        self.initialize_storage(uri)
        super(RedisStorage, self).__init__()

    def reset(self) -> int:
        """
        Redis Clusters are sharded and deleting across shards
        can't be done atomically. Because of this, this reset loops over all
        keys that are prefixed with 'LIMITER' and calls delete on them, one at
        a time.

        .. warning::
         This operation was not tested with extremely large data sets.
         On a large production based system, care should be taken with its
         usage as it could be slow on very large data sets"""

        keys = self.storage.keys("LIMITER*")
        return sum([self.storage.delete(k.decode("utf-8")) for k in keys])
