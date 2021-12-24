import time

import pymemcache.client
import pytest

from limits import RateLimitItemPerMinute, RateLimitItemPerSecond
from limits.storage import MemcachedStorage, storage_from_string
from limits.strategies import (
    FixedWindowElasticExpiryRateLimiter,
    FixedWindowRateLimiter,
)
from tests import fixed_start


@pytest.mark.flaky
class TestMemcachedStorage:
    @pytest.fixture(autouse=True)
    def setup(self, memcached):
        self.storage_url = "memcached://localhost:22122"

    def test_init_options(self, mocker):
        constructor = mocker.spy(pymemcache.client, "PooledClient")
        assert storage_from_string(self.storage_url, connect_timeout=1).check()
        assert constructor.call_args[1]["connect_timeout"] == 1

    @fixed_start
    def test_fixed_window(self):
        storage = MemcachedStorage("memcached://localhost:22122")
        limiter = FixedWindowRateLimiter(storage)
        per_min = RateLimitItemPerSecond(10)
        start = time.time()
        count = 0

        while time.time() - start < 0.5 and count < 10:
            assert limiter.hit(per_min)
            count += 1
        assert not limiter.hit(per_min)

        while time.time() - start <= 1:
            time.sleep(0.1)
        assert limiter.hit(per_min)

    @fixed_start
    def test_fixed_window_cluster(self, memcached_cluster):
        storage = MemcachedStorage("memcached://localhost:22122,localhost:22123")
        limiter = FixedWindowRateLimiter(storage)
        per_min = RateLimitItemPerSecond(10)
        start = time.time()
        count = 0

        while time.time() - start < 0.5 and count < 10:
            assert limiter.hit(per_min)
            count += 1
        assert not limiter.hit(per_min)

        while time.time() - start <= 1:
            time.sleep(0.1)
        assert limiter.hit(per_min)

    @fixed_start
    def test_fixed_window_with_elastic_expiry(self):
        storage = MemcachedStorage("memcached://localhost:22122")
        limiter = FixedWindowElasticExpiryRateLimiter(storage)
        per_sec = RateLimitItemPerSecond(2, 2)

        assert limiter.hit(per_sec)
        time.sleep(1)
        assert limiter.hit(per_sec)
        assert not limiter.test(per_sec)
        time.sleep(1)
        assert not limiter.test(per_sec)
        time.sleep(1)
        assert limiter.test(per_sec)

    @fixed_start
    def test_fixed_window_with_elastic_expiry_cluster(self, memcached_cluster):
        storage = MemcachedStorage("memcached://localhost:22122,localhost:22123")
        limiter = FixedWindowElasticExpiryRateLimiter(storage)
        per_sec = RateLimitItemPerSecond(2, 2)

        assert limiter.hit(per_sec)
        time.sleep(1)
        assert limiter.hit(per_sec)
        assert not limiter.test(per_sec)
        time.sleep(1)
        assert not limiter.test(per_sec)
        time.sleep(1)
        assert limiter.test(per_sec)

    def test_clear(self):
        storage = MemcachedStorage("memcached://localhost:22122")
        limiter = FixedWindowRateLimiter(storage)
        per_min = RateLimitItemPerMinute(1)
        limiter.hit(per_min)
        assert not limiter.hit(per_min)
        limiter.clear(per_min)
        assert limiter.hit(per_min)
