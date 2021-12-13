import threading
import time
import unittest
from uuid import uuid4

import pytest

from limits.limits import RateLimitItemPerSecond
from limits.storage import MemoryStorage
from limits.strategies import FixedWindowRateLimiter, MovingWindowRateLimiter


@pytest.mark.integration
class ConcurrencyTests(unittest.TestCase):
    def test_memory_storage_fixed_window(self):
        storage = MemoryStorage()
        limiter = FixedWindowRateLimiter(storage)
        per_second = RateLimitItemPerSecond(100)

        [limiter.hit(per_second, uuid4().hex) for _ in range(1000)]

        key = uuid4().hex
        hits = []

        def hit():
            if limiter.hit(per_second, key):
                hits.append(None)

        start = time.time()

        threads = [threading.Thread(target=hit) for _ in range(1000)]
        [t.start() for t in threads]
        [t.join() for t in threads]

        self.assertTrue(time.time() - start < 1)
        self.assertEqual(len(hits), 100)

    def test_memory_storage_moving_window(self):
        storage = MemoryStorage()
        limiter = MovingWindowRateLimiter(storage)
        per_second = RateLimitItemPerSecond(100)

        [limiter.hit(per_second, uuid4().hex) for _ in range(100)]

        key = uuid4().hex
        hits = []

        def hit():
            if limiter.hit(per_second, key):
                hits.append(None)

        start = time.time()

        threads = [threading.Thread(target=hit) for _ in range(1000)]
        [t.start() for t in threads]
        [t.join() for t in threads]

        self.assertTrue(time.time() - start < 1)
        self.assertEqual(len(hits), 100)
