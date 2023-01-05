import time

import pytest

from limits import RateLimitItemPerMinute
from limits.errors import ConfigurationError
from limits.storage import (
    EtcdStorage,
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
        "uri, args", [("blah://", {}), ("redis+sentinel://localhost:26379", {})]
    )
    def test_invalid_storage_string(self, uri, args):
        with pytest.raises(ConfigurationError):
            storage_from_string(uri, **args)

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


@pytest.mark.parametrize(
    "uri, args, expected_instance, fixture",
    [
        ("memory://", {}, MemoryStorage, None),
        pytest.param(
            "redis://localhost:7379",
            {},
            RedisStorage,
            pytest.lazy_fixture("redis_basic"),
            marks=pytest.mark.redis,
        ),
        pytest.param(
            "redis+unix:///tmp/limits.redis.sock",
            {},
            RedisStorage,
            pytest.lazy_fixture("redis_uds"),
            marks=pytest.mark.redis,
        ),
        pytest.param(
            "redis+unix://:password/tmp/limits.redis.sock",
            {},
            RedisStorage,
            pytest.lazy_fixture("redis_uds"),
            marks=pytest.mark.redis,
        ),
        pytest.param(
            "memcached://localhost:22122",
            {},
            MemcachedStorage,
            pytest.lazy_fixture("memcached"),
            marks=pytest.mark.memcached,
        ),
        pytest.param(
            "memcached://localhost:22122,localhost:22123",
            {},
            MemcachedStorage,
            pytest.lazy_fixture("memcached_cluster"),
            marks=pytest.mark.memcached,
        ),
        pytest.param(
            "memcached:///tmp/limits.memcached.sock",
            {},
            MemcachedStorage,
            pytest.lazy_fixture("memcached_uds"),
            marks=pytest.mark.memcached,
        ),
        pytest.param(
            "redis+sentinel://localhost:26379",
            {"service_name": "mymaster"},
            RedisSentinelStorage,
            pytest.lazy_fixture("redis_sentinel"),
            marks=pytest.mark.redis_sentinel,
        ),
        pytest.param(
            "redis+sentinel://localhost:26379/mymaster",
            {},
            RedisSentinelStorage,
            pytest.lazy_fixture("redis_sentinel"),
            marks=pytest.mark.redis_sentinel,
        ),
        pytest.param(
            "redis+sentinel://:sekret@localhost:36379/mymaster",
            {"password": "sekret"},
            RedisSentinelStorage,
            pytest.lazy_fixture("redis_sentinel_auth"),
            marks=pytest.mark.redis_sentinel,
        ),
        pytest.param(
            "redis+cluster://localhost:7001/",
            {},
            RedisClusterStorage,
            pytest.lazy_fixture("redis_cluster"),
            marks=pytest.mark.redis_cluster,
        ),
        pytest.param(
            "mongodb://localhost:37017/",
            {},
            MongoDBStorage,
            pytest.lazy_fixture("mongodb"),
            marks=pytest.mark.mongodb,
        ),
        pytest.param(
            "etcd://localhost:2379",
            {},
            EtcdStorage,
            pytest.lazy_fixture("etcd"),
            marks=pytest.mark.etcd,
        ),
    ],
)
class TestConcreteStorages:
    def test_storage_string(self, uri, args, expected_instance, fixture):
        assert isinstance(storage_from_string(uri, **args), expected_instance)

    def test_storage_check(self, uri, args, expected_instance, fixture):
        assert storage_from_string(uri, **args).check()

    def test_storage_reset(self, uri, args, expected_instance, fixture):
        if expected_instance == MemcachedStorage:
            pytest.skip("Reset not supported for memcached")
        limit = RateLimitItemPerMinute(10)
        storage = storage_from_string(uri, **args)
        for i in range(10):
            storage.incr(limit.key_for(str(i)), limit.get_expiry())
        assert storage.reset() == 10

    def test_storage_clear(self, uri, args, expected_instance, fixture):
        limit = RateLimitItemPerMinute(10)
        storage = storage_from_string(uri, **args)
        storage.incr(limit.key_for(), limit.get_expiry())
        assert 1 == storage.get(limit.key_for())
        storage.clear(limit.key_for())
        assert 0 == storage.get(limit.key_for())
