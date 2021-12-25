import time

import pytest

from limits.storage import (
    MemcachedStorage,
    MemoryStorage,
    MongoDBStorage,
    RedisClusterStorage,
    RedisSentinelStorage,
    RedisStorage,
    Storage,
    storage_from_string,
)
from limits.strategies import MovingWindowRateLimiter


class TestBaseStorage:
    @pytest.mark.parametrize(
        "uri, args, expected_instance, fixture",
        [
            ("memory://", {}, MemoryStorage, None),
            (
                "redis://localhost:7379",
                {},
                RedisStorage,
                pytest.lazy_fixture("redis_basic"),
            ),
            (
                "redis+unix:///tmp/limits.redis.sock",
                {},
                RedisStorage,
                pytest.lazy_fixture("redis_uds"),
            ),
            (
                "redis+unix://:password/tmp/limits.redis.sock",
                {},
                RedisStorage,
                pytest.lazy_fixture("redis_uds"),
            ),
            (
                "memcached://localhost:22122",
                {},
                MemcachedStorage,
                pytest.lazy_fixture("memcached"),
            ),
            (
                "memcached://localhost:22122,localhost:22123",
                {},
                MemcachedStorage,
                pytest.lazy_fixture("memcached_cluster"),
            ),
            (
                "memcached:///tmp/limits.memcached.sock",
                {},
                MemcachedStorage,
                pytest.lazy_fixture("memcached_uds"),
            ),
            (
                "redis+sentinel://localhost:26379",
                {"service_name": "localhost-redis-sentinel"},
                RedisSentinelStorage,
                pytest.lazy_fixture("redis_sentinel"),
            ),
            (
                "redis+sentinel://localhost:26379/localhost-redis-sentinel",
                {},
                RedisSentinelStorage,
                pytest.lazy_fixture("redis_sentinel"),
            ),
            (
                "redis+sentinel://:sekret@localhost:26379/localhost-redis-sentinel",
                {},
                RedisSentinelStorage,
                pytest.lazy_fixture("redis_sentinel_auth"),
            ),
            (
                "redis+cluster://localhost:7001/",
                {},
                RedisClusterStorage,
                pytest.lazy_fixture("redis_cluster"),
            ),
            (
                "mongodb://localhost:37017/",
                {},
                MongoDBStorage,
                pytest.lazy_fixture("mongodb"),
            ),
        ],
    )
    def test_storage_string(self, uri, args, expected_instance, fixture):
        assert isinstance(storage_from_string(uri, **args), expected_instance)

    @pytest.mark.parametrize(
        "uri, args, fixture",
        [
            ("memory://", {}, None),
            ("redis://localhost:7379", {}, pytest.lazy_fixture("redis_basic")),
            (
                "redis+unix:///tmp/limits.redis.sock",
                {},
                pytest.lazy_fixture("redis_uds"),
            ),
            (
                "redis+unix://:password/tmp/limits.redis.sock",
                {},
                pytest.lazy_fixture("redis_uds"),
            ),
            ("memcached://localhost:22122", {}, pytest.lazy_fixture("memcached")),
            (
                "memcached://localhost:22122,localhost:22123",
                {},
                pytest.lazy_fixture("memcached_cluster"),
            ),
            (
                "memcached:///tmp/limits.memcached.sock",
                {},
                pytest.lazy_fixture("memcached_uds"),
            ),
            (
                "redis+sentinel://localhost:26379",
                {"service_name": "localhost-redis-sentinel"},
                pytest.lazy_fixture("redis_sentinel"),
            ),
            (
                "redis+sentinel://localhost:26379/localhost-redis-sentinel",
                {},
                pytest.lazy_fixture("redis_sentinel"),
            ),
            (
                "redis+sentinel://:sekret@localhost:36379/localhost-redis-sentinel",
                {},
                pytest.lazy_fixture("redis_sentinel_auth"),
            ),
            (
                "redis+cluster://localhost:7001/",
                {},
                pytest.lazy_fixture("redis_cluster"),
            ),
            ("mongodb://localhost:37017/", {}, pytest.lazy_fixture("mongodb")),
        ],
    )
    def test_storage_check(self, uri, args, fixture):
        assert storage_from_string(uri, **args).check()

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
