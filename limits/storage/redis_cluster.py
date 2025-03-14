from __future__ import annotations

import urllib

from deprecated.sphinx import versionchanged
from packaging.version import Version

from limits.storage.redis import RedisStorage


@versionchanged(
    version="3.14.0",
    reason="""
Dropped support for the :pypi:`redis-py-cluster` library
which has been abandoned/deprecated.
""",
)
@versionchanged(
    version="2.5.0",
    reason="""
Cluster support was provided by the :pypi:`redis-py-cluster` library
which has been absorbed into the official :pypi:`redis` client. By
default the :class:`redis.cluster.RedisCluster` client will be used
however if the version of the package is lower than ``4.2.0`` the implementation
will fallback to trying to use :class:`rediscluster.RedisCluster`.
""",
)
@versionchanged(
    version="4.3",
    reason=(
        "Added support for using the redis client from :pypi:`valkey`"
        " if :paramref:`uri` has the ``valkey+cluster://`` schema"
    ),
)
class RedisClusterStorage(RedisStorage):
    """
    Rate limit storage with redis cluster as backend

    Depends on :pypi:`redis` (or :pypi:`valkey` if :paramref:`uri`
    starts with ``valkey+cluster://``).
    """

    STORAGE_SCHEME = ["redis+cluster", "valkey+cluster"]
    """The storage scheme for redis cluster"""

    DEFAULT_OPTIONS: dict[str, float | str | bool] = {
        "max_connections": 1000,
    }
    "Default options passed to the :class:`~redis.cluster.RedisCluster`"

    DEPENDENCIES = {
        "redis": Version("4.2.0"),
        "valkey": Version("6.0"),
    }

    def __init__(
        self,
        uri: str,
        wrap_exceptions: bool = False,
        **options: float | str | bool,
    ) -> None:
        """
        :param uri: url of the form
         ``redis+cluster://[:password]@host:port,host:port``

         If the uri scheme is ``valkey+cluster`` the implementation used will be from
         :pypi:`valkey`.
        :param wrap_exceptions: Whether to wrap storage exceptions in
         :exc:`limits.errors.StorageError` before raising it.
        :param options: all remaining keyword arguments are passed
         directly to the constructor of :class:`redis.cluster.RedisCluster`
        :raise ConfigurationError: when the :pypi:`redis` library is not
         available or if the redis cluster cannot be reached.
        """
        parsed = urllib.parse.urlparse(uri)
        parsed_auth: dict[str, float | str | bool] = {}

        if parsed.username:
            parsed_auth["username"] = parsed.username
        if parsed.password:
            parsed_auth["password"] = parsed.password

        sep = parsed.netloc.find("@") + 1
        cluster_hosts = []
        for loc in parsed.netloc[sep:].split(","):
            host, port = loc.split(":")
            cluster_hosts.append((host, int(port)))

        self.storage = None
        self.target_server = "valkey" if uri.startswith("valkey") else "redis"
        merged_options = {**self.DEFAULT_OPTIONS, **parsed_auth, **options}
        self.dependency = self.dependencies[self.target_server].module
        startup_nodes = [self.dependency.cluster.ClusterNode(*c) for c in cluster_hosts]
        if self.target_server == "redis":
            self.storage = self.dependency.cluster.RedisCluster(
                startup_nodes=startup_nodes, **merged_options
            )
        else:
            self.storage = self.dependency.cluster.ValkeyCluster(
                startup_nodes=startup_nodes, **merged_options
            )

        assert self.storage
        self.initialize_storage(uri)
        super(RedisStorage, self).__init__(uri, wrap_exceptions, **options)

    def reset(self) -> int | None:
        """
        Redis Clusters are sharded and deleting across shards
        can't be done atomically. Because of this, this reset loops over all
        keys that are prefixed with ``self.PREFIX`` and calls delete on them,
        one at a time.

        .. warning::
         This operation was not tested with extremely large data sets.
         On a large production based system, care should be taken with its
         usage as it could be slow on very large data sets"""

        prefix = self.prefixed_key("*")
        count = 0
        for primary in self.storage.get_primaries():
            node = self.storage.get_redis_connection(primary)
            keys = node.keys(prefix)
            count += sum([node.delete(k.decode("utf-8")) for k in keys])
        return count
