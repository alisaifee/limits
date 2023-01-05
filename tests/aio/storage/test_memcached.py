import asyncio
import time

import pytest

from limits import RateLimitItemPerMinute, RateLimitItemPerSecond
from limits.aio.storage import MemcachedStorage
from limits.aio.strategies import (
    FixedWindowElasticExpiryRateLimiter,
    FixedWindowRateLimiter,
)
from limits.storage import storage_from_string
from tests.utils import fixed_start


@pytest.mark.flaky
@pytest.mark.asynchronous
@pytest.mark.memcached
class TestAsyncMemcachedStorage:
    @pytest.fixture(autouse=True)
    def setup(self, memcached, memcached_cluster):
        self.storage_url = "async+memcached://localhost:22122"

    @pytest.mark.asyncio
    async def test_check(self):
        storage = storage_from_string(self.storage_url, connection_timeout=1)
        assert await storage.check()

    @fixed_start
    @pytest.mark.asyncio
    async def test_fixed_window(self):
        storage = MemcachedStorage("async+memcached://localhost:22122")
        limiter = FixedWindowRateLimiter(storage)
        per_sec = RateLimitItemPerSecond(10)
        start = time.time()
        count = 0

        while time.time() - start < 0.5 and count < 10:
            assert await limiter.hit(per_sec)
            count += 1
        assert not await limiter.hit(per_sec)

        while time.time() - start <= 1:
            await asyncio.sleep(0.1)
        assert await limiter.hit(per_sec)

    @fixed_start
    @pytest.mark.asyncio
    async def test_fixed_window_cluster(self):
        storage = MemcachedStorage("memcached://localhost:22122,localhost:22123")
        limiter = FixedWindowRateLimiter(storage)
        per_sec = RateLimitItemPerSecond(10)
        start = time.time()
        count = 0

        while time.time() - start < 0.5 and count < 10:
            assert await limiter.hit(per_sec)
            count += 1
        assert not await limiter.hit(per_sec)

        while time.time() - start <= 1:
            await asyncio.sleep(0.1)
        assert await limiter.hit(per_sec)

    @fixed_start
    @pytest.mark.asyncio
    async def test_fixed_window_with_elastic_expiry(self):
        storage = MemcachedStorage("memcached://localhost:22122")
        limiter = FixedWindowElasticExpiryRateLimiter(storage)
        per_sec = RateLimitItemPerSecond(2, 2)

        assert await limiter.hit(per_sec)
        await asyncio.sleep(1)
        assert await limiter.hit(per_sec)
        assert not await limiter.test(per_sec)
        await asyncio.sleep(1)
        assert not await limiter.test(per_sec)
        await asyncio.sleep(1)
        assert await limiter.test(per_sec)

    @fixed_start
    @pytest.mark.asyncio
    async def test_fixed_window_with_elastic_expiry_cluster(self):
        storage = MemcachedStorage("memcached://localhost:22122,localhost:22123")
        limiter = FixedWindowElasticExpiryRateLimiter(storage)
        per_sec = RateLimitItemPerSecond(2, 2)

        assert await limiter.hit(per_sec)
        await asyncio.sleep(1)
        assert await limiter.hit(per_sec)
        assert not await limiter.test(per_sec)
        await asyncio.sleep(1)
        assert not await limiter.test(per_sec)
        await asyncio.sleep(1)
        assert await limiter.test(per_sec)

    @pytest.mark.asyncio
    async def test_clear(self):
        storage = MemcachedStorage("memcached://localhost:22122")
        limiter = FixedWindowRateLimiter(storage)
        per_min = RateLimitItemPerMinute(1)
        await limiter.hit(per_min)
        assert not await limiter.hit(per_min)
        await limiter.clear(per_min)
        assert await limiter.hit(per_min)
