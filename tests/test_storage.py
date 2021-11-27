import time

import mock
import pymemcache.client
import pytest
import redis
import redis.sentinel
import rediscluster
import unittest

from limits.errors import ConfigurationError
from limits.storage import (
    MemoryStorage,
    RedisStorage,
    MemcachedStorage,
    RedisSentinelStorage,
    RedisClusterStorage,
    Storage,
    GAEMemcachedStorage,
    storage_from_string,
)
from limits.strategies import MovingWindowRateLimiter
from tests import RUN_GAE


@pytest.mark.unit
class BaseStorageTests(unittest.TestCase):
    def setUp(self):
        pymemcache.client.Client(("localhost", 22122)).flush_all()
        redis.from_url("unix:///tmp/limits.redis.sock").flushall()
        redis.from_url("redis://localhost:7379").flushall()
        redis.from_url("redis://:sekret@localhost:7389").flushall()
        redis.sentinel.Sentinel([("localhost", 26379)]).master_for(
            "localhost-redis-sentinel"
        ).flushall()
        rediscluster.RedisCluster("localhost", 7000).flushall()
        if RUN_GAE:
            from google.appengine.ext import testbed

            tb = testbed.Testbed()
            tb.activate()
            tb.init_memcache_stub()

    def test_storage_string(self):
        self.assertTrue(isinstance(storage_from_string("memory://"), MemoryStorage))
        self.assertTrue(
            isinstance(storage_from_string("redis://localhost:7379"), RedisStorage)
        )
        self.assertTrue(
            isinstance(
                storage_from_string("redis+unix:///tmp/limits.redis.sock"), RedisStorage
            )
        )

        self.assertTrue(
            isinstance(
                storage_from_string(
                    "redis+unix://:password/tmp/limits.redis.sock"
                ),  # noqa: E501
                RedisStorage,
            )
        )

        self.assertTrue(
            isinstance(
                storage_from_string("memcached://localhost:22122"), MemcachedStorage
            )
        )

        self.assertTrue(
            isinstance(
                storage_from_string(
                    "memcached://localhost:22122,localhost:22123"
                ),  # noqa: E501
                MemcachedStorage,
            )
        )

        self.assertTrue(
            isinstance(
                storage_from_string("memcached:///tmp/limits.memcached.sock"),
                MemcachedStorage,
            )
        )

        self.assertTrue(
            isinstance(
                storage_from_string(
                    "redis+sentinel://localhost:26379",
                    service_name="localhost-redis-sentinel",
                ),
                RedisSentinelStorage,
            )
        )
        self.assertTrue(
            isinstance(
                storage_from_string(
                    "redis+sentinel://localhost:26379/localhost-redis-sentinel"
                ),
                RedisSentinelStorage,
            )
        )
        self.assertTrue(
            isinstance(
                storage_from_string("redis+cluster://localhost:7000/"),
                RedisClusterStorage,
            )
        )
        if RUN_GAE:
            self.assertTrue(
                isinstance(storage_from_string("gaememcached://"), GAEMemcachedStorage)
            )
        self.assertRaises(ConfigurationError, storage_from_string, "blah://")
        self.assertRaises(
            ConfigurationError, storage_from_string, "redis+sentinel://localhost:26379"
        )
        with mock.patch(
            "limits.storage.redis_sentinel.get_dependency"
        ) as get_dependency:
            self.assertTrue(
                isinstance(
                    storage_from_string(
                        "redis+sentinel://:foobared@localhost:26379/localhost-redis-sentinel"
                    ),  # noqa: E501
                    RedisSentinelStorage,
                )
            )
            self.assertEqual(
                get_dependency().Sentinel.call_args[1]["password"], "foobared"
            )

    def test_storage_check(self):
        self.assertTrue(storage_from_string("memory://").check())
        self.assertTrue(storage_from_string("redis://localhost:7379").check())
        self.assertTrue(storage_from_string("redis://:sekret@localhost:7389").check())
        self.assertTrue(
            storage_from_string("redis+unix:///tmp/limits.redis.sock").check()
        )
        self.assertTrue(storage_from_string("memcached://localhost:22122").check())
        self.assertTrue(
            storage_from_string("memcached://localhost:22122,localhost:22123").check()
        )
        self.assertTrue(
            storage_from_string("memcached:///tmp/limits.memcached.sock").check()
        )
        self.assertTrue(
            storage_from_string(
                "redis+sentinel://localhost:26379",
                service_name="localhost-redis-sentinel",
            ).check()
        )
        self.assertTrue(storage_from_string("redis+cluster://localhost:7000").check())
        if RUN_GAE:
            self.assertTrue(storage_from_string("gaememcached://").check())

    def test_pluggable_storage_invalid_construction(self):
        def cons():
            class _(Storage):
                def incr(self, key, expiry, elastic_expiry=False):
                    return

                def get(self, key):
                    return 0

                def get_expiry(self, key):
                    return time.time()

        self.assertRaises(ConfigurationError, cons)

    def test_pluggable_storage_no_moving_window(self):
        class MyStorage(Storage):
            STORAGE_SCHEME = ["mystorage"]

            def incr(self, key, expiry, elastic_expiry=False):
                return

            def get(self, key):
                return 0

            def get_expiry(self, key):
                return time.time()

        storage = storage_from_string("mystorage://")
        self.assertTrue(isinstance(storage, MyStorage))
        self.assertRaises(NotImplementedError, MovingWindowRateLimiter, storage)

    def test_pluggable_storage_moving_window(self):
        class MyStorage(Storage):
            STORAGE_SCHEME = ["mystorage"]

            def incr(self, key, expiry, elastic_expiry=False):
                return

            def get(self, key):
                return 0

            def get_expiry(self, key):
                return time.time()

            def acquire_entry(self, *a, **k):
                return True

            def get_moving_window(self, *a, **k):
                return (time.time(), 1)

        storage = storage_from_string("mystorage://")
        self.assertTrue(isinstance(storage, MyStorage))
        MovingWindowRateLimiter(storage)
