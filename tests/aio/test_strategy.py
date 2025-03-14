from __future__ import annotations

import time
from math import ceil

import pytest

from limits.aio.strategies import (
    FixedWindowRateLimiter,
    MovingWindowRateLimiter,
    SlidingWindowCounterRateLimiter,
)
from limits.limits import (
    RateLimitItemPerHour,
    RateLimitItemPerMinute,
    RateLimitItemPerSecond,
)
from limits.storage import storage_from_string
from limits.storage.base import TimestampedSlidingWindow
from tests.utils import (
    async_all_storage,
    async_fixed_start,
    async_moving_window_storage,
    async_sliding_window_counter_storage,
    async_window,
    timestamp_based_key_ttl,
)


@pytest.mark.asyncio
@async_all_storage
class TestAsyncFixedWindow:
    @async_fixed_start
    async def test_fixed_window(self, uri, args, fixture):
        storage = storage_from_string(uri, **args)
        limiter = FixedWindowRateLimiter(storage)
        limit = RateLimitItemPerSecond(10, 2)
        async with async_window(1) as (start, _):
            assert all([await limiter.hit(limit) for _ in range(0, 10)])
        assert not await limiter.hit(limit)
        assert (await limiter.get_window_stats(limit)).remaining == 0
        assert (await limiter.get_window_stats(limit)).reset_time == pytest.approx(
            start + 2, 1e-2
        )

    @async_fixed_start
    async def test_fixed_window_empty_stats(self, uri, args, fixture):
        storage = storage_from_string(uri, **args)
        limiter = FixedWindowRateLimiter(storage)
        limit = RateLimitItemPerSecond(10, 2)
        assert (await limiter.get_window_stats(limit)).remaining == 10
        assert (await limiter.get_window_stats(limit)).reset_time == pytest.approx(
            time.time(), 1e-2
        )

    @async_fixed_start
    async def test_fixed_window_multiple_cost(self, uri, args, fixture):
        storage = storage_from_string(uri, **args)
        limiter = FixedWindowRateLimiter(storage)
        limit = RateLimitItemPerMinute(10, 2)
        assert not await limiter.hit(limit, "k1", cost=11)
        assert await limiter.hit(limit, "k2", cost=5)
        assert (await limiter.get_window_stats(limit, "k2")).remaining == 5
        assert not await limiter.test(limit, "k2", cost=6)
        assert not await limiter.hit(limit, "k2", cost=6)

    @async_fixed_start
    @pytest.mark.flaky
    async def test_test_fixed_window(self, uri, args, fixture):
        storage = storage_from_string(uri, **args)
        limiter = FixedWindowRateLimiter(storage)
        limit = RateLimitItemPerHour(2, 1)
        assert await limiter.hit(limit)
        assert await limiter.test(limit)
        assert await limiter.hit(limit)
        assert not await limiter.test(limit)
        assert not await limiter.hit(limit)


@pytest.mark.asyncio
@async_moving_window_storage
class TestAsyncMovingWindow:
    async def test_moving_window_stats(self, uri, args, fixture):
        storage = storage_from_string(uri, **args)
        limiter = MovingWindowRateLimiter(storage)
        limit = RateLimitItemPerMinute(2)
        assert await limiter.hit(limit, "key")
        time.sleep(1)
        assert await limiter.hit(limit, "key")
        time.sleep(1)
        assert not await limiter.hit(limit, "key")
        assert (await limiter.get_window_stats(limit, "key")).remaining == 0
        assert (
            await limiter.get_window_stats(limit, "key")
        ).reset_time - time.time() == pytest.approx(58, 1e-2)

    async def test_moving_window(self, uri, args, fixture):
        storage = storage_from_string(uri, **args)
        limiter = MovingWindowRateLimiter(storage)
        limit = RateLimitItemPerSecond(10, 2)
        # 5 hits in the first 500ms
        async with async_window(0.5):
            assert all([await limiter.hit(limit) for i in range(5)])
        # 5 hits in the last 200ms
        async with async_window(2, delay=1.3):
            assert all([await limiter.hit(limit) for i in range(5)])
            # 11th fails
            assert not await limiter.hit(limit)
        # 5 more succeed since there were only 5 in the last 2 seconds
        assert all([await limiter.hit(limit) for i in range(5)])
        assert (await limiter.get_window_stats(limit)).remaining == 0

    async def test_moving_window_empty_stats(self, uri, args, fixture):
        storage = storage_from_string(uri, **args)
        limiter = MovingWindowRateLimiter(storage)
        limit = RateLimitItemPerSecond(10, 2)
        assert (await limiter.get_window_stats(limit)).remaining == 10
        assert (await limiter.get_window_stats(limit)).reset_time == pytest.approx(
            time.time() + 2, 1e-2
        )

    async def test_moving_window_multiple_cost(self, uri, args, fixture):
        storage = storage_from_string(uri, **args)
        limiter = MovingWindowRateLimiter(storage)
        limit = RateLimitItemPerSecond(10, 2)

        assert not await limiter.hit(limit, "k1", cost=11)
        # 5 hits in the first 100ms
        async with async_window(0.1):
            assert await limiter.hit(limit, "k2", cost=5)
        # 5 hits in the last 100ms
        async with async_window(2, delay=1.8):
            assert all([await limiter.hit(limit, "k2") for i in range(4)])
            assert not await limiter.test(limit, "k2", cost=2)
            assert not await limiter.hit(limit, "k2", cost=2)
            assert await limiter.hit(limit, "k2")
        assert all([await limiter.hit(limit, "k2") for i in range(5)])
        assert (await limiter.get_window_stats(limit, "k2")).remaining == 0
        assert not await limiter.hit(limit, "k2", cost=2)

    async def test_moving_window_varying_cost(self, uri, args, fixture):
        storage = storage_from_string(uri, **args)
        limiter = MovingWindowRateLimiter(storage)
        five_per_min = RateLimitItemPerMinute(5)
        await limiter.hit(five_per_min, cost=5)
        assert not await limiter.hit(five_per_min, cost=2)
        await limiter.clear(five_per_min)
        assert await limiter.hit(five_per_min)

    async def test_moving_window_huge_cost_async(self, uri, args, fixture):
        storage = storage_from_string(uri, **args)
        limiter = MovingWindowRateLimiter(storage)
        many_per_min = RateLimitItemPerMinute(1_000_000)
        await limiter.hit(many_per_min, cost=999_999)
        assert not await limiter.hit(many_per_min, cost=2)
        await limiter.clear(many_per_min)
        assert await limiter.hit(many_per_min)

    async def test_test_moving_window(self, uri, args, fixture):
        storage = storage_from_string(uri, **args)
        limit = RateLimitItemPerHour(2, 1)
        limiter = MovingWindowRateLimiter(storage)
        assert await limiter.hit(limit)
        assert await limiter.test(limit)
        assert await limiter.hit(limit)
        assert not await limiter.test(limit)
        assert not await limiter.hit(limit)


@pytest.mark.asyncio
@async_sliding_window_counter_storage
class TestAsyncSlidingWindow:
    @async_fixed_start
    async def test_sliding_window_counter(self, uri, args, fixture):
        storage = storage_from_string(uri, **args)
        limiter = SlidingWindowCounterRateLimiter(storage)
        limit = RateLimitItemPerSecond(10, 2)
        if isinstance(storage, TimestampedSlidingWindow):
            # Avoid testing the behaviour when the window is about to be reset
            ttl = timestamp_based_key_ttl(limit)
            if ttl < 1:
                time.sleep(ttl)
        async with async_window(1) as (start, _):
            assert all([await limiter.hit(limit) for _ in range(0, 10)])
        assert not await limiter.hit(limit)
        assert (await limiter.get_window_stats(limit)).remaining == 0
        assert (await limiter.get_window_stats(limit)).reset_time == pytest.approx(
            start + 2, 1e-2
        )

    @pytest.mark.flaky
    async def test_sliding_window_counter_total_reset(self, uri, args, fixture):
        storage = storage_from_string(uri, **args)
        limiter = SlidingWindowCounterRateLimiter(storage)
        multiple = 10
        period = 1
        limit = RateLimitItemPerSecond(multiple, period)
        assert (await limiter.get_window_stats(limit)).remaining == multiple
        if isinstance(storage, TimestampedSlidingWindow):
            # Avoid testing the behaviour when the window is about to be reset
            ttl = timestamp_based_key_ttl(limit)
            if ttl < 0.5:
                time.sleep(ttl)
        assert await limiter.hit(limit, cost=multiple)
        assert not await limiter.hit(limit)
        assert (await limiter.get_window_stats(limit)).remaining == 0
        time.sleep(period * 2)
        assert (await limiter.get_window_stats(limit)).remaining == multiple
        assert (await limiter.get_window_stats(limit)).reset_time == pytest.approx(
            time.time(), abs=1e-2
        )

    async def test_sliding_window_counter_current_window(self, uri, args, fixture):
        """Check the window stats when only the current window is filled"""
        storage = storage_from_string(uri, **args)
        limiter = SlidingWindowCounterRateLimiter(storage)
        limit = RateLimitItemPerHour(2, 24)
        if isinstance(storage, TimestampedSlidingWindow):
            # Avoid testing the behaviour when the window is about to be reset
            ttl = timestamp_based_key_ttl(limit)
            if ttl < 0.5:
                time.sleep(ttl)
        assert await limiter.hit(limit)
        now = time.time()
        if isinstance(storage, TimestampedSlidingWindow):
            expected_reset_time = now + timestamp_based_key_ttl(limit, now)
        else:
            expected_reset_time = now + 24 * 3600
        assert (await limiter.get_window_stats(limit)).reset_time == pytest.approx(
            expected_reset_time, 1e-2
        )
        assert (await limiter.get_window_stats(limit)).remaining == 1
        assert await limiter.hit(limit)
        assert not await limiter.hit(limit)

    @pytest.mark.flaky(max_runs=3)
    async def test_sliding_window_counter_previous_window(self, uri, args, fixture):
        """Check the window stats when the previous window is partially filled"""
        storage = storage_from_string(uri, **args)
        limiter = SlidingWindowCounterRateLimiter(storage)
        limit = RateLimitItemPerSecond(5, 1)
        sleep_margin = 0.001
        if isinstance(storage, TimestampedSlidingWindow):
            # Avoid testing the behaviour when the window is about to be reset
            ttl = timestamp_based_key_ttl(limit)
            if ttl < 0.3:
                time.sleep(ttl + sleep_margin)
        t0 = time.time()
        previous_window_hits = 3
        await limiter.hit(limit)
        t1 = time.time()
        for i in range(previous_window_hits - 1):
            await limiter.hit(limit)
        # Check the stats: only the current window is filled
        if isinstance(storage, TimestampedSlidingWindow):
            expected_reset_time = t0 + timestamp_based_key_ttl(limit, t0)
        else:
            expected_reset_time = t1 + 1
        reset_time = (await limiter.get_window_stats(limit)).reset_time
        assert reset_time == pytest.approx(expected_reset_time, abs=0.03)
        assert (await limiter.get_window_stats(limit)).remaining == 2
        # Wait for the next window
        sleep_time = expected_reset_time - time.time() + sleep_margin
        time.sleep(sleep_time)
        # A new hit should be available immediately after window shift
        # The limiter should reset in a fraction of a period, according to how many hits are in the previous window
        reset_time = (await limiter.get_window_stats(limit)).reset_time
        reset_in = reset_time - time.time()
        assert reset_in == pytest.approx(
            limit.get_expiry() / previous_window_hits, abs=0.03
        )
        assert (await limiter.get_window_stats(limit)).remaining == 3
        assert await limiter.hit(limit)
        assert await limiter.hit(limit)
        for i in range(previous_window_hits):
            # A new item hit should be freed by the previous window
            t0 = time.time()
            assert (await limiter.get_window_stats(limit)).remaining == 1
            assert await limiter.hit(limit)
            assert (await limiter.get_window_stats(limit)).remaining == 0
            assert not await limiter.hit(limit)
            # The previous window has 4 hits. The reset time should be in a 1/4 of the window expiry
            reset_time = (await limiter.get_window_stats(limit)).reset_time
            t1 = time.time()
            reset_in = reset_time - time.time()
            assert reset_in == pytest.approx(
                limit.get_expiry() / previous_window_hits - (t1 - t0), abs=0.03
            )
            # Wait for the next hit available
            time.sleep(reset_in + sleep_margin)

    @async_fixed_start
    async def test_sliding_window_counter_empty_stats(self, uri, args, fixture):
        storage = storage_from_string(uri, **args)
        limiter = SlidingWindowCounterRateLimiter(storage)
        limit = RateLimitItemPerSecond(10, 2)
        assert (await limiter.get_window_stats(limit)).remaining == 10
        assert (await limiter.get_window_stats(limit)).reset_time == pytest.approx(
            time.time(), 1e-2
        )

    @async_fixed_start
    @pytest.mark.flaky
    async def test_sliding_window_counter_stats(self, uri, args, fixture):
        storage = storage_from_string(uri, **args)
        limiter = SlidingWindowCounterRateLimiter(storage)
        limit = RateLimitItemPerMinute(2)
        if isinstance(storage, TimestampedSlidingWindow):
            next_second_from_now = ceil(time.time())
        assert await limiter.hit(limit, "key")
        time.sleep(1)
        assert await limiter.hit(limit, "key")
        time.sleep(1)
        assert not await limiter.hit(limit, "key")
        assert (await limiter.get_window_stats(limit, "key")).remaining == 0
        if isinstance(storage, TimestampedSlidingWindow):
            # With timestamp-based key implementation,
            # the reset time is periodic according to the worker's timestamp
            reset_time = (await limiter.get_window_stats(limit, "key")).reset_time
            expected_reset = int(
                limit.get_expiry() - (next_second_from_now % limit.get_expiry())
            )
            assert reset_time - next_second_from_now == pytest.approx(
                expected_reset, abs=1e-2
            )
        else:
            assert (
                await limiter.get_window_stats(limit, "key")
            ).reset_time - time.time() == pytest.approx(58, 1e-2)

    @async_fixed_start
    async def test_sliding_window_counter_multiple_cost(self, uri, args, fixture):
        storage = storage_from_string(uri, **args)
        limiter = SlidingWindowCounterRateLimiter(storage)
        limit = RateLimitItemPerMinute(10, 2)
        if isinstance(storage, TimestampedSlidingWindow):
            # Avoid testing the behaviour when the window is about to be reset
            ttl = timestamp_based_key_ttl(limit)
            if ttl < 0.5:
                time.sleep(ttl)
        assert not await limiter.hit(limit, "k1", cost=11)
        assert await limiter.hit(limit, "k2", cost=5)
        assert (await limiter.get_window_stats(limit, "k2")).remaining == 5
        assert not await limiter.test(limit, "k2", cost=6)
        assert not await limiter.hit(limit, "k2", cost=6)

    async def test_test_sliding_window_counter(self, uri, args, fixture):
        storage = storage_from_string(uri, **args)
        limit = RateLimitItemPerHour(2, 1)
        limiter = SlidingWindowCounterRateLimiter(storage)
        assert await limiter.hit(limit)
        assert await limiter.test(limit)
        assert await limiter.hit(limit)
        assert not await limiter.test(limit)
        assert not await limiter.hit(limit)
