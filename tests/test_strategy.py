import threading
import time

import hiro
import pytest

from limits.limits import RateLimitItemPerMinute, RateLimitItemPerSecond
from limits.storage import (
    MemcachedStorage,
    MemoryStorage,
    MongoDBStorage,
    RedisSentinelStorage,
    RedisStorage,
)
from limits.strategies import (
    FixedWindowElasticExpiryRateLimiter,
    FixedWindowRateLimiter,
    MovingWindowRateLimiter,
)


class TestWindow:
    def test_fixed_window(self):
        storage = MemoryStorage()
        limiter = FixedWindowRateLimiter(storage)
        with hiro.Timeline().freeze() as timeline:
            start = int(time.time())
            limit = RateLimitItemPerSecond(10, 2)
            assert all([limiter.hit(limit) for _ in range(0, 10)])
            timeline.forward(1)
            assert not limiter.hit(limit)
            assert limiter.get_window_stats(limit)[1] == 0
            assert limiter.get_window_stats(limit)[0] == start + 2
            timeline.forward(1)
            assert limiter.get_window_stats(limit)[1] == 10
            assert limiter.hit(limit)

    @pytest.mark.flaky
    def test_fixed_window_with_elastic_expiry_in_memory(self):
        storage = MemoryStorage()
        limiter = FixedWindowElasticExpiryRateLimiter(storage)
        with hiro.Timeline().freeze() as timeline:
            start = int(time.time())
            limit = RateLimitItemPerSecond(10, 2)
            assert all([limiter.hit(limit) for _ in range(0, 10)])
            timeline.forward(1)
            assert not limiter.hit(limit)
            assert limiter.get_window_stats(limit)[1] == 0
            # three extensions to the expiry
            assert limiter.get_window_stats(limit)[0] == start + 3
            timeline.forward(1)
            assert not limiter.hit(limit)
            timeline.forward(3)
            start = int(time.time())
            assert limiter.hit(limit)
            assert limiter.get_window_stats(limit)[1] == 9
            assert limiter.get_window_stats(limit)[0] == start + 2

    @pytest.mark.flaky
    def test_fixed_window_with_elastic_expiry_memcache(self, memcached):
        storage = MemcachedStorage("memcached://localhost:22122")
        limiter = FixedWindowElasticExpiryRateLimiter(storage)
        limit = RateLimitItemPerSecond(10, 2)
        assert all([limiter.hit(limit) for _ in range(0, 10)])
        time.sleep(1)
        assert not limiter.hit(limit)
        time.sleep(1)
        assert not limiter.hit(limit)

    @pytest.mark.flaky
    def test_fixed_window_with_elastic_expiry_memcache_concurrency(self, memcached):
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
        assert limiter.get_window_stats(limit)[1] == 0
        assert start + 2 <= limiter.get_window_stats(limit)[0] <= start + 3
        assert storage.get(limit.key_for()) == 10

    def test_fixed_window_with_elastic_expiry_mongo(self, mongodb):
        storage = MongoDBStorage("mongodb://localhost:37017")
        limiter = FixedWindowElasticExpiryRateLimiter(storage)
        limit = RateLimitItemPerSecond(10, 2)
        assert all([limiter.hit(limit) for _ in range(0, 10)])
        time.sleep(1)
        assert not limiter.hit(limit)
        time.sleep(1)
        assert not limiter.hit(limit)
        assert limiter.get_window_stats(limit)[1] == 0

    def test_fixed_window_with_elastic_expiry_redis(self, redis_basic):
        storage = RedisStorage("redis://localhost:7379")
        limiter = FixedWindowElasticExpiryRateLimiter(storage)
        limit = RateLimitItemPerSecond(10, 2)
        assert all([limiter.hit(limit) for _ in range(0, 10)])
        time.sleep(1)
        assert not limiter.hit(limit)
        time.sleep(1)
        assert not limiter.hit(limit)
        assert limiter.get_window_stats(limit)[1] == 0

    def test_fixed_window_with_elastic_expiry_redis_sentinel(self, redis_sentinel):
        storage = RedisSentinelStorage(
            "redis+sentinel://localhost:26379", service_name="localhost-redis-sentinel"
        )
        limiter = FixedWindowElasticExpiryRateLimiter(storage)
        limit = RateLimitItemPerSecond(10, 2)
        assert all([limiter.hit(limit) for _ in range(0, 10)])
        time.sleep(1)
        assert not limiter.hit(limit)
        time.sleep(1)
        assert not limiter.hit(limit)
        assert limiter.get_window_stats(limit)[1] == 0

    def test_moving_window_in_memory(self):
        storage = MemoryStorage()
        limiter = MovingWindowRateLimiter(storage)
        with hiro.Timeline().freeze() as timeline:
            limit = RateLimitItemPerMinute(10)

            for i in range(0, 5):
                assert limiter.hit(limit)
                assert limiter.hit(limit)
                assert limiter.get_window_stats(limit)[1] == 10 - ((i + 1) * 2)
                timeline.forward(10)
            assert limiter.get_window_stats(limit)[1] == 0
            assert not limiter.hit(limit)
            timeline.forward(20)
            assert limiter.get_window_stats(limit)[1] == 2
            assert limiter.get_window_stats(limit)[0] == int(time.time() + 30)
            timeline.forward(31)
            assert limiter.get_window_stats(limit)[1] == 10

    def test_moving_window_redis(self, redis_basic):
        storage = RedisStorage("redis://localhost:7379")
        limiter = MovingWindowRateLimiter(storage)
        limit = RateLimitItemPerSecond(10, 2)

        for i in range(0, 10):
            assert limiter.hit(limit)
            assert limiter.get_window_stats(limit)[1] == 10 - (i + 1)
            time.sleep(2 * 0.095)
        assert not limiter.hit(limit)
        time.sleep(0.4)
        assert limiter.hit(limit)
        assert limiter.hit(limit)
        assert limiter.get_window_stats(limit)[1] == 0

    def test_moving_window_mongo(self, mongodb):
        storage = MongoDBStorage("mongodb://localhost:37017")
        limiter = MovingWindowRateLimiter(storage)
        with hiro.Timeline().freeze() as timeline:
            limit = RateLimitItemPerMinute(10)

            for i in range(0, 5):
                assert limiter.hit(limit)
                assert limiter.hit(limit)
                assert limiter.get_window_stats(limit)[1] == 10 - ((i + 1) * 2)
                timeline.forward(10)
            assert limiter.get_window_stats(limit)[1] == 0
            assert not limiter.hit(limit)
            timeline.forward(20)
            assert limiter.get_window_stats(limit)[1] == 2
            assert limiter.get_window_stats(limit)[0] == int(time.time() + 30)
            timeline.forward(31)
            assert limiter.get_window_stats(limit)[1] == 10

    def test_moving_window_memcached(self, memcached):
        storage = MemcachedStorage("memcached://localhost:22122")
        with pytest.raises(NotImplementedError):
            MovingWindowRateLimiter(storage)

    def test_test_fixed_window(self):
        with hiro.Timeline().freeze():
            store = MemoryStorage()
            limiter = FixedWindowRateLimiter(store)
            limit = RateLimitItemPerSecond(2, 1)
            assert limiter.hit(limit), store
            assert limiter.test(limit), store
            assert limiter.hit(limit), store
            assert not limiter.test(limit), store
            assert not limiter.hit(limit), store

    def test_test_moving_window(self):
        with hiro.Timeline().freeze():
            store = MemoryStorage()
            limit = RateLimitItemPerSecond(2, 1)
            limiter = MovingWindowRateLimiter(store)
            assert limiter.hit(limit), store
            assert limiter.test(limit), store
            assert limiter.hit(limit), store
            assert not limiter.test(limit), store
            assert not limiter.hit(limit), store
