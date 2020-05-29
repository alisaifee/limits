import time

import mock
import pymemcache.client
import redis
import redis.sentinel
import rediscluster

from limits.errors import ConfigurationError
from limits.storage import (
    MemoryStorage, RedisStorage, MemcachedStorage, RedisSentinelStorage,
    RedisClusterStorage, Storage, GAEMemcachedStorage, storage_from_string
)
from limits.strategies import (
    MovingWindowRateLimiter
)
from tests import RUN_GAE
import pytest


def setup_method():
    pymemcache.client.Client(('localhost', 22122)).flush_all()
    redis.from_url('unix:///tmp/limits.redis.sock').flushall()
    redis.from_url("redis://localhost:7379").flushall()
    redis.from_url("redis://:sekret@localhost:7389").flushall()
    redis.sentinel.Sentinel([
        ("localhost", 26379)
    ]).master_for("localhost-redis-sentinel").flushall()
    rediscluster.RedisCluster("localhost", 7000).flushall()
    if RUN_GAE:
        from google.appengine.ext import testbed
        tb = testbed.Testbed()
        tb.activate()
        tb.init_memcache_stub()


def test_storage_string():
    assert isinstance(storage_from_string("memory://"), MemoryStorage)
    assert isinstance(
        storage_from_string("redis://localhost:7379"), RedisStorage
    )
    assert isinstance(
        storage_from_string("redis+unix:///tmp/limits.redis.sock"),
        RedisStorage
    )

    assert isinstance(
        storage_from_string("redis+unix://:password/tmp/limits.redis.sock"),  # noqa: E501
        RedisStorage
    )

    assert isinstance(
        storage_from_string("memcached://localhost:22122"),
        MemcachedStorage
    )

    assert isinstance(
        storage_from_string("memcached://localhost:22122,localhost:22123"),  # noqa: E501
        MemcachedStorage
    )

    assert isinstance(
        storage_from_string("memcached:///tmp/limits.memcached.sock"),
        MemcachedStorage
    )

    assert isinstance(
        storage_from_string(
            "redis+sentinel://localhost:26379",
            service_name="localhost-redis-sentinel"
        ), RedisSentinelStorage
    )

    assert isinstance(
        storage_from_string(
            "redis+sentinel://localhost:26379/localhost-redis-sentinel"
        ), RedisSentinelStorage
    )

    assert isinstance(
        storage_from_string("redis+cluster://localhost:7000/"),
        RedisClusterStorage
    )

    if RUN_GAE:
        assert isinstance(
            storage_from_string("gaememcached://"),
            GAEMemcachedStorage
        )

    with pytest.raises(ConfigurationError):
        storage_from_string("blah://")

    with pytest.raises(ConfigurationError):
        storage_from_string("redis+sentinel://localhost:26379")

    with mock.patch(
            "limits.storage.redis_sentinel.get_dependency"
    ) as get_dependency:
        assert isinstance(
            storage_from_string("redis+sentinel://:foobared@localhost:26379/localhost-redis-sentinel"),  # noqa: E501
            RedisSentinelStorage
        )
        assert get_dependency().Sentinel.call_args[1]['password'] == 'foobared'


def test_storage_check():
    assert storage_from_string("memory://").check()
    assert storage_from_string("redis://localhost:7379").check()
    assert storage_from_string("redis://:sekret@localhost:7389").check()
    assert storage_from_string("redis+unix:///tmp/limits.redis.sock").check()
    assert storage_from_string("memcached://localhost:22122").check()
    assert storage_from_string(
        "memcached://localhost:22122,localhost:22123"
    ).check()
    assert storage_from_string(
        "memcached:///tmp/limits.memcached.sock"
    ).check()
    assert storage_from_string(
        "redis+sentinel://localhost:26379",
        service_name="localhost-redis-sentinel"
    ).check()
    assert storage_from_string("redis+cluster://localhost:7000").check()
    if RUN_GAE:
        assert storage_from_string("gaememcached://").check()


def test_pluggable_storage_invalid_construction():
    def cons():
        class _(Storage):
            def incr(self, key, expiry, elastic_expiry=False):
                return

            def get(self, key):
                return 0

            def get_expiry(self, key):
                return time.time()

    with pytest.raises(ConfigurationError):
        cons()


def test_pluggable_storage_no_moving_window():
    class MyStorage(Storage):
        STORAGE_SCHEME = ["mystorage"]

        def incr(self, key, expiry, elastic_expiry=False):
            return

        def get(self, key):
            return 0

        def get_expiry(self, key):
            return time.time()

    storage = storage_from_string("mystorage://")
    assert isinstance(storage, MyStorage)
    with pytest.raises(NotImplementedError):
        MovingWindowRateLimiter(storage)


def test_pluggable_storage_moving_window():
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
    assert isinstance(storage, MyStorage)
    MovingWindowRateLimiter(storage)
