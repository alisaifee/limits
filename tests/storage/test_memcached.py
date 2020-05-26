import time
import unittest

import mock
import pytest
import pymemcache.client

from limits import RateLimitItemPerSecond, RateLimitItemPerMinute
from limits.storage import storage_from_string, MemcachedStorage
from limits.strategies import (
    FixedWindowRateLimiter,
    FixedWindowElasticExpiryRateLimiter
)
from tests import fixed_start


@pytest.mark.unit
class MemcachedStorageTests(unittest.TestCase):
    def setUp(self):
        pymemcache.client.Client(('localhost', 22122)).flush_all()
        self.storage_url = 'memcached://localhost:22122'

    def test_options(self):
        with mock.patch(
            "limits.storage.memcached.get_dependency"
        ) as get_dependency:
            storage_from_string(self.storage_url, connect_timeout=1).check()
            self.assertEqual(
                get_dependency().Client.call_args[1]['connect_timeout'], 1
            )

    @fixed_start
    def test_fixed_window(self):
        storage = MemcachedStorage("memcached://localhost:22122")
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
    def test_fixed_window_cluster(self):
        storage = MemcachedStorage(
            "memcached://localhost:22122,localhost:22123"
        )
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
    def test_fixed_window_with_elastic_expiry(self):
        storage = MemcachedStorage("memcached://localhost:22122")
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

    @fixed_start
    def test_fixed_window_with_elastic_expiry_cluster(self):
        storage = MemcachedStorage(
            "memcached://localhost:22122,localhost:22123"
        )
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

    def test_clear(self):
        storage = MemcachedStorage("memcached://localhost:22122")
        limiter = FixedWindowRateLimiter(storage)
        per_min = RateLimitItemPerMinute(1)
        limiter.hit(per_min)
        self.assertFalse(limiter.hit(per_min))
        limiter.clear(per_min)
        self.assertTrue(limiter.hit(per_min))