import math
import time

import pytest

from limits.aio.storage import MemcachedStorage
from limits.aio.strategies import (
    FixedWindowElasticExpiryRateLimiter,
    FixedWindowRateLimiter,
    MovingWindowRateLimiter,
)
from limits.limits import RateLimitItemPerMinute, RateLimitItemPerSecond
from limits.storage import storage_from_string
from tests.utils import (
    async_all_storage,
    async_moving_window_storage,
    async_window,
    fixed_start,
)


@pytest.mark.asynchronous
@pytest.mark.asyncio
class TestAsyncWindow:
    @async_all_storage
    @fixed_start
    async def test_fixed_window(self, uri, args, fixture):
        storage = storage_from_string(uri, **args)
        limiter = FixedWindowRateLimiter(storage)
        limit = RateLimitItemPerSecond(10, 2)
        async with async_window(1) as (start, end):
            assert all([await limiter.hit(limit) for _ in range(0, 10)])
        assert not await limiter.hit(limit)
        assert (await limiter.get_window_stats(limit))[1] == 0
        assert (await limiter.get_window_stats(limit))[0] == start + 2

    @async_all_storage
    @fixed_start
    async def test_fixed_window_empty_stats(self, uri, args, fixture):
        storage = storage_from_string(uri, **args)
        limiter = FixedWindowRateLimiter(storage)
        limit = RateLimitItemPerSecond(10, 2)
        assert (await limiter.get_window_stats(limit))[1] == 10
        assert (await limiter.get_window_stats(limit))[0] == int(time.time())

    @async_all_storage
    @fixed_start
    async def test_fixed_window_multiple_cost(self, uri, args, fixture):
        storage = storage_from_string(uri, **args)
        limiter = FixedWindowRateLimiter(storage)
        limit = RateLimitItemPerSecond(10, 2)
        async with async_window(0) as (start, _):
            assert await limiter.hit(limit, cost=5)
            assert (await limiter.get_window_stats(limit))[1] == 5
            assert (await limiter.get_window_stats(limit))[0] == math.floor(start + 2)

    @async_all_storage
    @fixed_start
    async def test_fixed_window_with_elastic_expiry(self, uri, args, fixture):
        storage = storage_from_string(uri, **args)
        limiter = FixedWindowElasticExpiryRateLimiter(storage)
        limit = RateLimitItemPerSecond(10, 2)
        async with async_window(1) as (start, end):
            assert all([await limiter.hit(limit) for _ in range(0, 10)])
            assert not await limiter.hit(limit)
        assert (await limiter.get_window_stats(limit))[1] == 0
        assert (await limiter.get_window_stats(limit))[0] == start + 2
        async with async_window(3) as (start, end):
            assert not await limiter.hit(limit)
        assert await limiter.hit(limit)
        assert (await limiter.get_window_stats(limit))[1] == 9
        assert (await limiter.get_window_stats(limit))[0] == end + 2

    @async_all_storage
    @fixed_start
    async def test_fixed_window_with_elastic_expiry_multiple_cost(
        self, uri, args, fixture
    ):
        storage = storage_from_string(uri, **args)
        limiter = FixedWindowElasticExpiryRateLimiter(storage)
        limit = RateLimitItemPerSecond(10, 2)
        async with async_window(0) as (start, end):
            assert await limiter.hit(limit, cost=5)
        assert (await limiter.get_window_stats(limit))[1] == 5
        assert (await limiter.get_window_stats(limit))[0] == end + 2

    @async_moving_window_storage
    async def test_moving_window(self, uri, args, fixture):
        storage = storage_from_string(uri, **args)
        limiter = MovingWindowRateLimiter(storage)
        limit = RateLimitItemPerSecond(10, 2)

        # 5 hits in the first 100ms
        async with async_window(0.1):
            assert all([await limiter.hit(limit) for i in range(5)])
        # 5 hits in the last 100ms
        async with async_window(2, delay=1.8):
            assert all([await limiter.hit(limit) for i in range(5)])
            # 11th fails
            assert not await limiter.hit(limit)
        # 5 more succeed since there were only 5 in the last 2 seconds
        assert all([await limiter.hit(limit) for i in range(5)])
        assert (await limiter.get_window_stats(limit))[1] == 0
        assert (await limiter.get_window_stats(limit))[0] == int(time.time() + 2)

    @async_moving_window_storage
    async def test_moving_window_empty_stats(self, uri, args, fixture):
        storage = storage_from_string(uri, **args)
        limiter = MovingWindowRateLimiter(storage)
        limit = RateLimitItemPerSecond(10, 2)
        assert (await limiter.get_window_stats(limit))[1] == 10
        assert (await limiter.get_window_stats(limit))[0] == int(time.time() + 2)

    @async_moving_window_storage
    async def test_moving_window_multiple_cost(self, uri, args, fixture):
        storage = storage_from_string(uri, **args)
        limiter = MovingWindowRateLimiter(storage)
        limit = RateLimitItemPerSecond(10, 2)

        # 5 hits in the first 100ms
        async with async_window(0.1):
            assert await limiter.hit(limit, cost=5)
        # 5 hits in the last 100ms
        async with async_window(2, delay=1.8):
            assert all([await limiter.hit(limit) for i in range(5)])
            # 11th fails
            assert not await limiter.hit(limit)
        assert all([await limiter.hit(limit) for i in range(5)])
        assert (await limiter.get_window_stats(limit))[1] == 0
        assert (await limiter.get_window_stats(limit))[0] == int(time.time() + 2)

    @pytest.mark.memcached
    async def test_moving_window_memcached(self, memcached):
        storage = MemcachedStorage("memcached://localhost:22122")
        with pytest.raises(NotImplementedError):
            MovingWindowRateLimiter(storage)

    @async_all_storage
    @fixed_start
    @pytest.mark.flaky
    async def test_test_fixed_window(self, uri, args, fixture):
        storage = storage_from_string(uri, **args)
        limiter = FixedWindowRateLimiter(storage)
        limit = RateLimitItemPerMinute(2, 1)
        assert await limiter.hit(limit)
        assert await limiter.test(limit)
        assert await limiter.hit(limit)
        assert not await limiter.test(limit)
        assert not await limiter.hit(limit)

    @async_moving_window_storage
    async def test_test_moving_window(self, uri, args, fixture):
        storage = storage_from_string(uri, **args)
        limit = RateLimitItemPerMinute(2, 1)
        limiter = MovingWindowRateLimiter(storage)
        assert await limiter.hit(limit)
        assert await limiter.test(limit)
        assert await limiter.hit(limit)
        assert not await limiter.test(limit)
        assert not await limiter.hit(limit)
