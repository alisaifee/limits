import time

import pytest

from limits import RateLimitItemPerMinute, RateLimitItemPerSecond
from limits.storage import EtcdStorage
from limits.strategies import (
    FixedWindowElasticExpiryRateLimiter,
    FixedWindowRateLimiter,
)
from tests.utils import fixed_start


@pytest.mark.flaky
@pytest.mark.etcd
class TestEtcdStorage:
    @pytest.fixture(autouse=True)
    def setup(self, etcd):
        self.storage_url = "etcd://localhost:2379"
        self.storage = EtcdStorage(self.storage_url)

    @fixed_start
    def test_fixed_window(self):
        limiter = FixedWindowRateLimiter(self.storage)
        per_sec = RateLimitItemPerSecond(10)
        start = time.time()
        count = 0

        while time.time() - start < 0.5 and count < 10:
            assert limiter.hit(per_sec)
            count += 1
        assert not limiter.hit(per_sec)

        while time.time() - start <= 1:
            time.sleep(0.1)
        assert limiter.hit(per_sec)

    @fixed_start
    def test_fixed_window_with_elastic_expiry(self):
        limiter = FixedWindowElasticExpiryRateLimiter(self.storage)
        per_sec = RateLimitItemPerSecond(2, 2)

        assert limiter.hit(per_sec)
        time.sleep(1)
        assert limiter.hit(per_sec)
        assert not limiter.test(per_sec)
        time.sleep(1)
        assert not limiter.test(per_sec)
        time.sleep(1)
        assert limiter.test(per_sec)

    def test_reset(self):
        limiter = FixedWindowRateLimiter(self.storage)

        for i in range(0, 10):
            rate = RateLimitItemPerMinute(i)
            limiter.hit(rate)
        assert self.storage.reset() == 10

    def test_clear(self):
        limiter = FixedWindowRateLimiter(self.storage)
        per_min = RateLimitItemPerMinute(1)
        limiter.hit(per_min)
        assert not limiter.hit(per_min)
        limiter.clear(per_min)
        assert limiter.hit(per_min)
