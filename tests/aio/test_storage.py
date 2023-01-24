import time

import pytest

from limits import RateLimitItemPerMinute, RateLimitItemPerSecond
from limits.aio.storage import (
    EtcdStorage,
    MemcachedStorage,
    MemoryStorage,
    MongoDBStorage,
    MovingWindowSupport,
    RedisClusterStorage,
    RedisSentinelStorage,
    RedisStorage,
    Storage,
)
from limits.aio.strategies import MovingWindowRateLimiter
from limits.storage import storage_from_string
from tests.utils import fixed_start


@pytest.mark.asyncio
class TestBaseStorage:
    async def test_pluggable_storage_no_moving_window(self):
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

    async def test_pluggable_storage_moving_window(self):
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
        pytest.param("async+memory://", {}, MemoryStorage, None, id="in-memory"),
        pytest.param(
            "async+redis://localhost:7379",
            {},
            RedisStorage,
            pytest.lazy_fixture("redis_basic"),
            marks=pytest.mark.redis,
            id="redis",
        ),
        pytest.param(
            "async+redis+unix:///tmp/limits.redis.sock",
            {},
            RedisStorage,
            pytest.lazy_fixture("redis_uds"),
            marks=pytest.mark.redis,
            id="redis-uds",
        ),
        pytest.param(
            "async+redis+unix://:password/tmp/limits.redis.sock",
            {},
            RedisStorage,
            pytest.lazy_fixture("redis_uds"),
            marks=pytest.mark.redis,
            id="redis-uds-auth",
        ),
        pytest.param(
            "async+memcached://localhost:22122",
            {},
            MemcachedStorage,
            pytest.lazy_fixture("memcached"),
            marks=pytest.mark.memcached,
            id="memcached",
        ),
        pytest.param(
            "async+memcached://localhost:22122,localhost:22123",
            {},
            MemcachedStorage,
            pytest.lazy_fixture("memcached_cluster"),
            marks=pytest.mark.memcached,
            id="memcached-cluster",
        ),
        pytest.param(
            "async+redis+sentinel://localhost:26379",
            {"service_name": "mymaster"},
            RedisSentinelStorage,
            pytest.lazy_fixture("redis_sentinel"),
            marks=pytest.mark.redis_sentinel,
            id="redis-sentinel",
        ),
        pytest.param(
            "async+redis+sentinel://localhost:26379/mymaster",
            {},
            RedisSentinelStorage,
            pytest.lazy_fixture("redis_sentinel"),
            marks=pytest.mark.redis_sentinel,
            id="redis-sentinel-service-name-url",
        ),
        pytest.param(
            "async+redis+sentinel://:sekret@localhost:36379/mymaster",
            {"password": "sekret"},
            RedisSentinelStorage,
            pytest.lazy_fixture("redis_sentinel_auth"),
            marks=pytest.mark.redis_sentinel,
            id="redis-sentinel-auth",
        ),
        pytest.param(
            "async+redis+cluster://localhost:7001/",
            {},
            RedisClusterStorage,
            pytest.lazy_fixture("redis_cluster"),
            marks=pytest.mark.redis_cluster,
            id="redis-cluster",
        ),
        pytest.param(
            "async+redis+cluster://:sekret@localhost:8400/",
            {},
            RedisClusterStorage,
            pytest.lazy_fixture("redis_auth_cluster"),
            marks=pytest.mark.redis_cluster,
            id="redis-cluster-auth",
        ),
        pytest.param(
            "async+mongodb://localhost:37017/",
            {},
            MongoDBStorage,
            pytest.lazy_fixture("mongodb"),
            marks=pytest.mark.mongodb,
            id="mongodb",
        ),
        pytest.param(
            "async+etcd://localhost:2379",
            {},
            EtcdStorage,
            pytest.lazy_fixture("etcd"),
            marks=pytest.mark.etcd,
            id="etcd",
        ),
    ],
)
class TestConcreteStorages:
    async def test_storage_string(self, uri, args, expected_instance, fixture):
        assert isinstance(storage_from_string(uri, **args), expected_instance)

    @fixed_start
    async def test_expiry_incr(self, uri, args, expected_instance, fixture):
        storage = storage_from_string(uri, **args)
        limit = RateLimitItemPerSecond(1)
        await storage.incr(limit.key_for(), limit.get_expiry())
        time.sleep(1.1)
        assert await storage.get(limit.key_for()) == 0

    @fixed_start
    async def test_expiry_acquire_entry(self, uri, args, expected_instance, fixture):
        if not issubclass(expected_instance, MovingWindowSupport):
            pytest.skip("%s does not support acquire entry" % expected_instance)
        storage = storage_from_string(uri, **args)
        limit = RateLimitItemPerSecond(1)
        assert await storage.acquire_entry(
            limit.key_for(), limit.amount, limit.get_expiry()
        )
        time.sleep(1.1)
        assert await storage.get(limit.key_for()) == 0

    async def test_incr_custom_amount(self, uri, args, expected_instance, fixture):
        storage = storage_from_string(uri, **args)
        limit = RateLimitItemPerMinute(1)
        assert 1 == await storage.incr(limit.key_for(), limit.get_expiry(), amount=1)
        assert 11 == await storage.incr(limit.key_for(), limit.get_expiry(), amount=10)

    async def test_acquire_entry_custom_amount(
        self, uri, args, expected_instance, fixture
    ):
        if not issubclass(expected_instance, MovingWindowSupport):
            pytest.skip("%s does not support acquire entry" % expected_instance)
        storage = storage_from_string(uri, **args)
        limit = RateLimitItemPerMinute(10)
        assert not await storage.acquire_entry(
            limit.key_for(), limit.amount, limit.get_expiry(), amount=11
        )
        assert await storage.acquire_entry(
            limit.key_for(), limit.amount, limit.get_expiry(), amount=1
        )
        assert not await storage.acquire_entry(
            limit.key_for(), limit.amount, limit.get_expiry(), amount=10
        )

    async def test_storage_check(self, uri, args, expected_instance, fixture):
        assert await (storage_from_string(uri, **args)).check()

    async def test_storage_reset(self, uri, args, expected_instance, fixture):
        if expected_instance == MemcachedStorage:
            pytest.skip("Reset not supported for memcached")
        limit = RateLimitItemPerMinute(10)
        storage = storage_from_string(uri, **args)
        for i in range(10):
            await storage.incr(limit.key_for(str(i)), limit.get_expiry())
        assert await storage.reset() == 10

    async def test_storage_clear(self, uri, args, expected_instance, fixture):
        limit = RateLimitItemPerMinute(10)
        storage = storage_from_string(uri, **args)
        await storage.incr(limit.key_for(), limit.get_expiry())
        assert 1 == await storage.get(limit.key_for())
        await storage.clear(limit.key_for())
        assert 0 == await storage.get(limit.key_for())
