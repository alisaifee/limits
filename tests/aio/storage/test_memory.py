import asyncio

import hiro
import pytest

from limits import RateLimitItemPerMinute, RateLimitItemPerSecond
from limits.aio.storage import MemoryStorage
from limits.aio.strategies import (
    FixedWindowRateLimiter,
    MovingWindowRateLimiter,
)


@pytest.mark.asynchronous
class TestAsyncMemoryStorage:
    def setup_method(self, method):
        self.storage = MemoryStorage()

    @pytest.mark.asyncio
    async def test_init(self):
        assert await self.storage.check()

    @pytest.mark.asyncio
    async def test_in_memory(self):
        with hiro.Timeline().freeze() as timeline:
            limiter = FixedWindowRateLimiter(self.storage)
            per_min = RateLimitItemPerMinute(10)

            for i in range(0, 10):
                assert await limiter.hit(per_min)
            assert not await limiter.hit(per_min)
            timeline.forward(61)
            assert await limiter.hit(per_min)

    @pytest.mark.asyncio
    async def test_fixed_window_clear(self):
        limiter = FixedWindowRateLimiter(self.storage)
        per_min = RateLimitItemPerMinute(1)
        await limiter.hit(per_min)
        assert not await limiter.hit(per_min)
        await limiter.clear(per_min)
        assert await limiter.hit(per_min)

    @pytest.mark.asyncio
    async def test_moving_window_clear(self):
        limiter = MovingWindowRateLimiter(self.storage)
        per_min = RateLimitItemPerMinute(1)
        await limiter.hit(per_min)
        assert not await limiter.hit(per_min)
        await limiter.clear(per_min)
        assert await limiter.hit(per_min)

    @pytest.mark.asyncio
    async def test_reset(self):
        limiter = FixedWindowRateLimiter(self.storage)
        per_min = RateLimitItemPerMinute(10)

        for i in range(0, 10):
            assert await limiter.hit(per_min)
        assert not await limiter.hit(per_min)
        await self.storage.reset()

        for i in range(0, 10):
            assert await limiter.hit(per_min)
        assert not await limiter.hit(per_min)

    @pytest.mark.asyncio
    async def test_expiry(self):
        with hiro.Timeline().freeze() as timeline:
            limiter = FixedWindowRateLimiter(self.storage)
            per_min = RateLimitItemPerMinute(10)

            for i in range(0, 10):
                assert await limiter.hit(per_min)
            timeline.forward(60)
            # touch another key and yield
            await limiter.hit(RateLimitItemPerSecond(1))
            await asyncio.sleep(0.1)
            assert per_min.key_for() not in self.storage.storage

    @pytest.mark.asyncio
    async def test_expiry_moving_window(self):
        with hiro.Timeline().freeze() as timeline:
            limiter = MovingWindowRateLimiter(self.storage)
            per_min = RateLimitItemPerMinute(10)
            per_sec = RateLimitItemPerSecond(1)

            for _ in range(0, 2):
                for _ in range(0, 10):
                    assert await limiter.hit(per_min)
                timeline.forward(60)
                assert await limiter.hit(per_sec)
                timeline.forward(1)
                await asyncio.sleep(0.1)
                assert [] == self.storage.events[per_min.key_for()]
