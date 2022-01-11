import math
import time

import pytest

from limits.limits import RateLimitItemPerSecond
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
        assert limiter.get_window_stats(limit)[1] == 0
        assert limiter.get_window_stats(limit)[0] == math.floor(start + 2)

    @all_storage
    def test_fixed_window_empty_stats(self, uri, args, fixture):
        storage = storage_from_string(uri, **args)
        limiter = FixedWindowRateLimiter(storage)
        limit = RateLimitItemPerSecond(10, 2)
        assert limiter.get_window_stats(limit)[1] == 10
        assert limiter.get_window_stats(limit)[0] == int(time.time())

    @all_storage
    def test_fixed_window_with_elastic_expiry(self, uri, args, fixture):
        storage = storage_from_string(uri, **args)
        limiter = FixedWindowElasticExpiryRateLimiter(storage)
        limit = RateLimitItemPerSecond(10, 2)
        with window(1) as (start, end):
            assert all([limiter.hit(limit) for _ in range(0, 10)])
            assert not limiter.hit(limit)
        assert limiter.get_window_stats(limit)[1] == 0
        assert limiter.get_window_stats(limit)[0] == start + 2
        with window(3) as (start, end):
            assert not limiter.hit(limit)
        assert limiter.hit(limit)
        assert limiter.get_window_stats(limit)[1] == 9
        assert limiter.get_window_stats(limit)[0] == end + 2

    @moving_window_storage
    def test_moving_window_empty_stats(self, uri, args, fixture):
        storage = storage_from_string(uri, **args)
        limiter = MovingWindowRateLimiter(storage)
        limit = RateLimitItemPerSecond(10, 2)
        assert limiter.get_window_stats(limit)[1] == 10
        assert limiter.get_window_stats(limit)[0] == int(time.time() + 2)

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
        # 5 more succeed since there were only 5 in the last 2 seconds
        assert all(limiter.hit(limit) for i in range(5))
        assert limiter.get_window_stats(limit)[1] == 0
        assert limiter.get_window_stats(limit)[0] == int(time.time() + 2)

    @pytest.mark.memcached
    def test_moving_window_memcached(self, memcached):
        storage = MemcachedStorage("memcached://localhost:22122")
        with pytest.raises(NotImplementedError):
            MovingWindowRateLimiter(storage)

    @all_storage
    def test_test_fixed_window(self, uri, args, fixture):
        storage = storage_from_string(uri, **args)
        limiter = FixedWindowRateLimiter(storage)
        limit = RateLimitItemPerSecond(2, 1)
        assert limiter.hit(limit)
        assert limiter.test(limit)
        assert limiter.hit(limit)
        assert not limiter.test(limit)
        assert not limiter.hit(limit)

    @moving_window_storage
    def test_test_moving_window(self, uri, args, fixture):
        storage = storage_from_string(uri, **args)
        limit = RateLimitItemPerSecond(2, 1)
        limiter = MovingWindowRateLimiter(storage)
        assert limiter.hit(limit)
        assert limiter.test(limit)
        assert limiter.hit(limit)
        assert not limiter.test(limit)
        assert not limiter.hit(limit)
