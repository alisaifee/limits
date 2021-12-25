import pytest
import rediscluster

from limits.storage import RedisClusterStorage, storage_from_string
from tests.storage.test_redis import SharedRedisTests


@pytest.mark.redis_cluster
class TestRedisClusterStorage(SharedRedisTests):
    @pytest.fixture(autouse=True)
    def setup(self, redis_cluster):
        self.storage_url = "redis+cluster://localhost:7001"
        self.storage = RedisClusterStorage("redis+cluster://localhost:7001")

    def test_init_options(self, mocker):
        constructor = mocker.spy(rediscluster, "RedisCluster")
        assert storage_from_string(self.storage_url, socket_timeout=1).check()
        assert constructor.call_args[1]["socket_timeout"] == 1
