import math
import time

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
)
from tests.utils import all_storage, fixed_start, moving_window_storage, window


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
        assert limiter.get_window_stats(limit).reset_time == math.floor(start + 2)

    @all_storage
    @fixed_start
    def test_fixed_window_empty_stats(self, uri, args, fixture):
        storage = storage_from_string(uri, **args)
        limiter = FixedWindowRateLimiter(storage)
        limit = RateLimitItemPerSecond(10, 2)
        assert limiter.get_window_stats(limit).remaining == 10
        assert limiter.get_window_stats(limit).reset_time == int(time.time())

    @all_storage
    @fixed_start
    def test_fixed_window_multiple_cost(self, uri, args, fixture):
        storage = storage_from_string(uri, **args)
        limiter = FixedWindowRateLimiter(storage)
        limit = RateLimitItemPerMinute(10, 2)
        assert not limiter.hit(limit, "k1", cost=11)
        assert limiter.hit(limit, "k2", cost=5)
        assert limiter.get_window_stats(limit, "k2").remaining == 5
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
        assert limiter.get_window_stats(limit).reset_time == start + 2
        with window(3) as (start, end):
            assert not limiter.hit(limit)
        assert limiter.hit(limit)
        assert limiter.get_window_stats(limit).remaining == 9
        assert limiter.get_window_stats(limit).reset_time == end + 2

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
        assert limiter.get_window_stats(limit, "k2").reset_time == end + 2
        assert not limiter.hit(limit, "k2", cost=6)

    @moving_window_storage
    def test_moving_window_empty_stats(self, uri, args, fixture):
        storage = storage_from_string(uri, **args)
        limiter = MovingWindowRateLimiter(storage)
        limit = RateLimitItemPerSecond(10, 2)
        assert limiter.get_window_stats(limit).remaining == 10
        assert limiter.get_window_stats(limit).reset_time == int(time.time() + 2)

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
        assert (
            limiter.get_window_stats(limit, "key").reset_time - int(time.time()) == 58
        )

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
            assert all(limiter.hit(limit, "k2") for i in range(5))
            # 11th fails
            assert not limiter.hit(limit, "k2")

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
