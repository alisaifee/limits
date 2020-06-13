import time
import unittest
import asyncio

import hiro
import pytest

from limits import RateLimitItemPerMinute, RateLimitItemPerSecond
from limits._async.storage import AsyncMemoryStorage
from limits._async.strategies import AsyncFixedWindowRateLimiter, AsyncMovingWindowRateLimiter


@pytest.mark.unit
class TestAsyncMemoryStorage:
    def setup_method(self, method):
        self.storage = AsyncMemoryStorage()

    @pytest.mark.asyncio
    async def test_in_memory(self):
        with hiro.Timeline().freeze() as timeline:
            limiter = AsyncFixedWindowRateLimiter(self.storage)
            per_min = RateLimitItemPerMinute(10)
            for i in range(0, 10):
                assert await limiter.hit(per_min)
            assert not await limiter.hit(per_min)
            timeline.forward(61)
            assert await limiter.hit(per_min)

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
    async def test_reset(self):
        limiter = AsyncFixedWindowRateLimiter(self.storage)
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
            limiter = AsyncFixedWindowRateLimiter(self.storage)
            per_min = RateLimitItemPerMinute(10)
            for i in range(0, 10):
                assert await limiter.hit(per_min)
            timeline.forward(60)
            # touch another key and yield
            await limiter.hit(RateLimitItemPerSecond(1))
            time.sleep(0.1)
            assert per_min.key_for() not in self.storage.storage

    @pytest.mark.asyncio
    async def test_expiry_moving_window(self):
        with hiro.Timeline().freeze() as timeline:
            limiter = AsyncMovingWindowRateLimiter(self.storage)
            per_min = RateLimitItemPerMinute(10)
            per_sec = RateLimitItemPerSecond(1)
            for _ in range(0, 2):
                for _ in range(0, 10):
                    assert await limiter.hit(per_min)
                timeline.forward(60)
                assert await limiter.hit(per_sec)
                timeline.forward(1)
                time.sleep(0.1)
                assert [] == self.storage.events[per_min.key_for()]
