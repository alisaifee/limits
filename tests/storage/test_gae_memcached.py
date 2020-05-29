import time
import unittest

from limits import RateLimitItemPerSecond
from limits.storage import GAEMemcachedStorage
from limits.strategies import (
    FixedWindowRateLimiter,
    FixedWindowElasticExpiryRateLimiter
)
from tests import RUN_GAE, fixed_start


def setup_method():
    from google.appengine.ext import testbed
    tb = testbed.Testbed()
    tb.activate()
    tb.init_memcache_stub()


@fixed_start
@unittest.skipUnless(RUN_GAE, reason='Only for GAE')
def test_fixed_window():
    storage = GAEMemcachedStorage("gaememcached://")
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
@unittest.skipUnless(RUN_GAE, reason='Only for GAE')
def test_fixed_window_with_elastic_expiry_cluster():
    storage = GAEMemcachedStorage("gaememcached://")
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
