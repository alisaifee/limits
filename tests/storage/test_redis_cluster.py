import mock
import rediscluster

from limits.storage import RedisClusterStorage, storage_from_string
from tests.storage.test_redis import SharedRedisTests


class TestRedisClusterStorage(SharedRedisTests):
    def setup_method(self):
        rediscluster.RedisCluster("localhost", 7000).flushall()
        self.storage_url = "redis+cluster://localhost:7000"
        self.storage = RedisClusterStorage("redis+cluster://localhost:7000")

    def test_init_options(self):
        with mock.patch(
            "limits.storage.redis_cluster.get_dependency"
        ) as get_dependency:
            storage_from_string(self.storage_url, connection_timeout=1)
            call_args = get_dependency().RedisCluster.call_args
            assert call_args[1]['connection_timeout'] == 1
