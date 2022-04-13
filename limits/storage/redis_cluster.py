import urllib
import warnings
from typing import Any, List, Tuple

from packaging.version import Version

from ..errors import ConfigurationError
from .redis import RedisStorage


class RedisClusterStorage(RedisStorage):
    """
    Rate limit storage with redis cluster as backend

    Depends on :pypi:`redis`
    """

    STORAGE_SCHEME = ["redis+cluster"]
    """The storage scheme for redis cluster"""

    DEFAULT_OPTIONS = {
        "max_connections": 1000,
    }
    "Default options passed to the :class:`~redis.cluster.RedisCluster`"

    DEPENDENCIES = ["redis", "rediscluster"]
    FAIL_ON_MISSING_DEPENDENCY = False

    def __init__(self, uri: str, **options):
        """
        :param uri: url of the form
         ``redis+cluster://[:password]@host:port,host:port``
        :param options: all remaining keyword arguments are passed
         directly to the constructor of :class:`redis.cluster.RedisCluster`
        :raise ConfigurationError: when the :pypi:`redis` library is not
         available or if the redis cluster cannot be reached.
        """
        parsed = urllib.parse.urlparse(uri)
        cluster_hosts = []
        for loc in parsed.netloc.split(","):
            host, port = loc.split(":")
            cluster_hosts.append((host, int(port)))

        self.storage = None
        self.using_redis_py = False
        self.__pick_storage(cluster_hosts, **{**self.DEFAULT_OPTIONS, **options})
        assert self.storage
        self.initialize_storage(uri)
        super(RedisStorage, self).__init__()

    def __pick_storage(self, cluster_hosts: List[Tuple[str, int]], **options: Any):
        redis_py = self.dependencies["redis"]
        redis_cluster = self.dependencies["rediscluster"]
        if redis_py:
            redis_py_version = Version(redis_py.__version__)
            if redis_py_version > Version("4.2.0"):
                startup_nodes = [
                    redis_py.cluster.ClusterNode(*c) for c in cluster_hosts
                ]
                self.storage = redis_py.cluster.RedisCluster(
                    startup_nodes=startup_nodes, **options
                )
                self.using_redis_py = True
                return
        if redis_cluster:
            warnings.warn(
                (
                    "Using redis-py-cluster is deprecated as the library has been"
                    " absorbed by redis-py (>=4.2). This support will be removed"
                    " in limits 2.6. To get rid of this warning, uninstall"
                    " redis-py-cluster and ensure redis-py>=4.2.0 is installed"
                )
            )
            self.storage = redis_cluster.RedisCluster(
                startup_nodes=[{"host": c[0], "port": c[1]} for c in cluster_hosts],
                **options
            )
        if not self.storage:
            raise ConfigurationError(
                (
                    "Unable to find an implementation for redis cluster"
                    " Cluster support requires either redis-py>=4.2 or"
                    " redis-py-cluster"
                )
            )  # pragma: no cover

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

        if self.using_redis_py:
            count = 0
            for primary in self.storage.get_primaries():
                node = self.storage.get_redis_connection(primary)
                keys = node.keys("LIMITER*")
                count += sum([node.delete(k.decode("utf-8")) for k in keys])
            return count
        else:
            keys = self.storage.keys("LIMITER*")
            return sum([self.storage.delete(k.decode("utf-8")) for k in keys])
