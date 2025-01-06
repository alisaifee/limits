import time
from math import ceil

import pytest

from limits.limits import (
    RateLimitItemPerHour,
    RateLimitItemPerMinute,
    RateLimitItemPerSecond,
)
from limits.storage import MemcachedStorage, storage_from_string
from limits.strategies import (
    FixedWindowElasticExpiryRateLimiter,
    FixedWindowRateLimiter,
    MovingWindowRateLimiter,
    SlidingWindowCounterRateLimiter,
)
from tests.utils import (
    all_storage,
    fixed_start,
    moving_window_storage,
    sliding_window_counter_storage,
    sliding_window_counter_timestamp_based_key,
    timestamp_based_key_ttl,
    window,
)


class TestWindow:
    @all_storage
    @fixed_start
    def test_fixed_window(self, uri, args, fixture):
        storage = storage_from_string(uri, **args)
        limiter = FixedWindowRateLimiter(storage)
        limit = RateLimitItemPerSecond(10, 2)
        with window(1) as (start, end):
            assert all([limiter.hit(limit) for _ in range(0, 10)])
        assert not limiter.hit(limit)
        assert limiter.get_window_stats(limit).remaining == 0
        assert limiter.get_window_stats(limit).reset_time == pytest.approx(
            start + 2, 1e-2
        )

    @all_storage
    @fixed_start
    def test_fixed_window_empty_stats(self, uri, args, fixture):
        storage = storage_from_string(uri, **args)
        limiter = FixedWindowRateLimiter(storage)
        limit = RateLimitItemPerSecond(10, 2)
        assert limiter.get_window_stats(limit).remaining == 10
        assert limiter.get_window_stats(limit).reset_time == pytest.approx(
            time.time(), 1e-2
        )

    @all_storage
    @fixed_start
    def test_fixed_window_multiple_cost(self, uri, args, fixture):
        storage = storage_from_string(uri, **args)
        limiter = FixedWindowRateLimiter(storage)
        limit = RateLimitItemPerMinute(10, 2)
        assert not limiter.hit(limit, "k1", cost=11)
        assert limiter.hit(limit, "k2", cost=5)
        assert limiter.get_window_stats(limit, "k2").remaining == 5
        assert not limiter.test(limit, "k2", cost=6)
        assert not limiter.hit(limit, "k2", cost=6)

    @all_storage
    @fixed_start
    def test_fixed_window_with_elastic_expiry(self, uri, args, fixture):
        storage = storage_from_string(uri, **args)
        limiter = FixedWindowElasticExpiryRateLimiter(storage)
        limit = RateLimitItemPerSecond(10, 2)
        with window(1) as (start, end):
            assert all([limiter.hit(limit) for _ in range(0, 10)])
            assert not limiter.hit(limit)
        assert limiter.get_window_stats(limit).remaining == 0
        assert limiter.get_window_stats(limit).reset_time == pytest.approx(
            start + 2, 1e-2
        )
        with window(3) as (start, end):
            assert not limiter.hit(limit)
        assert limiter.hit(limit)
        assert limiter.get_window_stats(limit).remaining == 9
        assert limiter.get_window_stats(limit).reset_time == pytest.approx(
            end + 2, 1e-2
        )

    @all_storage
    @fixed_start
    def test_fixed_window_with_elastic_expiry_multiple_cost(self, uri, args, fixture):
        storage = storage_from_string(uri, **args)
        limiter = FixedWindowElasticExpiryRateLimiter(storage)
        limit = RateLimitItemPerSecond(10, 2)
        assert not limiter.hit(limit, "k1", cost=11)
        with window(0) as (start, end):
            assert limiter.hit(limit, "k2", cost=5)
        assert limiter.get_window_stats(limit, "k2").remaining == 5
        assert limiter.get_window_stats(limit, "k2").reset_time == pytest.approx(
            end + 2, 1e-2
        )
        assert not limiter.hit(limit, "k2", cost=6)

    @sliding_window_counter_storage
    @fixed_start
    def test_sliding_window_counter(self, uri, args, fixture):
        storage = storage_from_string(uri, **args)
        limiter = SlidingWindowCounterRateLimiter(storage)
        limit = RateLimitItemPerSecond(10, 2)
        if sliding_window_counter_timestamp_based_key(uri):
            next_second_from_now = ceil(time.time())
            if next_second_from_now % 2 == 0:
                # Next second is even, so the curent one is odd.
                # Must wait a full period for memcached.
                time.sleep(1)
                next_second_from_now = ceil(time.time())
        with window(1) as (start, end):
            assert all([limiter.hit(limit) for _ in range(0, 10)])
        assert not limiter.hit(limit)
        assert limiter.get_window_stats(limit).remaining == 0
        if sliding_window_counter_timestamp_based_key(uri):
            # If the key is timestamp-based, the reset time is periodic according to the worker's timestamp
            reset_time = limiter.get_window_stats(limit).reset_time
            expected_reset = int(
                limit.get_expiry() - (next_second_from_now % limit.get_expiry())
            )
            assert reset_time - next_second_from_now == pytest.approx(
                expected_reset, abs=1e-2
            )
        else:
            assert limiter.get_window_stats(limit).reset_time == pytest.approx(
                start + 2, 1e-2
            )

    @sliding_window_counter_storage
    def test_sliding_window_counter_current_window(self, uri, args, fixture):
        """Check the window stats when only the current window is filled"""
        storage = storage_from_string(uri, **args)
        limiter = SlidingWindowCounterRateLimiter(storage)
        limit = RateLimitItemPerHour(2, 24)
        if sliding_window_counter_timestamp_based_key(uri):
            # Avoid testing the behaviour when the window is about to be reset
            ttl = timestamp_based_key_ttl(limit)
            if ttl < 0.5:
                time.sleep(ttl)
        assert limiter.hit(limit)
        now = time.time()
        if sliding_window_counter_timestamp_based_key(uri):
            expected_reset_time = now + timestamp_based_key_ttl(limit, now)
        else:
            expected_reset_time = now + 24 * 3600
        assert limiter.get_window_stats(limit).reset_time == pytest.approx(
            expected_reset_time, 1e-2
        )
        assert limiter.get_window_stats(limit).remaining == 1
        assert limiter.hit(limit)
        assert not limiter.hit(limit)

    @sliding_window_counter_storage
    @pytest.mark.flaky(max_runs=3)
    def test_sliding_window_counter_previous_window(self, uri, args, fixture):
        """Check the window stats when the previous window is partially filled"""
        storage = storage_from_string(uri, **args)
        limiter = SlidingWindowCounterRateLimiter(storage)
        limit = RateLimitItemPerSecond(5, 1)
        sleep_margin = 0.001
        if sliding_window_counter_timestamp_based_key(uri):
            # Avoid testing the behaviour when the window is about to be reset
            ttl = timestamp_based_key_ttl(limit)
            if ttl < 0.3:
                time.sleep(ttl + sleep_margin)
        previous_window_hits = 3
        for i in range(previous_window_hits):
            limiter.hit(limit)
        now = time.time()
        # Check the stats: only the current window is filled
        assert limiter.get_window_stats(limit).remaining == 2
        if sliding_window_counter_timestamp_based_key(uri):
            expected_reset_time = now + timestamp_based_key_ttl(limit, now)
        else:
            expected_reset_time = now + 1
        assert limiter.get_window_stats(limit).reset_time == pytest.approx(
            expected_reset_time, 1e-2
        )
        # Wait for the next window
        sleep_time = expected_reset_time - time.time() + sleep_margin
        time.sleep(sleep_time)
        # A new hit should be available immediately after window shift
        # The limiter should reset in a fraction of a period, according to how many hits are in the previous window
        reset_time = limiter.get_window_stats(limit).reset_time
        reset_in = reset_time - time.time()
        assert reset_in == pytest.approx(
            limit.get_expiry() / previous_window_hits, abs=0.03
        )
        assert limiter.get_window_stats(limit).remaining == 3
        assert limiter.hit(limit)
        assert limiter.hit(limit)
        for i in range(previous_window_hits):
            # A new item hit should be freed by the previous window
            t0 = time.time()
            assert limiter.get_window_stats(limit).remaining == 1
            assert limiter.hit(limit)
            assert limiter.get_window_stats(limit).remaining == 0
            assert not limiter.hit(limit)
            # The previous window has 4 hits. The reset time should be in a 1/4 of the window expiry
            reset_time = limiter.get_window_stats(limit).reset_time
            t1 = time.time()
            reset_in = reset_time - time.time()
            assert reset_in == pytest.approx(
                limit.get_expiry() / previous_window_hits - (t1 - t0), abs=0.03
            )
            # Wait for the next hit available
            time.sleep(reset_in + sleep_margin)

    @sliding_window_counter_storage
    @fixed_start
    def test_sliding_window_counter_empty_stats(self, uri, args, fixture):
        storage = storage_from_string(uri, **args)
        limiter = SlidingWindowCounterRateLimiter(storage)
        limit = RateLimitItemPerSecond(10, 2)
        assert limiter.get_window_stats(limit).remaining == 10
        assert limiter.get_window_stats(limit).reset_time == pytest.approx(
            time.time(), 1e-2
        )

    @sliding_window_counter_storage
    @fixed_start
    def test_sliding_window_counter_multiple_cost(self, uri, args, fixture):
        storage = storage_from_string(uri, **args)
        limiter = SlidingWindowCounterRateLimiter(storage)
        limit = RateLimitItemPerMinute(10, 2)
        if sliding_window_counter_timestamp_based_key(uri):
            # Avoid testing the behaviour when the window is about to be reset
            ttl = timestamp_based_key_ttl(limit)
            if ttl < 0.5:
                time.sleep(ttl)
        assert not limiter.hit(limit, "k1", cost=11)
        assert limiter.hit(limit, "k2", cost=5)
        assert limiter.get_window_stats(limit, "k2").remaining == 5
        assert not limiter.test(limit, "k2", cost=6)
        assert not limiter.hit(limit, "k2", cost=6)

    @moving_window_storage
    def test_moving_window_empty_stats(self, uri, args, fixture):
        storage = storage_from_string(uri, **args)
        limiter = MovingWindowRateLimiter(storage)
        limit = RateLimitItemPerSecond(10, 2)
        assert limiter.get_window_stats(limit).remaining == 10
        assert limiter.get_window_stats(limit).reset_time == pytest.approx(
            time.time() + 2, 1e-2
        )

    @moving_window_storage
    def test_moving_window_stats(self, uri, args, fixture):
        storage = storage_from_string(uri, **args)
        limiter = MovingWindowRateLimiter(storage)
        limit = RateLimitItemPerMinute(2)
        assert limiter.hit(limit, "key")
        time.sleep(1)
        assert limiter.hit(limit, "key")
        time.sleep(1)
        assert not limiter.hit(limit, "key")
        assert limiter.get_window_stats(limit, "key").remaining == 0
        assert limiter.get_window_stats(
            limit, "key"
        ).reset_time - time.time() == pytest.approx(58, 1e-2)

    @moving_window_storage
    def test_moving_window(self, uri, args, fixture):
        storage = storage_from_string(uri, **args)
        limiter = MovingWindowRateLimiter(storage)
        limit = RateLimitItemPerSecond(10, 2)

        # 5 hits in the first 100ms
        with window(0.1):
            assert all(limiter.hit(limit) for i in range(5))
        # 5 hits in the last 100ms
        with window(2, delay=1.8):
            assert all(limiter.hit(limit) for i in range(5))
            # 11th fails
            assert not limiter.hit(limit)

    @moving_window_storage
    def test_moving_window_multiple_cost(self, uri, args, fixture):
        storage = storage_from_string(uri, **args)
        limiter = MovingWindowRateLimiter(storage)
        limit = RateLimitItemPerSecond(10, 2)

        assert not limiter.hit(limit, "k1", cost=11)
        # 5 hits in the first 100ms
        with window(0.1):
            limiter.hit(limit, "k2", cost=5)
        # 5 hits in the last 100ms
        with window(2, delay=1.8):
            assert all(limiter.hit(limit, "k2") for i in range(4))
            assert not limiter.test(limit, "k2", cost=2)
            assert not limiter.hit(limit, "k2", cost=2)
            assert limiter.hit(limit, "k2")

        # 5 more succeed since there were only 5 in the last 2 seconds
        assert all([limiter.hit(limit, "k2") for i in range(5)])
        assert limiter.get_window_stats(limit, "k2")[1] == 0
        assert not limiter.hit(limit, "k2", cost=2)

    @moving_window_storage
    def test_moving_window_varying_cost(self, uri, args, fixture):
        storage = storage_from_string(uri, **args)
        limiter = MovingWindowRateLimiter(storage)
        five_per_min = RateLimitItemPerMinute(5)
        limiter.hit(five_per_min, cost=5)
        assert not limiter.hit(five_per_min, cost=2)
        limiter.clear(five_per_min)
        assert limiter.hit(five_per_min)

    @moving_window_storage
    def test_moving_window_huge_cost_sync(self, uri, args, fixture):
        storage = storage_from_string(uri, **args)
        limiter = MovingWindowRateLimiter(storage)
        many_per_min = RateLimitItemPerMinute(1_000_000)
        limiter.hit(many_per_min, cost=1_000_000)
        assert not limiter.hit(many_per_min, cost=2)
        limiter.clear(many_per_min)
        assert limiter.hit(many_per_min)

    @pytest.mark.memcached
    def test_moving_window_memcached(self, memcached):
        storage = MemcachedStorage("memcached://localhost:22122")
        with pytest.raises(NotImplementedError):
            MovingWindowRateLimiter(storage)

    @all_storage
    @fixed_start
    @pytest.mark.flaky
    def test_test_fixed_window(self, uri, args, fixture):
        storage = storage_from_string(uri, **args)
        limiter = FixedWindowRateLimiter(storage)
        limit = RateLimitItemPerHour(2, 1)
        assert limiter.hit(limit)
        assert limiter.test(limit)
        assert limiter.hit(limit)
        assert not limiter.test(limit)
        assert not limiter.hit(limit)

    @sliding_window_counter_storage
    @fixed_start
    @pytest.mark.flaky
    def test_test_sliding_window_counter(self, uri, args, fixture):
        storage = storage_from_string(uri, **args)
        limiter = SlidingWindowCounterRateLimiter(storage)
        limit = RateLimitItemPerHour(2, 1)
        assert limiter.hit(limit)
        assert limiter.test(limit)
        assert limiter.hit(limit)
        assert not limiter.test(limit)
        assert not limiter.hit(limit)

    @moving_window_storage
    def test_test_moving_window(self, uri, args, fixture):
        storage = storage_from_string(uri, **args)
        limit = RateLimitItemPerHour(2, 1)
        limiter = MovingWindowRateLimiter(storage)
        assert limiter.hit(limit)
        assert limiter.test(limit)
        assert limiter.hit(limit)
        assert not limiter.test(limit)
        assert not limiter.hit(limit)
