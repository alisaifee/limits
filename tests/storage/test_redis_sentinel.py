import unittest

import mock
import redis.sentinel

from limits.storage import RedisSentinelStorage, storage_from_string
from tests.storage.test_redis import SharedRedisTests


class RedisSentinelStorageTests(SharedRedisTests, unittest.TestCase):
    def setUp(self):
        self.storage_url = "redis+sentinel://localhost:26379"
        self.service_name = "localhost-redis-sentinel"
        self.storage = RedisSentinelStorage(
            self.storage_url, service_name=self.service_name
        )
        redis.sentinel.Sentinel([("localhost", 26379)]).master_for(
            self.service_name
        ).flushall()

    def test_init_options(self):
        with mock.patch(
            "limits.storage.redis_sentinel.get_dependency"
        ) as get_dependency:
            storage_from_string(
                self.storage_url + "/" + self.service_name, connection_timeout=1
            )
            self.assertEqual(
                get_dependency().Sentinel.call_args[1]["connection_timeout"], 1
            )
