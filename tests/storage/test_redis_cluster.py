import pytest
import rediscluster

from limits.storage import RedisClusterStorage, storage_from_string
from tests.storage.test_redis import SharedRedisTests


@pytest.mark.unit
class TestRedisClusterStorage(SharedRedisTests):
    def setup_method(self):
        rediscluster.RedisCluster("localhost", 7000).flushall()
        self.storage_url = "redis+cluster://localhost:7000"
        self.storage = RedisClusterStorage("redis+cluster://localhost:7000")

    def test_init_options(self, mocker):
        lib = mocker.Mock()
        mocker.patch("limits.storage.redis_cluster.get_dependency", return_value=lib)
        assert storage_from_string(self.storage_url, connection_timeout=1).check()
        assert lib.RedisCluster.call_args[1]["connection_timeout"] == 1
