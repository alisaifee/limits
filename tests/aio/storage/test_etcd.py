import asyncio
import time

import pytest

from limits import RateLimitItemPerMinute, RateLimitItemPerSecond
from limits.aio.storage import EtcdStorage
from limits.aio.strategies import FixedWindowRateLimiter


@pytest.mark.flaky
@pytest.mark.asynchronous
@pytest.mark.etcd
class TestAsyncEtcdStorage:
    @pytest.fixture(autouse=True)
    def setup(self, etcd):
        self.storage_url = "etcd://localhost:2379"
        self.storage = EtcdStorage(f"async+{self.storage_url}")

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
    async def test_clear(self):
        limiter = FixedWindowRateLimiter(self.storage)
        per_min = RateLimitItemPerMinute(1)
        await limiter.hit(per_min)
        assert not await limiter.hit(per_min)
        await limiter.clear(per_min)
        assert await limiter.hit(per_min)
