import time

import pymemcache.client
import pymongo
import pytest
import redis
import redis.sentinel
import rediscluster

from limits.errors import ConfigurationError
from limits.storage import (
    MemoryStorage,
    RedisStorage,
    MemcachedStorage,
    MongoDBStorage,
    RedisSentinelStorage,
    RedisClusterStorage,
    Storage,
    storage_from_string,
)
from limits.strategies import MovingWindowRateLimiter


@pytest.mark.unit
class TestBaseStorage:
    def setup_method(self):
        pymemcache.client.Client(("localhost", 22122)).flush_all()
        redis.from_url("unix:///tmp/limits.redis.sock").flushall()
        redis.from_url("redis://localhost:7379").flushall()
        redis.from_url("redis://:sekret@localhost:7389").flushall()
        redis.sentinel.Sentinel([("localhost", 26379)]).master_for(
            "localhost-redis-sentinel"
        ).flushall()
        pymongo.MongoClient("mongodb://localhost:37017").limits.windows.drop()
        pymongo.MongoClient("mongodb://localhost:37017").limits.counters.drop()
        rediscluster.RedisCluster("localhost", 7000).flushall()

    def test_storage_string(self, mocker):
        assert isinstance(storage_from_string("memory://"), MemoryStorage)
        assert isinstance(storage_from_string("redis://localhost:7379"), RedisStorage)
        assert isinstance(
            storage_from_string("redis+unix:///tmp/limits.redis.sock"), RedisStorage
        )

        assert isinstance(
            storage_from_string("redis+unix://:password/tmp/limits.redis.sock"),
            RedisStorage,
        )

        assert isinstance(
            storage_from_string("memcached://localhost:22122"), MemcachedStorage
        )

        assert isinstance(
            storage_from_string("memcached://localhost:22122,localhost:22123"),
            MemcachedStorage,
        )

        assert isinstance(
            storage_from_string("memcached:///tmp/limits.memcached.sock"),
            MemcachedStorage,
        )

        assert isinstance(
            storage_from_string(
                "redis+sentinel://localhost:26379",
                service_name="localhost-redis-sentinel",
            ),
            RedisSentinelStorage,
        )

        assert isinstance(
            storage_from_string(
                "redis+sentinel://localhost:26379/localhost-redis-sentinel"
            ),
            RedisSentinelStorage,
        )
        assert isinstance(
            storage_from_string("redis+cluster://localhost:7000/"),
            RedisClusterStorage,
        )
        assert isinstance(
            storage_from_string("mongodb://localhost:37017/"), MongoDBStorage
        )
        with pytest.raises(ConfigurationError):
            storage_from_string("blah://")
        with pytest.raises(ConfigurationError):
            storage_from_string("redis+sentinel://localhost:26379")
        sentinel = mocker.Mock()
        mocker.patch("limits.util.get_dependency", return_value=sentinel)
        assert isinstance(
            storage_from_string(
                "redis+sentinel://:foobared@localhost:26379/localhost-redis-sentinel"
            ),
            RedisSentinelStorage,
        )
        assert (
            sentinel.Sentinel.call_args[1]["sentinel_kwargs"]["password"] == "foobared"
        )

    def test_storage_check(self):
        assert storage_from_string("memory://").check()
        assert storage_from_string("redis://localhost:7379").check()
        assert storage_from_string("redis://:sekret@localhost:7389").check()
        assert storage_from_string("redis+unix:///tmp/limits.redis.sock").check()
        assert storage_from_string("memcached://localhost:22122").check()
        assert storage_from_string(
            "memcached://localhost:22122,localhost:22123"
        ).check()
        assert storage_from_string("memcached:///tmp/limits.memcached.sock").check()
        assert storage_from_string(
            "redis+sentinel://localhost:26379",
            service_name="localhost-redis-sentinel",
        ).check()
        assert storage_from_string("redis+cluster://localhost:7000").check()
        assert storage_from_string("mongodb://localhost:37017").check()

    def test_pluggable_storage_no_moving_window(self):
        class MyStorage(Storage):
            STORAGE_SCHEME = ["mystorage"]

            def incr(self, key, expiry, elastic_expiry=False):
                return

            def get(self, key):
                return 0

            def get_expiry(self, key):
                return time.time()

            def reset(self):
                return

            def check(self):
                return

            def clear(self):
                return

        storage = storage_from_string("mystorage://")
        assert isinstance(storage, MyStorage)
        with pytest.raises(NotImplementedError):
            MovingWindowRateLimiter(storage)

    def test_pluggable_storage_moving_window(self):
        class MyStorage(Storage):
            STORAGE_SCHEME = ["mystorage"]

            def incr(self, key, expiry, elastic_expiry=False):
                return

            def get(self, key):
                return 0

            def get_expiry(self, key):
                return time.time()

            def reset(self):
                return

            def check(self):
                return

            def clear(self):
                return

            def acquire_entry(self, *a, **k):
                return True

            def get_moving_window(self, *a, **k):
                return (time.time(), 1)

        storage = storage_from_string("mystorage://")
        assert isinstance(storage, MyStorage)
        MovingWindowRateLimiter(storage)
