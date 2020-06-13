import time

import mock
import pytest  # type: ignore
import redis

from limits import RateLimitItemPerSecond, RateLimitItemPerMinute
from limits._async.storage import AsyncRedisStorage, async_storage_from_string
from limits._async.strategies import (
    AsyncFixedWindowRateLimiter,
    AsyncMovingWindowRateLimiter,
)


@pytest.mark.unit
class AsyncSharedRedisTests:
    @pytest.mark.asyncio
    async def test_fixed_window(self):
        limiter = AsyncFixedWindowRateLimiter(self.storage)
        per_second = RateLimitItemPerSecond(10)
        start = time.time()
        count = 0
        while time.time() - start < 0.5 and count < 10:
            assert await limiter.hit(per_second)
            count += 1
        assert not await limiter.hit(per_second)
        while time.time() - start <= 1:
            time.sleep(0.1)
        for _ in range(10):
            assert await limiter.hit(per_second)

    @pytest.mark.asyncio
    async def test_reset(self):
        limiter = AsyncFixedWindowRateLimiter(self.storage)
        for i in range(0, 10):
            rate = RateLimitItemPerMinute(i)
            await limiter.hit(rate)
        assert await self.storage.reset() == 10

    @pytest.mark.asyncio
    async def test_fixed_window_clear(self):
        limiter = AsyncFixedWindowRateLimiter(self.storage)
        per_min = RateLimitItemPerMinute(1)
        await limiter.hit(per_min)
        assert not await limiter.hit(per_min)
        await limiter.clear(per_min)
        assert await limiter.hit(per_min)

    @pytest.mark.asyncio
    async def test_moving_window_clear(self):
        limiter = AsyncMovingWindowRateLimiter(self.storage)
        per_min = RateLimitItemPerMinute(1)
        await limiter.hit(per_min)
        assert not await limiter.hit(per_min)
        await limiter.clear(per_min)
        assert await limiter.hit(per_min)

    @pytest.mark.asyncio
    async def test_moving_window_expiry(self):
        limiter = AsyncMovingWindowRateLimiter(self.storage)
        limit = RateLimitItemPerSecond(2)
        assert await limiter.hit(limit)
        time.sleep(0.9)
        assert await limiter.hit(limit)
        assert not await limiter.hit(limit)
        time.sleep(0.1)
        assert await limiter.hit(limit)
        last = time.time()
        while time.time() - last <= 1:
            time.sleep(0.05)
        assert await self.storage.storage.keys("%s/*" % limit.namespace) == []


@pytest.mark.unit
class TestAsyncRedisStorage(AsyncSharedRedisTests):
    def setup_method(self):
        self.storage_url = "aredis://localhost:7379"
        self.storage = AsyncRedisStorage(self.storage_url)
        redis.from_url(self.storage_url).flushall()

    @pytest.mark.asyncio
    async def test_init_options(self):
        with mock.patch(
            "limits._async.storage.redis.get_dependency"
        ) as get_dependency:
            async_storage_from_string(self.storage_url, connection_timeout=1)
            assert (
                get_dependency().StrictRedis.from_url.call_args[1][
                    "connection_timeout"
                ]
                == 1
            )


@pytest.mark.unit
class TestAsyncRedisUnixSocketStorage(AsyncSharedRedisTests):
    def setup_method(self):
        self.storage_url = "aredis+unix:///tmp/limits.redis.sock"
        self.storage = AsyncRedisStorage(self.storage_url)
        redis.from_url("unix:///tmp/limits.redis.sock").flushall()

    @pytest.mark.asyncio
    async def test_init_options(self):
        with mock.patch(
            "limits._async.storage.redis.get_dependency"
        ) as get_dependency:
            async_storage_from_string(self.storage_url, connection_timeout=1)
            assert (
                get_dependency().StrictRedis.from_url.call_args[1][
                    "connection_timeout"
                ]
                == 1
            )
