import datetime
import time
import unittest

import mock
import pytest
import pymongo

from limits import RateLimitItemPerSecond, RateLimitItemPerMinute
from limits.storage import MongoDBStorage, storage_from_string
from limits.strategies import FixedWindowRateLimiter, MovingWindowRateLimiter


@pytest.mark.unit
class MongoDBStorageTests(unittest.TestCase):
    def setUp(self):
        self.storage_url = "mongodb://localhost:37017"
        self.storage = MongoDBStorage(self.storage_url)
        pymongo.MongoClient(self.storage_url).limits.windows.drop()
        pymongo.MongoClient(self.storage_url).limits.counters.drop()

    def test_init_options(self):
        with mock.patch("limits.storage.mongodb.get_dependency") as get_dependency:
            storage_from_string(self.storage_url, connection_timeout=1)
            self.assertEqual(
                get_dependency().MongoClient.call_args[1]["connection_timeout"], 1
            )

    def test_fixed_window(self):
        limiter = FixedWindowRateLimiter(self.storage)
        per_second = RateLimitItemPerSecond(10)
        start = time.time()
        count = 0

        while time.time() - start < 0.5 and count < 10:
            self.assertTrue(limiter.hit(per_second))
            count += 1
        self.assertFalse(limiter.hit(per_second))

        while time.time() - start <= 1:
            time.sleep(0.1)
        [self.assertTrue(limiter.hit(per_second)) for _ in range(10)]

    def test_reset(self):
        limiter = FixedWindowRateLimiter(self.storage)

        for i in range(0, 10):
            rate = RateLimitItemPerMinute(i)
            limiter.hit(rate)
        self.assertEqual(self.storage.reset(), 10)

    def test_fixed_window_clear(self):
        limiter = FixedWindowRateLimiter(self.storage)
        per_min = RateLimitItemPerMinute(1)
        limiter.hit(per_min)
        self.assertFalse(limiter.hit(per_min))
        limiter.clear(per_min)
        self.assertTrue(limiter.hit(per_min))

    def test_moving_window_clear(self):
        limiter = MovingWindowRateLimiter(self.storage)
        per_min = RateLimitItemPerMinute(1)
        limiter.hit(per_min)
        self.assertFalse(limiter.hit(per_min))
        limiter.clear(per_min)
        self.assertTrue(limiter.hit(per_min))

    def test_moving_window_expiry(self):
        limiter = MovingWindowRateLimiter(self.storage)
        limit = RateLimitItemPerSecond(2)
        self.assertTrue(limiter.hit(limit))
        time.sleep(0.9)
        self.assertTrue(limiter.hit(limit))
        self.assertFalse(limiter.hit(limit))
        time.sleep(0.1)
        self.assertTrue(limiter.hit(limit))
        last = time.time()

        while time.time() - last <= 1:
            time.sleep(0.05)

        assert [] == list(
            self.storage.storage.limits.windows.find(
                {"expireAt": {"$gt": datetime.datetime.utcnow()}}
            )
        )
