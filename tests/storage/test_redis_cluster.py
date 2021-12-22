import rediscluster

from limits.storage import RedisClusterStorage, storage_from_string
from tests.storage.test_redis import SharedRedisTests


class TestRedisClusterStorage(SharedRedisTests):
    def setup_method(self):
        rediscluster.RedisCluster("localhost", 7000).flushall()
        self.storage_url = "redis+cluster://localhost:7000"
        self.storage = RedisClusterStorage("redis+cluster://localhost:7000")

    def test_init_options(self, mocker):
        constructor = mocker.spy(rediscluster, "RedisCluster")
        assert storage_from_string(self.storage_url, socket_timeout=1).check()
        assert constructor.call_args[1]["socket_timeout"] == 1
