import asyncio
import datetime
import time

import pytest

from limits import RateLimitItemPerMinute, RateLimitItemPerSecond
from limits.aio.storage import MongoDBStorage
from limits.aio.strategies import FixedWindowRateLimiter, MovingWindowRateLimiter
from limits.storage import storage_from_string


@pytest.mark.asynchronous
@pytest.mark.mongodb
class TestAsyncMongoDBStorage:
    @pytest.fixture(autouse=True)
    def setup(self, mongodb):
        self.storage_url = "mongodb://localhost:37017"
        self.storage = MongoDBStorage(f"async+{self.storage_url}")

    @pytest.mark.asyncio
    async def test_init_options(self, mocker):
        import motor.motor_asyncio

        constructor = mocker.spy(motor.motor_asyncio, "AsyncIOMotorClient")
        assert await storage_from_string(
            f"async+{self.storage_url}", socketTimeoutMS=100
        ).check()
        assert constructor.call_args[1]["socketTimeoutMS"] == 100

    @pytest.mark.asyncio
    async def test_fixed_window(self):
        limiter = FixedWindowRateLimiter(self.storage)
        per_second = RateLimitItemPerSecond(10)
        start = time.time()
        count = 0

        while time.time() - start < 0.5 and count < 10:
            assert await limiter.hit(per_second)
            count += 1
        assert not await limiter.hit(per_second)

        while time.time() - start <= 1:
            await asyncio.sleep(0.1)
        for _ in range(10):
            assert await limiter.hit(per_second)

    @pytest.mark.asyncio
    async def test_reset(self):
        limiter = FixedWindowRateLimiter(self.storage)

        for i in range(0, 10):
            rate = RateLimitItemPerMinute(i)
            await limiter.hit(rate)
        assert await self.storage.reset() == 10

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
    async def test_moving_window_expiry(self):
        limiter = MovingWindowRateLimiter(self.storage)
        limit = RateLimitItemPerSecond(2)
        assert await limiter.hit(limit)
        await asyncio.sleep(0.9)
        assert await limiter.hit(limit)
        assert not await limiter.hit(limit)
        await asyncio.sleep(0.1)
        assert await limiter.hit(limit)
        last = time.time()

        while time.time() - last <= 1:
            await asyncio.sleep(0.05)

        assert [] == (
            await self.storage.storage.limits.windows.find(
                {"expireAt": {"$gt": datetime.datetime.utcnow()}}
            ).to_list(1)
        )
