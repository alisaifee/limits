import time
import unittest

import pytest

from limits import RateLimitItemPerSecond
from limits.storage import GAEMemcachedStorage
from limits.strategies import (
    FixedWindowRateLimiter,
    FixedWindowElasticExpiryRateLimiter
)
from tests import RUN_GAE, fixed_start


@pytest.mark.unit
@unittest.skipUnless(RUN_GAE, reason='Only for GAE')
class GAEMemcachedStorageTests(unittest.TestCase):
    def setUp(self):
        from google.appengine.ext import testbed
        tb = testbed.Testbed()
        tb.activate()
        tb.init_memcache_stub()

    @fixed_start
    def test_fixed_window(self):
        storage = GAEMemcachedStorage("gaememcached://")
        limiter = FixedWindowRateLimiter(storage)
        per_min = RateLimitItemPerSecond(10)
        start = time.time()
        count = 0
        while time.time() - start < 0.5 and count < 10:
            self.assertTrue(limiter.hit(per_min))
            count += 1
        self.assertFalse(limiter.hit(per_min))
        while time.time() - start <= 1:
            time.sleep(0.1)
        self.assertTrue(limiter.hit(per_min))

    @fixed_start
    def test_fixed_window_with_elastic_expiry_cluster(self):
        storage = GAEMemcachedStorage("gaememcached://")
        limiter = FixedWindowElasticExpiryRateLimiter(storage)
        per_sec = RateLimitItemPerSecond(2, 2)

        self.assertTrue(limiter.hit(per_sec))
        time.sleep(1)
        self.assertTrue(limiter.hit(per_sec))
        self.assertFalse(limiter.test(per_sec))
        time.sleep(1)
        self.assertFalse(limiter.test(per_sec))
        time.sleep(1)
        self.assertTrue(limiter.test(per_sec))