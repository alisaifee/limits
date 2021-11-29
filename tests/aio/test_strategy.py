import time

import pytest
import aredis
import redis

import hiro

from limits.limits import RateLimitItemPerSecond, RateLimitItemPerMinute
from limits.aio.storage import (
    MemoryStorage,
    RedisStorage,
)
from limits.aio.strategies import (
    MovingWindowRateLimiter,
    FixedWindowElasticExpiryRateLimiter,
    FixedWindowRateLimiter,
)


@pytest.mark.asynchronous
class TestAsyncWindow:
    def setup_method(self, method):
        redis.StrictRedis.from_url("redis://localhost:7379").flushall()

    @pytest.mark.asyncio
    async def test_fixed_window(self):
        storage = MemoryStorage()
        limiter = FixedWindowRateLimiter(storage)
        with hiro.Timeline().freeze() as timeline:
            start = int(time.time())
            limit = RateLimitItemPerSecond(10, 2)
            assert all([await limiter.hit(limit) for _ in range(0, 10)])
            timeline.forward(1)
            assert not await limiter.hit(limit)
            assert (await limiter.get_window_stats(limit))[1] == 0
            assert (await limiter.get_window_stats(limit))[0] == start + 2
            timeline.forward(1)
            assert (await limiter.get_window_stats(limit))[1] == 10
            assert await limiter.hit(limit)

    @pytest.mark.asyncio
    async def test_fixed_window_with_elastic_expiry_in_memory(self):
        storage = MemoryStorage()
        limiter = FixedWindowElasticExpiryRateLimiter(storage)
        with hiro.Timeline().freeze() as timeline:
            start = int(time.time())
            limit = RateLimitItemPerSecond(10, 2)
            assert all([await limiter.hit(limit) for _ in range(0, 10)])
            timeline.forward(1)
            assert not await limiter.hit(limit)
            assert (await limiter.get_window_stats(limit))[1] == 0
            # three extensions to the expiry
            assert (await limiter.get_window_stats(limit))[0] == start + 3
            timeline.forward(1)
            assert not await limiter.hit(limit)
            timeline.forward(3)
            start = int(time.time())
            assert await limiter.hit(limit)
            assert (await limiter.get_window_stats(limit))[1] == 9
            assert (await limiter.get_window_stats(limit))[0] == start + 2

    @pytest.mark.asyncio
    async def test_fixed_window_with_elastic_expiry_redis(self):
        await aredis.StrictRedis.from_url("aredis://localhost:7379").flushall()
        storage = RedisStorage("aredis://localhost:7379")
        limiter = FixedWindowElasticExpiryRateLimiter(storage)
        limit = RateLimitItemPerSecond(10, 2)

        for _ in range(0, 10):
            assert await limiter.hit(limit)
        time.sleep(1)
        assert not await limiter.hit(limit)
        time.sleep(1)
        assert not await limiter.hit(limit)
        assert (await limiter.get_window_stats(limit))[1] == 0

    @pytest.mark.asyncio
    async def test_moving_window_in_memory(self):
        storage = MemoryStorage()
        limiter = MovingWindowRateLimiter(storage)
        with hiro.Timeline().freeze() as timeline:
            limit = RateLimitItemPerMinute(10)

            for i in range(0, 5):
                assert await limiter.hit(limit)
                assert await limiter.hit(limit)
                assert (await limiter.get_window_stats(limit))[1] == 10 - ((i + 1) * 2)
                timeline.forward(10)
            assert (await limiter.get_window_stats(limit))[1] == 0
            assert not await limiter.hit(limit)
            timeline.forward(20)
            assert (await limiter.get_window_stats(limit))[1] == 2
            assert (await limiter.get_window_stats(limit))[0] == int(time.time() + 30)
            timeline.forward(31)
            assert (await limiter.get_window_stats(limit))[1] == 10

    @pytest.mark.asyncio
    async def test_moving_window_redis(self):
        await aredis.StrictRedis.from_url("aredis://localhost:7379").flushall()
        storage = RedisStorage("aredis://localhost:7379")
        limiter = MovingWindowRateLimiter(storage)
        limit = RateLimitItemPerSecond(10, 2)

        for i in range(0, 10):
            assert await limiter.hit(limit)
            assert (await limiter.get_window_stats(limit))[1] == 10 - (i + 1)
            time.sleep(2 * 0.095)
        assert not await limiter.hit(limit)
        time.sleep(0.4)
        assert await limiter.hit(limit)
        assert await limiter.hit(limit)
        assert (await limiter.get_window_stats(limit))[1] == 0

    @pytest.mark.asyncio
    async def test_test_fixed_window(self):
        with hiro.Timeline().freeze():
            store = MemoryStorage()
            limiter = FixedWindowRateLimiter(store)
            limit = RateLimitItemPerSecond(2, 1)
            assert await limiter.hit(limit)
            assert await limiter.test(limit)
            assert await limiter.hit(limit)
            assert not await limiter.test(limit)
            assert not await limiter.hit(limit)

    @pytest.mark.asyncio
    async def test_test_moving_window(self):
        with hiro.Timeline().freeze():
            store = MemoryStorage()
            limit = RateLimitItemPerSecond(2, 1)
            limiter = MovingWindowRateLimiter(store)
            assert await limiter.hit(limit)
            assert await limiter.test(limit)
            assert await limiter.hit(limit)
            assert not await limiter.test(limit)
            assert not await limiter.hit(limit)
