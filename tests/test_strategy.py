import threading
import time
import unittest

import pymemcache.client
import pytest
import redis
import redis.sentinel
import rediscluster
import hiro

from limits.limits import RateLimitItemPerSecond, RateLimitItemPerMinute
from limits.storage import (
    MemoryStorage,
    RedisStorage,
    MemcachedStorage,
    RedisSentinelStorage,
)
from limits.strategies import (
    MovingWindowRateLimiter,
    FixedWindowElasticExpiryRateLimiter,
    FixedWindowRateLimiter,
)
from tests import skip_if_pypy


@pytest.mark.unit
class WindowTests(unittest.TestCase):
    def setUp(self):
        pymemcache.client.Client(("localhost", 22122)).flush_all()
        redis.from_url("redis://localhost:7379").flushall()
        redis.from_url("redis://:sekret@localhost:7389").flushall()
        redis.sentinel.Sentinel([("localhost", 26379)]).master_for(
            "localhost-redis-sentinel"
        ).flushall()
        rediscluster.RedisCluster("localhost", 7000).flushall()

    def test_fixed_window(self):
        storage = MemoryStorage()
        limiter = FixedWindowRateLimiter(storage)
        with hiro.Timeline().freeze() as timeline:
            start = int(time.time())
            limit = RateLimitItemPerSecond(10, 2)
            self.assertTrue(all([limiter.hit(limit) for _ in range(0, 10)]))
            timeline.forward(1)
            self.assertFalse(limiter.hit(limit))
            self.assertEqual(limiter.get_window_stats(limit)[1], 0)
            self.assertEqual(limiter.get_window_stats(limit)[0], start + 2)
            timeline.forward(1)
            self.assertEqual(limiter.get_window_stats(limit)[1], 10)
            self.assertTrue(limiter.hit(limit))

    def test_fixed_window_with_elastic_expiry_in_memory(self):
        storage = MemoryStorage()
        limiter = FixedWindowElasticExpiryRateLimiter(storage)
        with hiro.Timeline().freeze() as timeline:
            start = int(time.time())
            limit = RateLimitItemPerSecond(10, 2)
            self.assertTrue(all([limiter.hit(limit) for _ in range(0, 10)]))
            timeline.forward(1)
            self.assertFalse(limiter.hit(limit))
            self.assertEqual(limiter.get_window_stats(limit)[1], 0)
            # three extensions to the expiry
            self.assertEqual(limiter.get_window_stats(limit)[0], start + 3)
            timeline.forward(1)
            self.assertFalse(limiter.hit(limit))
            timeline.forward(3)
            start = int(time.time())
            self.assertTrue(limiter.hit(limit))
            self.assertEqual(limiter.get_window_stats(limit)[1], 9)
            self.assertEqual(limiter.get_window_stats(limit)[0], start + 2)

    def test_fixed_window_with_elastic_expiry_memcache(self):
        storage = MemcachedStorage("memcached://localhost:22122")
        limiter = FixedWindowElasticExpiryRateLimiter(storage)
        limit = RateLimitItemPerSecond(10, 2)
        self.assertTrue(all([limiter.hit(limit) for _ in range(0, 10)]))
        time.sleep(1)
        self.assertFalse(limiter.hit(limit))
        time.sleep(1)
        self.assertFalse(limiter.hit(limit))

    def test_fixed_window_with_elastic_expiry_memcache_concurrency(self):
        storage = MemcachedStorage("memcached://localhost:22122")
        limiter = FixedWindowElasticExpiryRateLimiter(storage)
        start = int(time.time())
        limit = RateLimitItemPerSecond(10, 2)

        def _c():
            for i in range(0, 5):
                limiter.hit(limit)

        t1, t2 = threading.Thread(target=_c), threading.Thread(target=_c)
        t1.start(), t2.start()
        t1.join(), t2.join()
        self.assertEqual(limiter.get_window_stats(limit)[1], 0)
        self.assertTrue(start + 2 <= limiter.get_window_stats(limit)[0] <= start + 3)
        self.assertEqual(storage.get(limit.key_for()), 10)

    def test_fixed_window_with_elastic_expiry_redis(self):
        storage = RedisStorage("redis://localhost:7379")
        limiter = FixedWindowElasticExpiryRateLimiter(storage)
        limit = RateLimitItemPerSecond(10, 2)
        self.assertTrue(all([limiter.hit(limit) for _ in range(0, 10)]))
        time.sleep(1)
        self.assertFalse(limiter.hit(limit))
        time.sleep(1)
        self.assertFalse(limiter.hit(limit))
        self.assertEqual(limiter.get_window_stats(limit)[1], 0)

    def test_fixed_window_with_elastic_expiry_redis_sentinel(self):
        storage = RedisSentinelStorage(
            "redis+sentinel://localhost:26379", service_name="localhost-redis-sentinel"
        )
        limiter = FixedWindowElasticExpiryRateLimiter(storage)
        limit = RateLimitItemPerSecond(10, 2)
        self.assertTrue(all([limiter.hit(limit) for _ in range(0, 10)]))
        time.sleep(1)
        self.assertFalse(limiter.hit(limit))
        time.sleep(1)
        self.assertFalse(limiter.hit(limit))
        self.assertEqual(limiter.get_window_stats(limit)[1], 0)

    def test_moving_window_in_memory(self):
        storage = MemoryStorage()
        limiter = MovingWindowRateLimiter(storage)
        with hiro.Timeline().freeze() as timeline:
            limit = RateLimitItemPerMinute(10)
            for i in range(0, 5):
                self.assertTrue(limiter.hit(limit))
                self.assertTrue(limiter.hit(limit))
                self.assertEqual(limiter.get_window_stats(limit)[1], 10 - ((i + 1) * 2))
                timeline.forward(10)
            self.assertEqual(limiter.get_window_stats(limit)[1], 0)
            self.assertFalse(limiter.hit(limit))
            timeline.forward(20)
            self.assertEqual(limiter.get_window_stats(limit)[1], 2)
            self.assertEqual(limiter.get_window_stats(limit)[0], int(time.time() + 30))
            timeline.forward(31)
            self.assertEqual(limiter.get_window_stats(limit)[1], 10)

    @skip_if_pypy
    def test_moving_window_redis(self):
        storage = RedisStorage("redis://localhost:7379")
        limiter = MovingWindowRateLimiter(storage)
        limit = RateLimitItemPerSecond(10, 2)
        for i in range(0, 10):
            self.assertTrue(limiter.hit(limit))
            self.assertEqual(limiter.get_window_stats(limit)[1], 10 - (i + 1))
            time.sleep(2 * 0.095)
        self.assertFalse(limiter.hit(limit))
        time.sleep(0.4)
        self.assertTrue(limiter.hit(limit))
        self.assertTrue(limiter.hit(limit))
        self.assertEqual(limiter.get_window_stats(limit)[1], 0)

    def test_moving_window_memcached(self):
        storage = MemcachedStorage("memcached://localhost:22122")
        self.assertRaises(NotImplementedError, MovingWindowRateLimiter, storage)

    def test_test_fixed_window(self):
        with hiro.Timeline().freeze():
            store = MemoryStorage()
            limiter = FixedWindowRateLimiter(store)
            limit = RateLimitItemPerSecond(2, 1)
            self.assertTrue(limiter.hit(limit), store)
            self.assertTrue(limiter.test(limit), store)
            self.assertTrue(limiter.hit(limit), store)
            self.assertFalse(limiter.test(limit), store)
            self.assertFalse(limiter.hit(limit), store)

    def test_test_moving_window(self):
        with hiro.Timeline().freeze():
            store = MemoryStorage()
            limit = RateLimitItemPerSecond(2, 1)
            limiter = MovingWindowRateLimiter(store)
            self.assertTrue(limiter.hit(limit), store)
            self.assertTrue(limiter.test(limit), store)
            self.assertTrue(limiter.hit(limit), store)
            self.assertFalse(limiter.test(limit), store)
            self.assertFalse(limiter.hit(limit), store)
