import datetime
import asyncio
import time

import pytest
import pymongo

from limits import RateLimitItemPerSecond, RateLimitItemPerMinute
from limits.storage import storage_from_string
from limits.aio.storage import MongoDBStorage
from limits.aio.strategies import FixedWindowRateLimiter, MovingWindowRateLimiter


@pytest.mark.asynchronous
class TestAsyncMongoDBStorage:
    def setup_method(self):
        self.storage_url = "mongodb://localhost:37017"
        self.storage = MongoDBStorage(f"async+{self.storage_url}")
        pymongo.MongoClient(self.storage_url).limits.windows.drop()
        pymongo.MongoClient(self.storage_url).limits.counters.drop()

    @pytest.mark.asyncio
    async def test_init_options(self, mocker):
        lib = mocker.Mock()
        server_info_response = asyncio.Future()
        server_info_response.set_result({})
        lib.AsyncIOMotorClient.return_value.server_info.return_value = (
            server_info_response
        )
        mocker.patch("limits.aio.storage.base.get_dependency", return_value=lib)
        assert await storage_from_string(
            f"async+{self.storage_url}", connectTimeoutMS=1
        ).check()
        assert lib.AsyncIOMotorClient.call_args[1]["connectTimeoutMS"] == 1

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
