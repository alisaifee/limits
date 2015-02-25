import time
import random
import threading
import unittest
from uuid import uuid4

import hiro
import redis

from limits.strategies import FixedWindowRateLimiter, MovingWindowRateLimiter
from limits.errors import ConfigurationError
from limits.limits import RateLimitItemPerMinute, RateLimitItemPerSecond
from limits.storage import (
    MemoryStorage, RedisStorage, MemcachedStorage,
    SaslMemcachedStorage, Storage, storage_from_string
)


class StorageTests(unittest.TestCase):
    def setUp(self):
        redis.Redis().flushall()

    def test_storage_string(self):
        self.assertTrue(isinstance(storage_from_string("memory://"), MemoryStorage))
        self.assertTrue(isinstance(storage_from_string("redis://localhost:6379"), RedisStorage))
        self.assertTrue(isinstance(storage_from_string("memcached://localhost:11211"), MemcachedStorage))
        self.assertTrue(isinstance(storage_from_string("saslmemcached://username:password@localhost:11211"), SaslMemcachedStorage))
        self.assertTrue(isinstance(storage_from_string("saslmemcached://username:password@localhost:11211,localhost:11211"), SaslMemcachedStorage))
        self.assertRaises(ConfigurationError, storage_from_string, "blah://")

    def test_in_memory(self):
        with hiro.Timeline().freeze() as timeline:
            storage = MemoryStorage()
            limiter = FixedWindowRateLimiter(storage)
            per_min = RateLimitItemPerMinute(10)
            for i in range(0,10):
                self.assertTrue(limiter.hit(per_min))
            self.assertFalse(limiter.hit(per_min))
            timeline.forward(61)
            self.assertTrue(limiter.hit(per_min))

    def test_in_memory_expiry(self):
        with hiro.Timeline().freeze() as timeline:
            storage = MemoryStorage()
            limiter = FixedWindowRateLimiter(storage)
            per_min = RateLimitItemPerMinute(10)
            for i in range(0,10):
                self.assertTrue(limiter.hit(per_min))
            timeline.forward(60)
            # touch another key and yield
            limiter.hit(RateLimitItemPerSecond(1))
            time.sleep(0.1)
            self.assertTrue(per_min.key_for() not in storage.storage)

    def test_in_memory_expiry_moving_window(self):
        with hiro.Timeline().freeze() as timeline:
            storage = MemoryStorage()
            limiter = MovingWindowRateLimiter(storage)
            per_min = RateLimitItemPerMinute(10)
            per_sec = RateLimitItemPerSecond(1)
            for i in range(0,2):
                for i in range(0,10):
                    self.assertTrue(limiter.hit(per_min))
                timeline.forward(60)
                self.assertTrue(limiter.hit(per_sec))
                time.sleep(1)
                self.assertEqual([], storage.events[per_min.key_for()])


    def test_redis(self):
        storage = RedisStorage("redis://localhost:6379")
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

    def test_pluggable_storage_no_moving_window(self):
        class MyStorage(Storage):
            STORAGE_SCHEME = "mystorage"
            def incr(self, key, expiry, elastic_expiry=False):
                return

            def get(self, key):
                return 0

            def get_expiry(self, key):
                return time.time()


        storage = storage_from_string("mystorage://")
        self.assertTrue(isinstance(storage, MyStorage))
        self.assertRaises(NotImplementedError, MovingWindowRateLimiter, storage)

    def test_pluggable_storage_moving_window(self):
        class MyStorage(Storage):
            STORAGE_SCHEME = "mystorage"
            def incr(self, key, expiry, elastic_expiry=False):
                return

            def get(self, key):
                return 0

            def get_expiry(self, key):
                return time.time()

            def acquire_entry(self, *a, **k):
                return True

            def get_moving_window(self, *a, **k):
                return (time.time(), 1)

        storage = storage_from_string("mystorage://")
        self.assertTrue(isinstance(storage, MyStorage))
        MovingWindowRateLimiter(storage)

    def test_memcached(self):
        storage = MemcachedStorage("memcached://localhost:11211")
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


    def test_large_dataset_redis_moving_window_expiry(self):
        storage = RedisStorage("redis://localhost:6379")
        limiter = MovingWindowRateLimiter(storage)
        limit = RateLimitItemPerSecond(1000)
        keys_start = storage.storage.keys('%s/*' % limit.namespace)
        # 100 routes
        fake_routes = [uuid4().hex for _ in range(0,100)]
        # go as fast as possible in 2 seconds.
        start = time.time()
        def smack(e):
            while not e.is_set():
                self.assertTrue(limiter.hit(limit, random.choice(fake_routes)))
        events = [threading.Event() for _ in range(0,100)]
        threads = [threading.Thread(target=smack, args=(e,)) for e in events]
        [k.start() for k in threads]
        while time.time() - start < 2:
            time.sleep(0.1)
        [k.set() for k in events]
        time.sleep(2)
        self.assertTrue(storage.storage.keys("%s/*" % limit.namespace) == [])
