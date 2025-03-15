from __future__ import annotations

import asyncio
import random
import threading
import time
from uuid import uuid4

import pytest

import limits.aio.storage.memory
import limits.aio.strategies
import limits.strategies
from limits.limits import RateLimitItemPerMinute
from limits.storage import storage_from_string
from limits.storage.base import TimestampedSlidingWindow
from tests.utils import (
    all_storage,
    async_all_storage,
    async_moving_window_storage,
    async_sliding_window_counter_storage,
    moving_window_storage,
    sliding_window_counter_storage,
    timestamp_based_key_ttl,
)


@pytest.mark.integration
class TestConcurrency:
    CONCURRENT_REQUESTS: int = 100

    @all_storage
    def test_fixed_window(self, uri, args, fixture):
        storage = storage_from_string(uri, **args)
        limiter = limits.strategies.FixedWindowRateLimiter(storage)
        limit = RateLimitItemPerMinute(5)

        [limiter.hit(limit, uuid4().hex) for _ in range(self.CONCURRENT_REQUESTS)]

        key = uuid4().hex
        hits = []

        def hit():
            time.sleep(random.random() / 1000)
            if limiter.hit(limit, key):
                hits.append(None)

        threads = [
            threading.Thread(target=hit) for _ in range(self.CONCURRENT_REQUESTS)
        ]
        [t.start() for t in threads]
        [t.join() for t in threads]

        assert len(hits) == 5

    @sliding_window_counter_storage
    def test_sliding_window_counter(self, uri, args, fixture):
        storage = storage_from_string(uri, **args)
        limiter = limits.strategies.SlidingWindowCounterRateLimiter(storage)
        limit = RateLimitItemPerMinute(5)

        [limiter.hit(limit, uuid4().hex) for _ in range(self.CONCURRENT_REQUESTS)]

        key = uuid4().hex
        hits = []

        def hit():
            time.sleep(random.random() / 1000)
            if limiter.hit(limit, key):
                hits.append(None)

        threads = [
            threading.Thread(target=hit) for _ in range(self.CONCURRENT_REQUESTS)
        ]
        [t.start() for t in threads]
        [t.join() for t in threads]

        assert len(hits) == 5

    @moving_window_storage
    def test_moving_window(self, uri, args, fixture):
        storage = storage_from_string(uri, **args)
        limiter = limits.strategies.MovingWindowRateLimiter(storage)
        limit = RateLimitItemPerMinute(5)

        [limiter.hit(limit, uuid4().hex) for _ in range(self.CONCURRENT_REQUESTS)]

        key = uuid4().hex
        hits = []

        def hit():
            time.sleep(random.random() / 1000)
            if limiter.hit(limit, key):
                hits.append(None)

        threads = [
            threading.Thread(target=hit) for _ in range(self.CONCURRENT_REQUESTS)
        ]
        [t.start() for t in threads]
        [t.join() for t in threads]

        assert len(hits) == 5


@pytest.mark.asyncio
@pytest.mark.integration
class TestAsyncConcurrency:
    CONCURRENT_REQUESTS: int = 100

    @async_all_storage
    async def test_fixed_window(self, uri, args, fixture):
        storage = storage_from_string(uri, **args)
        limiter = limits.aio.strategies.FixedWindowRateLimiter(storage)
        limit = RateLimitItemPerMinute(5)

        [await limiter.hit(limit, uuid4().hex) for _ in range(self.CONCURRENT_REQUESTS)]

        key = uuid4().hex
        hits = []

        async def hit():
            await asyncio.sleep(random.random() / 1000)
            if await limiter.hit(limit, key):
                hits.append(None)

        await asyncio.gather(*[hit() for _ in range(self.CONCURRENT_REQUESTS)])

        assert len(hits) == 5

    @async_sliding_window_counter_storage
    async def test_sliding_window_counter(self, uri, args, fixture):
        storage = storage_from_string(uri, **args)
        limiter = limits.aio.strategies.SlidingWindowCounterRateLimiter(storage)
        limit = RateLimitItemPerMinute(5)
        if isinstance(storage, TimestampedSlidingWindow):
            # Avoid testing the behaviour when the window is about to be reset
            ttl = timestamp_based_key_ttl(limit)
            if ttl < 1:
                time.sleep(ttl)

        key = uuid4().hex
        hits = []

        async def hit():
            await asyncio.sleep(random.random() / 1000)
            if await limiter.hit(limit, key):
                hits.append(None)

        await asyncio.gather(*[hit() for _ in range(self.CONCURRENT_REQUESTS)])

        assert len(hits) == 5

    @async_moving_window_storage
    async def test_moving_window(self, uri, args, fixture):
        storage = storage_from_string(uri, **args)
        limiter = limits.aio.strategies.MovingWindowRateLimiter(storage)
        limit = RateLimitItemPerMinute(5)

        [await limiter.hit(limit, uuid4().hex) for _ in range(self.CONCURRENT_REQUESTS)]

        key = uuid4().hex
        hits = []

        async def hit():
            await asyncio.sleep(random.random() / 1000)
            if await limiter.hit(limit, key):
                hits.append(None)

        await asyncio.gather(*[hit() for _ in range(self.CONCURRENT_REQUESTS)])

        assert len(hits) == 5
