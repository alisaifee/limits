import random
import threading
import time
import unittest
from uuid import uuid4

import pymemcache.client
import redis
import redis.sentinel
import rediscluster

import hiro
import mock

from limits.errors import ConfigurationError
from limits.limits import RateLimitItemPerMinute, RateLimitItemPerSecond
from limits.storage import (
    MemoryStorage, RedisStorage, MemcachedStorage, RedisSentinelStorage,
    RedisClusterStorage, Storage, GAEMemcachedStorage, storage_from_string
)
from limits.strategies import FixedWindowRateLimiter, MovingWindowRateLimiter
from tests import skip_if, RUN_GAE


class BaseStorageTests(unittest.TestCase):
    def setUp(self):
        pymemcache.client.Client(('localhost', 22122)).flush_all()
        redis.from_url('unix:///var/tmp/limits.redis.sock').flushall()
        redis.Redis().flushall()
        redis.sentinel.Sentinel([
            ("localhost", 26379)
        ]).master_for("localhost-redis-sentinel").flushall()
        rediscluster.RedisCluster("localhost", 7000).flushall()
        if RUN_GAE:
            from google.appengine.ext import testbed
            tb = testbed.Testbed()
            tb.activate()
            tb.init_memcache_stub()

    def test_storage_string(self):
        self.assertTrue(
            isinstance(storage_from_string("memory://"), MemoryStorage)
        )
        self.assertTrue(
            isinstance(
                storage_from_string("redis://localhost:6379"), RedisStorage
            )
        )
        self.assertTrue(
            isinstance(
                storage_from_string("redis+unix:///var/tmp/limits.redis.sock"), RedisStorage
            )
        )

        self.assertTrue(
            isinstance(
                storage_from_string("redis+unix://:password/var/tmp/limits.redis.sock"), RedisStorage
            )
        )

        self.assertTrue(
            isinstance(
                storage_from_string("memcached://localhost:22122"),
                MemcachedStorage
            )
        )

        self.assertTrue(
            isinstance(
                storage_from_string("memcached://localhost:22122,localhost:22123"),
                MemcachedStorage
            )
        )

        self.assertTrue(
            isinstance(
                storage_from_string("memcached:///tmp/limits.memcached.sock"),
                MemcachedStorage
            )
        )

        self.assertTrue(
            isinstance(
                storage_from_string(
                    "redis+sentinel://localhost:26379",
                    service_name="localhost-redis-sentinel"
                ), RedisSentinelStorage
            )
        )
        self.assertTrue(
            isinstance(
                storage_from_string(
                    "redis+sentinel://localhost:26379/localhost-redis-sentinel"
                ), RedisSentinelStorage
            )
        )
        self.assertTrue(
            isinstance(
                storage_from_string("redis+cluster://localhost:7000/"),
                RedisClusterStorage
            )
        )
        if RUN_GAE:
            self.assertTrue(
                isinstance(
                    storage_from_string("gaememcached://"), GAEMemcachedStorage
                )
            )
        self.assertRaises(ConfigurationError, storage_from_string, "blah://")
        self.assertRaises(
            ConfigurationError, storage_from_string,
            "redis+sentinel://localhost:26379"
        )
        with mock.patch("limits.storage.get_dependency") as get_dependency:
            self.assertTrue(
                isinstance(
                    storage_from_string(
                        "redis+sentinel://:foobared@localhost:26379/localhost-redis-sentinel"
                    ), RedisSentinelStorage
                )
            )
            self.assertEqual(
                get_dependency().Sentinel.call_args[1]['password'], 'foobared'
            )

    def test_storage_check(self):
        self.assertTrue(storage_from_string("memory://").check())
        self.assertTrue(storage_from_string("redis://localhost:6379").check())
        self.assertTrue(storage_from_string("redis+unix:///var/tmp/limits.redis.sock").check())
        self.assertTrue(
            storage_from_string("memcached://localhost:22122").check()
        )
        self.assertTrue(
            storage_from_string("memcached://localhost:22122,localhost:22123").check()
        )
        self.assertTrue(
            storage_from_string("memcached:///tmp/limits.memcached.sock").check()
        )
        self.assertTrue(
            storage_from_string(
                "redis+sentinel://localhost:26379",
                service_name="localhost-redis-sentinel"
            ).check()
        )
        self.assertTrue(
            storage_from_string("redis+cluster://localhost:7000").check()
        )
        if RUN_GAE:
            self.assertTrue(storage_from_string("gaememcached://").check())


    def test_pluggable_storage_invalid_construction(self):
        def cons():
            class _(Storage):
                def incr(self, key, expiry, elastic_expiry=False):
                    return

                def get(self, key):
                    return 0

                def get_expiry(self, key):
                    return time.time()

        self.assertRaises(ConfigurationError, cons)

    def test_pluggable_storage_no_moving_window(self):
        class MyStorage(Storage):
            STORAGE_SCHEME = ["mystorage"]

            def incr(self, key, expiry, elastic_expiry=False):
                return

            def get(self, key):
                return 0

            def get_expiry(self, key):
                return time.time()

        storage = storage_from_string("mystorage://")
        self.assertTrue(isinstance(storage, MyStorage))
        self.assertRaises(
            NotImplementedError, MovingWindowRateLimiter, storage
        )

    def test_pluggable_storage_moving_window(self):
        class MyStorage(Storage):
            STORAGE_SCHEME = ["mystorage"]

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

class MemoryStorageTests(unittest.TestCase):
    def setUp(self):
        self.storage = MemoryStorage()

    def test_in_memory(self):
        with hiro.Timeline().freeze() as timeline:
            limiter = FixedWindowRateLimiter(self.storage)
            per_min = RateLimitItemPerMinute(10)
            for i in range(0, 10):
                self.assertTrue(limiter.hit(per_min))
            self.assertFalse(limiter.hit(per_min))
            timeline.forward(61)
            self.assertTrue(limiter.hit(per_min))

    def test_in_memory_fixed_window_clear(self):
        storage = MemoryStorage()
        limiter = FixedWindowRateLimiter(self.storage)
        per_min = RateLimitItemPerMinute(1)
        limiter.hit(per_min)
        self.assertFalse(limiter.hit(per_min))
        limiter.clear(per_min)
        self.assertTrue(limiter.hit(per_min))

    def test_in_memory_moving_window_clear(self):
        limiter = MovingWindowRateLimiter(self.storage)
        per_min = RateLimitItemPerMinute(1)
        limiter.hit(per_min)
        self.assertFalse(limiter.hit(per_min))
        limiter.clear(per_min)
        self.assertTrue(limiter.hit(per_min))

    def test_in_memory_reset(self):
        limiter = FixedWindowRateLimiter(self.storage)
        per_min = RateLimitItemPerMinute(10)
        for i in range(0, 10):
            self.assertTrue(limiter.hit(per_min))
        self.assertFalse(limiter.hit(per_min))
        self.storage.reset()
        for i in range(0, 10):
            self.assertTrue(limiter.hit(per_min))
        self.assertFalse(limiter.hit(per_min))

    def test_in_memory_expiry(self):
        with hiro.Timeline().freeze() as timeline:
            limiter = FixedWindowRateLimiter(self.storage)
            per_min = RateLimitItemPerMinute(10)
            for i in range(0, 10):
                self.assertTrue(limiter.hit(per_min))
            timeline.forward(60)
            # touch another key and yield
            limiter.hit(RateLimitItemPerSecond(1))
            time.sleep(0.1)
            self.assertTrue(per_min.key_for() not in self.storage.storage)

    def test_in_memory_expiry_moving_window(self):
        with hiro.Timeline().freeze() as timeline:
            limiter = MovingWindowRateLimiter(self.storage)
            per_min = RateLimitItemPerMinute(10)
            per_sec = RateLimitItemPerSecond(1)
            for _ in range(0, 2):
                for _ in range(0, 10):
                    self.assertTrue(limiter.hit(per_min))
                timeline.forward(60)
                self.assertTrue(limiter.hit(per_sec))
                timeline.forward(1)
                time.sleep(0.1)
                self.assertEqual([], self.storage.events[per_min.key_for()])


class RedisStorageTests(unittest.TestCase):
    def setUp(self):
        self.storage_url = "redis://localhost:6379"
        self.storage = RedisStorage(self.storage_url)
        redis.Redis().flushall()

    def test_redis(self):
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
        self.assertTrue(limiter.hit(per_second))

    def test_redis_options(self):
        with mock.patch("limits.storage.get_dependency") as get_dependency:
            storage_from_string(self.storage_url, connection_timeout=1)
            self.assertEqual(
                get_dependency().from_url.call_args[1]['connection_timeout'], 1
            )

    def test_redis_reset(self):
        limiter = FixedWindowRateLimiter(self.storage)
        for i in range(0, 100):
            rate = RateLimitItemPerMinute(i)
            limiter.hit(rate)
        self.assertEqual(self.storage.reset(), 100)

    def test_redis_fixed_window_clear(self):
        limiter = FixedWindowRateLimiter(self.storage)
        per_min = RateLimitItemPerMinute(1)
        limiter.hit(per_min)
        self.assertFalse(limiter.hit(per_min))
        limiter.clear(per_min)
        self.assertTrue(limiter.hit(per_min))

    def test_redis_moving_window_clear(self):
        limiter = MovingWindowRateLimiter(self.storage)
        per_min = RateLimitItemPerMinute(1)
        limiter.hit(per_min)
        self.assertFalse(limiter.hit(per_min))
        limiter.clear(per_min)
        self.assertTrue(limiter.hit(per_min))

    def test_large_dataset_redis_moving_window_expiry(self):
        limiter = MovingWindowRateLimiter(self.storage)
        limit = RateLimitItemPerSecond(1000)
        # 100 routes
        fake_routes = [uuid4().hex for _ in range(0, 100)]
        # go as fast as possible in 2 seconds.
        start = time.time()

        def smack(e):
            while not e.is_set():
                self.assertTrue(limiter.hit(limit, random.choice(fake_routes)))

        events = [threading.Event() for _ in range(0, 100)]
        threads = [threading.Thread(target=smack, args=(e, )) for e in events]
        [k.start() for k in threads]
        while time.time() - start < 2:
            time.sleep(0.1)
        [k.set() for k in events]
        time.sleep(2)
        self.assertTrue(self.storage.storage.keys("%s/*" % limit.namespace) == [])


class RedisUnixSocketStorageTests(RedisStorageTests):
    def setUp(self):
        self.storage_url = "redis+unix:///var/tmp/limits.redis.sock"
        self.storage = RedisStorage(self.storage_url)
        redis.from_url('unix:///var/tmp/limits.redis.sock').flushall()


class RedisSentinelStorageTests(unittest.TestCase):
    def setUp(self):
        self.storage_url = 'redis+sentinel://localhost:26379'
        self.service_name = 'localhost-redis-sentinel'
        redis.sentinel.Sentinel([
            ("localhost", 26379)
        ]).master_for(self.service_name).flushall()

    def test_redis_sentinel_options(self):
        with mock.patch("limits.storage.get_dependency") as get_dependency:
            storage_from_string(self.storage_url+'/'+self.service_name, connection_timeout=1)
            self.assertEqual(
                get_dependency().Sentinel.call_args[1]['connection_timeout'], 1
            )
    def test_redis_sentinel(self):
        storage = RedisSentinelStorage(
            self.storage_url,
            service_name=self.service_name
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

    def test_redis_sentinel_reset(self):
        storage = RedisSentinelStorage(
            "redis+sentinel://localhost:26379",
            service_name="localhost-redis-sentinel"
        )
        limiter = FixedWindowRateLimiter(storage)
        for i in range(0, 10000):
            rate = RateLimitItemPerMinute(i)
            limiter.hit(rate)
        self.assertEqual(storage.reset(), 10000)

    def test_large_dataset_redis_sentinel_moving_window_expiry(self):
        storage = RedisSentinelStorage(
            "redis+sentinel://localhost:26379",
            service_name="localhost-redis-sentinel"
        )
        limiter = MovingWindowRateLimiter(storage)
        limit = RateLimitItemPerSecond(1000)
        # 100 routes
        fake_routes = [uuid4().hex for _ in range(0, 100)]
        # go as fast as possible in 2 seconds.
        start = time.time()

        def smack(e):
            while not e.is_set():
                self.assertTrue(limiter.hit(limit, random.choice(fake_routes)))

        events = [threading.Event() for _ in range(0, 100)]
        threads = [threading.Thread(target=smack, args=(e, )) for e in events]
        [k.start() for k in threads]
        while time.time() - start < 2:
            time.sleep(0.1)
        [k.set() for k in events]
        time.sleep(2)
        self.assertTrue(
            storage.sentinel.slave_for("localhost-redis-sentinel")
            .keys("%s/*" % limit.namespace) == []
        )


class RedisClusterStorageTests(unittest.TestCase):
    def setUp(self):
        rediscluster.RedisCluster("localhost", 7000).flushall()

    def test_redis_cluster(self):
        storage = RedisClusterStorage("redis+cluster://localhost:7000")
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

    def test_redis_cluster_reset(self):
        storage = RedisClusterStorage("redis+cluster://localhost:7000")
        limiter = FixedWindowRateLimiter(storage)
        for i in range(0, 10000):
            rate = RateLimitItemPerMinute(i)
            limiter.hit(rate)
        self.assertEqual(storage.reset(), 10000)

    def test_redis_cluster_clear(self):
        storage = RedisClusterStorage("redis+cluster://localhost:7000")
        limiter = MovingWindowRateLimiter(storage)
        per_min = RateLimitItemPerMinute(1)
        limiter.hit(per_min)
        self.assertFalse(limiter.hit(per_min))
        limiter.clear(per_min)
        self.assertTrue(limiter.hit(per_min))

    def test_large_dataset_redis_cluster_moving_window_expiry(self):
        storage = RedisClusterStorage("redis+cluster://localhost:7000")
        limiter = MovingWindowRateLimiter(storage)
        limit = RateLimitItemPerSecond(1000)
        # 100 routes
        fake_routes = [uuid4().hex for _ in range(0, 100)]
        # go as fast as possible in 2 seconds.
        start = time.time()

        def smack(e):
            while not e.is_set():
                self.assertTrue(limiter.hit(limit, random.choice(fake_routes)))

        events = [threading.Event() for _ in range(0, 100)]
        threads = [threading.Thread(target=smack, args=(e, )) for e in events]
        [k.start() for k in threads]
        while time.time() - start < 2:
            time.sleep(0.1)
        [k.set() for k in events]
        time.sleep(2)
        self.assertTrue(storage.storage.keys("%s/*" % limit.namespace) == [])


class MemcachedStorageTests(unittest.TestCase):
    def setUp(self):
        pymemcache.client.Client(('localhost', 22122)).flush_all()
        self.storage_url = 'memcached://localhost:22122'

    def test_options(self):
        with mock.patch("limits.storage.get_dependency") as get_dependency:
            storage_from_string(self.storage_url, connect_timeout=1).check()
            self.assertEqual(
                get_dependency().Client.call_args[1]['connect_timeout'], 1
            )

    def test_memcached(self):
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

    def test_memcached_clear(self):
        storage = MemcachedStorage("memcached://localhost:22122")
        limiter = FixedWindowRateLimiter(storage)
        per_min = RateLimitItemPerMinute(1)
        limiter.hit(per_min)
        self.assertFalse(limiter.hit(per_min))
        limiter.clear(per_min)
        self.assertTrue(limiter.hit(per_min))


class GAEMemcachedStorageTests(unittest.TestCase):
    def setUp(self):
        if RUN_GAE:
            from google.appengine.ext import testbed
            tb = testbed.Testbed()
            tb.activate()
            tb.init_memcache_stub()

    @skip_if(not RUN_GAE)
    def test_gae_memcached(self):
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
