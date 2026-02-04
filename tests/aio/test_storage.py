from __future__ import annotations

import time

import pytest
from pytest_lazy_fixtures import lf

from limits import RateLimitItemPerMinute, RateLimitItemPerSecond
from limits.aio.storage import (
    MemcachedStorage,
    MemoryStorage,
    MongoDBStorage,
    MovingWindowSupport,
    RedisClusterStorage,
    RedisSentinelStorage,
    RedisStorage,
    SlidingWindowCounterSupport,
    Storage,
)
from limits.aio.strategies import (
    MovingWindowRateLimiter,
    SlidingWindowCounterRateLimiter,
)
from limits.errors import StorageError
from limits.storage import storage_from_string
from tests.utils import async_fixed_start


@pytest.mark.asyncio
class TestBaseStorage:
    async def test_pluggable_storage_fixed_only(self):
        class MyStorage(Storage):
            STORAGE_SCHEME = ["async+mystorage+fixed"]

            @property
            def base_exceptions(self):
                return ValueError

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

        storage = storage_from_string("async+mystorage+fixed://")
        assert isinstance(storage, MyStorage)
        with pytest.raises(NotImplementedError):
            MovingWindowRateLimiter(storage)
        with pytest.raises(NotImplementedError):
            SlidingWindowCounterRateLimiter(storage)

    async def test_pluggable_storage_moving_window(self):
        class MyStorage(Storage):
            STORAGE_SCHEME = ["async+mystorage+moving"]

            @property
            def base_exceptions(self):
                return ValueError

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

        storage = storage_from_string("async+mystorage+moving://")
        assert isinstance(storage, MyStorage)
        MovingWindowRateLimiter(storage)

    async def test_pluggable_storage_sliding_window_counter(self):
        class MyStorage(Storage, SlidingWindowCounterSupport):
            STORAGE_SCHEME = ["async+mystorage+sliding"]

            @property
            def base_exceptions(self):
                return ValueError

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

            async def acquire_sliding_window_entry(
                self, key: str, limit: int, expiry: int, amount: int = 1
            ) -> bool:
                pass

            async def get_sliding_window(
                self, key: str, expiry: int
            ) -> tuple[int, float, int, float]:
                pass

            async def clear_sliding_window(self, key: str, expiry: int) -> None:
                pass

        storage = storage_from_string("async+mystorage+sliding://")
        assert isinstance(storage, MyStorage)
        SlidingWindowCounterRateLimiter(storage)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "uri, args, expected_instance, fixture",
    [
        pytest.param(
            "async+memory://",
            {},
            MemoryStorage,
            None,
            marks=pytest.mark.memory,
            id="in-memory",
        ),
        pytest.param(
            "async+redis://localhost:7379",
            {},
            RedisStorage,
            lf("redis_basic"),
            marks=pytest.mark.redis,
            id="redis",
        ),
        pytest.param(
            "async+redis+unix:///tmp/limits.redis.sock",
            {},
            RedisStorage,
            lf("redis_uds"),
            marks=pytest.mark.redis,
            id="redis-uds",
        ),
        pytest.param(
            "async+memcached://localhost:22122",
            {},
            MemcachedStorage,
            lf("memcached"),
            marks=pytest.mark.memcached,
            id="memcached",
        ),
        pytest.param(
            "async+memcached://localhost:22122,localhost:22123",
            {},
            MemcachedStorage,
            lf("memcached_cluster"),
            marks=pytest.mark.memcached,
            id="memcached-cluster",
        ),
        pytest.param(
            "async+redis+sentinel://localhost:26379",
            {"service_name": "mymaster"},
            RedisSentinelStorage,
            lf("redis_sentinel"),
            marks=pytest.mark.redis_sentinel,
            id="redis-sentinel",
        ),
        pytest.param(
            "async+redis+sentinel://localhost:26379/mymaster",
            {},
            RedisSentinelStorage,
            lf("redis_sentinel"),
            marks=pytest.mark.redis_sentinel,
            id="redis-sentinel-service-name-url",
        ),
        pytest.param(
            "async+redis+sentinel://:sekret@localhost:36379/mymaster",
            {"password": "sekret"},
            RedisSentinelStorage,
            lf("redis_sentinel_auth"),
            marks=pytest.mark.redis_sentinel,
            id="redis-sentinel-auth",
        ),
        pytest.param(
            "async+redis+cluster://localhost:7001/",
            {},
            RedisClusterStorage,
            lf("redis_cluster"),
            marks=pytest.mark.redis_cluster,
            id="redis-cluster",
        ),
        pytest.param(
            "async+redis+cluster://localhost:8400/",
            {"password": "sekret"},
            RedisClusterStorage,
            lf("redis_auth_cluster"),
            marks=pytest.mark.redis_cluster,
            id="redis-cluster-auth-password-from-param",
        ),
        pytest.param(
            "async+mongodb://localhost:37017/",
            {},
            MongoDBStorage,
            lf("mongodb"),
            marks=pytest.mark.mongodb,
            id="mongodb",
        ),
    ],
)
class TestConcreteStorages:
    async def test_storage_string(self, uri, args, expected_instance, fixture):
        storage = storage_from_string(uri, **args)
        assert isinstance(storage, expected_instance)
        assert await storage.check()

    @async_fixed_start
    async def test_expiry_incr(self, uri, args, expected_instance, fixture):
        storage = storage_from_string(uri, **args)
        limit = RateLimitItemPerSecond(1)
        await storage.incr(limit.key_for(), limit.get_expiry())
        time.sleep(1.1)
        assert await storage.get(limit.key_for()) == 0

    @async_fixed_start
    async def test_expiry_acquire_entry(self, uri, args, expected_instance, fixture):
        if not issubclass(expected_instance, MovingWindowSupport):
            pytest.skip(f"{expected_instance} does not support acquire entry")
        storage = storage_from_string(uri, **args)
        limit = RateLimitItemPerSecond(1)
        assert await storage.acquire_entry(
            limit.key_for(), limit.amount, limit.get_expiry()
        )
        time.sleep(1.1)
        assert await storage.get(limit.key_for()) == 0

    @async_fixed_start
    async def test_expiry_acquire_sliding_window_entry(
        self, uri, args, expected_instance, fixture
    ):
        if not issubclass(expected_instance, SlidingWindowCounterSupport):
            pytest.skip(f"{expected_instance} does not support acquire entry")
        storage = storage_from_string(uri, **args)
        limit = RateLimitItemPerSecond(1)
        assert await storage.acquire_sliding_window_entry(
            limit.key_for(), limit.amount, limit.get_expiry()
        )
        assert (await storage.get_sliding_window(limit.key_for(), limit.get_expiry()))[
            -1
        ] == pytest.approx(2, abs=1e2)

    async def test_incr_custom_amount(self, uri, args, expected_instance, fixture):
        storage = storage_from_string(uri, **args)
        limit = RateLimitItemPerMinute(1)
        assert 1 == await storage.incr(limit.key_for(), limit.get_expiry(), amount=1)
        assert 11 == await storage.incr(limit.key_for(), limit.get_expiry(), amount=10)

    async def test_acquire_entry_custom_amount(
        self, uri, args, expected_instance, fixture
    ):
        if not issubclass(expected_instance, MovingWindowSupport):
            pytest.skip(f"{expected_instance} does not support acquire entry")
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
        assert await storage_from_string(uri, **args).check()

    async def test_storage_reset(self, uri, args, expected_instance, fixture):
        if expected_instance == MemcachedStorage:
            pytest.skip("Reset not supported for memcached")
        limit1 = RateLimitItemPerMinute(10)  # default namespace, LIMITER
        limit2 = RateLimitItemPerMinute(10, namespace="OTHER")
        storage = storage_from_string(uri, **args)
        for i in range(10):
            await storage.incr(limit1.key_for(str(i)), limit1.get_expiry())
            await storage.incr(limit2.key_for(str(i)), limit2.get_expiry())
        assert await storage.reset() == 20

    async def test_storage_clear(self, uri, args, expected_instance, fixture):
        limit = RateLimitItemPerMinute(10)
        storage = storage_from_string(uri, **args)
        await storage.incr(limit.key_for(), limit.get_expiry())
        assert 1 == await storage.get(limit.key_for())
        await storage.clear(limit.key_for())
        assert 0 == await storage.get(limit.key_for())


@pytest.mark.asyncio
@pytest.mark.parametrize("wrap_exceptions", (True, False))
class TestStorageErrors:
    class MyStorage(Storage, MovingWindowSupport, SlidingWindowCounterSupport):
        STORAGE_SCHEME = ["mystorage"]

        class MyError(Exception):
            pass

        @property
        def base_exceptions(self):
            return self.MyError

        async def incr(self, key, expiry, elastic_expiry=False, amount=1):
            raise self.MyError()

        async def get(self, key):
            raise self.MyError()

        async def get_expiry(self, key):
            raise self.MyError()

        async def reset(self):
            raise self.MyError()

        async def check(self):
            raise self.MyError()

        async def clear(self, key):
            raise self.MyError()

        async def acquire_entry(self, key, limit, expiry, amount=1):
            raise self.MyError()

        async def get_moving_window(self, key, limit, expiry):
            raise self.MyError()

        async def acquire_sliding_window_entry(
            self, key: str, limit: int, expiry: int, amount: int = 1
        ) -> bool:
            raise self.MyError()

        async def get_sliding_window(
            self, key: str, expiry: int
        ) -> tuple[int, float, int, float]:
            raise self.MyError()

        async def clear_sliding_window(self, key: str, expiry: int) -> None:
            raise self.MyError()

    def assert_exception(self, exc, wrap_exceptions):
        if wrap_exceptions:
            assert isinstance(exc, StorageError)
            assert isinstance(exc.storage_error, self.MyStorage.MyError)
        else:
            assert isinstance(exc, self.MyStorage.MyError)

    async def test_incr_exception(self, wrap_exceptions):
        with pytest.raises(Exception) as exc:
            await self.MyStorage(wrap_exceptions=wrap_exceptions).incr("", 1)

        self.assert_exception(exc.value, wrap_exceptions)

    async def test_get_exception(self, wrap_exceptions):
        with pytest.raises(Exception) as exc:
            await self.MyStorage(wrap_exceptions=wrap_exceptions).get("")

        self.assert_exception(exc.value, wrap_exceptions)

    async def test_get_expiry_exception(self, wrap_exceptions):
        with pytest.raises(Exception) as exc:
            await self.MyStorage(wrap_exceptions=wrap_exceptions).get_expiry("")

        self.assert_exception(exc.value, wrap_exceptions)

    async def test_reset_exception(self, wrap_exceptions):
        with pytest.raises(Exception) as exc:
            await self.MyStorage(wrap_exceptions=wrap_exceptions).reset()

        self.assert_exception(exc.value, wrap_exceptions)

    async def test_check_exception(self, wrap_exceptions):
        with pytest.raises(Exception) as exc:
            await self.MyStorage(wrap_exceptions=wrap_exceptions).check()

        self.assert_exception(exc.value, wrap_exceptions)

    async def test_clear_exception(self, wrap_exceptions):
        with pytest.raises(Exception) as exc:
            await self.MyStorage(wrap_exceptions=wrap_exceptions).clear("")

        self.assert_exception(exc.value, wrap_exceptions)

    async def test_acquire_entry_exception(self, wrap_exceptions):
        with pytest.raises(Exception) as exc:
            await self.MyStorage(wrap_exceptions=wrap_exceptions).acquire_entry(
                "", 1, 1
            )

        self.assert_exception(exc.value, wrap_exceptions)

    async def test_get_moving_window_exception(self, wrap_exceptions):
        with pytest.raises(Exception) as exc:
            await self.MyStorage(wrap_exceptions=wrap_exceptions).get_moving_window(
                "", 1, 1
            )

        self.assert_exception(exc.value, wrap_exceptions)

    async def test_acquire_sliding_window_entry_exception(self, wrap_exceptions):
        with pytest.raises(Exception) as exc:
            await self.MyStorage(
                wrap_exceptions=wrap_exceptions
            ).acquire_sliding_window_entry("", 1, 1)

        self.assert_exception(exc.value, wrap_exceptions)

    async def test_get_sliding_window_exception(self, wrap_exceptions):
        with pytest.raises(Exception) as exc:
            await self.MyStorage(wrap_exceptions=wrap_exceptions).get_sliding_window(
                "", 1
            )

        self.assert_exception(exc.value, wrap_exceptions)

    async def test_clear_sliding_window_exception(self, wrap_exceptions):
        with pytest.raises(Exception) as exc:
            await self.MyStorage(wrap_exceptions=wrap_exceptions).clear_sliding_window(
                "", 1
            )

        self.assert_exception(exc.value, wrap_exceptions)
