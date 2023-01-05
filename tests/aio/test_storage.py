import time

import pytest

from limits.errors import ConfigurationError
from limits.aio.storage import (
    EtcdStorage,
    MemcachedStorage,
    MemoryStorage,
    MongoDBStorage,
    RedisClusterStorage,
    RedisSentinelStorage,
    RedisStorage,
    Storage,
)
from limits.storage import storage_from_string
from limits.aio.strategies import MovingWindowRateLimiter


@pytest.mark.asyncio
class TestBaseStorage:
    def test_pluggable_storage_no_moving_window(self):
        class MyStorage(Storage):
            STORAGE_SCHEME = ["async+mystorage"]

            async def incr(self, key, expiry, elastic_expiry=False):
                return

            async def get(self, key):
                return 0

            async def get_expiry(self, key):
                return time.time()

            async def reset(self):
                return

            async def check(self):
                return

            async def clear(self):
                return

        storage = storage_from_string("async+mystorage://")
        assert isinstance(storage, MyStorage)
        with pytest.raises(NotImplementedError):
            MovingWindowRateLimiter(storage)

    def test_pluggable_storage_moving_window(self):
        class MyStorage(Storage):
            STORAGE_SCHEME = ["async+mystorage"]

            async def incr(self, key, expiry, elastic_expiry=False):
                return

            async def get(self, key):
                return 0

            async def get_expiry(self, key):
                return time.time()

            async def reset(self):
                return

            async def check(self):
                return

            async def clear(self):
                return

            async def acquire_entry(self, *a, **k):
                return True

            async def get_moving_window(self, *a, **k):
                return (time.time(), 1)

        storage = storage_from_string("async+mystorage://")
        assert isinstance(storage, MyStorage)
        MovingWindowRateLimiter(storage)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "uri, args, expected_instance, fixture",
    [
        ("async+memory://", {}, MemoryStorage, None),
        pytest.param(
            "async+redis://localhost:7379",
            {},
            RedisStorage,
            pytest.lazy_fixture("redis_basic"),
            marks=pytest.mark.redis,
        ),
        pytest.param(
            "async+redis+unix:///tmp/limits.redis.sock",
            {},
            RedisStorage,
            pytest.lazy_fixture("redis_uds"),
            marks=pytest.mark.redis,
        ),
        pytest.param(
            "async+redis+unix://:password/tmp/limits.redis.sock",
            {},
            RedisStorage,
            pytest.lazy_fixture("redis_uds"),
            marks=pytest.mark.redis,
        ),
        pytest.param(
            "async+memcached://localhost:22122",
            {},
            MemcachedStorage,
            pytest.lazy_fixture("memcached"),
            marks=pytest.mark.memcached,
        ),
        pytest.param(
            "async+memcached://localhost:22122,localhost:22123",
            {},
            MemcachedStorage,
            pytest.lazy_fixture("memcached_cluster"),
            marks=pytest.mark.memcached,
        ),
        pytest.param(
            "async+memcached:///tmp/limits.memcached.sock",
            {},
            MemcachedStorage,
            pytest.lazy_fixture("memcached_uds"),
            marks=pytest.mark.memcached,
        ),
        pytest.param(
            "async+redis+sentinel://localhost:26379",
            {"service_name": "mymaster"},
            RedisSentinelStorage,
            pytest.lazy_fixture("redis_sentinel"),
            marks=pytest.mark.redis_sentinel,
        ),
        pytest.param(
            "async+redis+sentinel://localhost:26379/mymaster",
            {},
            RedisSentinelStorage,
            pytest.lazy_fixture("redis_sentinel"),
            marks=pytest.mark.redis_sentinel,
        ),
        pytest.param(
            "async+redis+sentinel://:sekret@localhost:36379/mymaster",
            {"password": "sekret"},
            RedisSentinelStorage,
            pytest.lazy_fixture("redis_sentinel_auth"),
            marks=pytest.mark.redis_sentinel,
        ),
        pytest.param(
            "async+redis+cluster://localhost:7001/",
            {},
            RedisClusterStorage,
            pytest.lazy_fixture("redis_cluster"),
            marks=pytest.mark.redis_cluster,
        ),
        pytest.param(
            "async+mongodb://localhost:37017/",
            {},
            MongoDBStorage,
            pytest.lazy_fixture("mongodb"),
            marks=pytest.mark.mongodb,
        ),
        pytest.param(
            "async+etcd://localhost:2379",
            {},
            EtcdStorage,
            pytest.lazy_fixture("etcd"),
            marks=pytest.mark.etcd,
        ),
    ],
)
class TestConcreteStorages:
    async def test_storage_string(self, uri, args, expected_instance, fixture):
        assert isinstance(storage_from_string(uri, **args), expected_instance)

    async def test_storage_check(self, uri, args, expected_instance, fixture):
        assert await (storage_from_string(uri, **args)).check()
