import time

import pytest

from limits import RateLimitItemPerMinute, RateLimitItemPerSecond
from limits.errors import ConfigurationError, StorageError
from limits.storage import (
    EtcdStorage,
    MemcachedStorage,
    MemoryStorage,
    MongoDBStorage,
    MovingWindowSupport,
    RedisClusterStorage,
    RedisSentinelStorage,
    RedisStorage,
    Storage,
    storage_from_string,
)
from limits.strategies import MovingWindowRateLimiter
from tests.utils import fixed_start


class TestBaseStorage:
    @pytest.mark.parametrize(
        "uri, args", [("blah://", {}), ("redis+sentinel://localhost:26379", {})]
    )
    def test_invalid_storage_string(self, uri, args):
        with pytest.raises(ConfigurationError):
            storage_from_string(uri, **args)

    def test_pluggable_storage_no_moving_window(self):
        class MyStorage(Storage):
            STORAGE_SCHEME = ["mystorage"]

            @property
            def base_exceptions(self):
                return ValueError

            def incr(self, key, expiry, elastic_expiry=False):
                return

            def get(self, key):
                return 0

            def get_expiry(self, key):
                return time.time()

            def reset(self):
                return

            def check(self):
                return

            def clear(self):
                return

        storage = storage_from_string("mystorage://")
        assert isinstance(storage, MyStorage)
        with pytest.raises(NotImplementedError):
            MovingWindowRateLimiter(storage)

    def test_pluggable_storage_moving_window(self):
        class MyStorage(Storage):
            STORAGE_SCHEME = ["mystorage"]

            @property
            def base_exceptions(self):
                return ValueError

            def incr(self, key, expiry, elastic_expiry=False):
                return

            def get(self, key):
                return 0

            def get_expiry(self, key):
                return time.time()

            def reset(self):
                return

            def check(self):
                return

            def clear(self):
                return

            def acquire_entry(self, *a, **k):
                return True

            def get_moving_window(self, *a, **k):
                return (time.time(), 1)

        storage = storage_from_string("mystorage://")
        assert isinstance(storage, MyStorage)
        MovingWindowRateLimiter(storage)


@pytest.mark.parametrize(
    "uri, args, expected_instance, fixture",
    [
        pytest.param("memory://", {}, MemoryStorage, None, id="in-memory"),
        pytest.param(
            "redis://localhost:7379",
            {},
            RedisStorage,
            pytest.lazy_fixture("redis_basic"),
            marks=pytest.mark.redis,
            id="redis",
        ),
        pytest.param(
            "redis+unix:///tmp/limits.redis.sock",
            {},
            RedisStorage,
            pytest.lazy_fixture("redis_uds"),
            marks=pytest.mark.redis,
            id="redis-uds",
        ),
        pytest.param(
            "redis+unix://:password/tmp/limits.redis.sock",
            {},
            RedisStorage,
            pytest.lazy_fixture("redis_uds"),
            marks=pytest.mark.redis,
            id="redis-uds-auth",
        ),
        pytest.param(
            "memcached://localhost:22122",
            {},
            MemcachedStorage,
            pytest.lazy_fixture("memcached"),
            marks=pytest.mark.memcached,
            id="memcached",
        ),
        pytest.param(
            "memcached://localhost:22122,localhost:22123",
            {},
            MemcachedStorage,
            pytest.lazy_fixture("memcached_cluster"),
            marks=pytest.mark.memcached,
            id="memcached-cluster",
        ),
        pytest.param(
            "memcached:///tmp/limits.memcached.sock",
            {},
            MemcachedStorage,
            pytest.lazy_fixture("memcached_uds"),
            marks=pytest.mark.memcached,
            id="memcached-uds",
        ),
        pytest.param(
            "redis+sentinel://localhost:26379",
            {"service_name": "mymaster"},
            RedisSentinelStorage,
            pytest.lazy_fixture("redis_sentinel"),
            marks=pytest.mark.redis_sentinel,
            id="redis-sentinel",
        ),
        pytest.param(
            "redis+sentinel://localhost:26379/mymaster",
            {},
            RedisSentinelStorage,
            pytest.lazy_fixture("redis_sentinel"),
            marks=pytest.mark.redis_sentinel,
            id="redis-sentinel-service-name-url",
        ),
        pytest.param(
            "redis+sentinel://:sekret@localhost:36379/mymaster",
            {"password": "sekret"},
            RedisSentinelStorage,
            pytest.lazy_fixture("redis_sentinel_auth"),
            marks=pytest.mark.redis_sentinel,
            id="redis-sentinel-auth",
        ),
        pytest.param(
            "redis+cluster://localhost:7001/",
            {},
            RedisClusterStorage,
            pytest.lazy_fixture("redis_cluster"),
            marks=pytest.mark.redis_cluster,
            id="redis-cluster",
        ),
        pytest.param(
            "redis+cluster://:sekret@localhost:8400/",
            {},
            RedisClusterStorage,
            pytest.lazy_fixture("redis_auth_cluster"),
            marks=pytest.mark.redis_cluster,
            id="redis-cluster-auth",
        ),
        pytest.param(
            "mongodb://localhost:37017/",
            {},
            MongoDBStorage,
            pytest.lazy_fixture("mongodb"),
            marks=pytest.mark.mongodb,
            id="mongodb",
        ),
        pytest.param(
            "etcd://localhost:2379",
            {},
            EtcdStorage,
            pytest.lazy_fixture("etcd"),
            marks=pytest.mark.etcd,
            id="etcd",
        ),
    ],
)
class TestConcreteStorages:
    def test_storage_string(self, uri, args, expected_instance, fixture):
        assert isinstance(storage_from_string(uri, **args), expected_instance)

    @fixed_start
    def test_expiry_incr(self, uri, args, expected_instance, fixture):
        storage = storage_from_string(uri, **args)
        limit = RateLimitItemPerSecond(1)
        storage.incr(limit.key_for(), limit.get_expiry())
        time.sleep(1.1)
        assert storage.get(limit.key_for()) == 0

    @fixed_start
    def test_expiry_acquire_entry(self, uri, args, expected_instance, fixture):
        if not issubclass(expected_instance, MovingWindowSupport):
            pytest.skip("%s does not support acquire entry" % expected_instance)
        storage = storage_from_string(uri, **args)
        limit = RateLimitItemPerSecond(1)
        assert storage.acquire_entry(limit.key_for(), limit.amount, limit.get_expiry())
        time.sleep(1.1)
        assert storage.get(limit.key_for()) == 0

    def test_incr_custom_amount(self, uri, args, expected_instance, fixture):
        storage = storage_from_string(uri, **args)
        limit = RateLimitItemPerMinute(1)
        assert 1 == storage.incr(limit.key_for(), limit.get_expiry(), amount=1)
        assert 11 == storage.incr(limit.key_for(), limit.get_expiry(), amount=10)

    def test_acquire_entry_custom_amount(self, uri, args, expected_instance, fixture):
        if not issubclass(expected_instance, MovingWindowSupport):
            pytest.skip("%s does not support acquire entry" % expected_instance)
        storage = storage_from_string(uri, **args)
        limit = RateLimitItemPerMinute(10)
        assert not storage.acquire_entry(
            limit.key_for(), limit.amount, limit.get_expiry(), amount=11
        )
        assert storage.acquire_entry(
            limit.key_for(), limit.amount, limit.get_expiry(), amount=1
        )
        assert not storage.acquire_entry(
            limit.key_for(), limit.amount, limit.get_expiry(), amount=10
        )

    def test_storage_check(self, uri, args, expected_instance, fixture):
        assert storage_from_string(uri, **args).check()

    def test_storage_reset(self, uri, args, expected_instance, fixture):
        if expected_instance == MemcachedStorage:
            pytest.skip("Reset not supported for memcached")
        limit1 = RateLimitItemPerMinute(10)  # default namespace, LIMITER
        limit2 = RateLimitItemPerMinute(10, namespace="OTHER")
        storage = storage_from_string(uri, **args)
        for i in range(10):
            storage.incr(limit1.key_for(str(i)), limit1.get_expiry())
            storage.incr(limit2.key_for(str(i)), limit2.get_expiry())
        assert storage.reset() == 20

    def test_storage_clear(self, uri, args, expected_instance, fixture):
        limit = RateLimitItemPerMinute(10)
        storage = storage_from_string(uri, **args)
        storage.incr(limit.key_for(), limit.get_expiry())
        assert 1 == storage.get(limit.key_for())
        storage.clear(limit.key_for())
        assert 0 == storage.get(limit.key_for())


@pytest.mark.parametrize("wrap_exceptions", (True, False))
class TestStorageErrors:
    class MyStorage(Storage, MovingWindowSupport):
        STORAGE_SCHEME = ["mystorage"]

        class MyError(Exception):
            pass

        @property
        def base_exceptions(self):
            return self.MyError

        def incr(self, key, expiry, elastic_expiry=False, amount=1):
            raise self.MyError()

        def get(self, key):
            raise self.MyError()

        def get_expiry(self, key):
            raise self.MyError()

        def reset(self):
            raise self.MyError()

        def check(self):
            raise self.MyError()

        def clear(self, key):
            raise self.MyError()

        def acquire_entry(self, key, limit, expiry, amount=1):
            raise self.MyError()

        def get_moving_window(self, key, limit, expiry):
            raise self.MyError()

    def assert_exception(self, exc, wrap_exceptions):
        if wrap_exceptions:
            assert isinstance(exc, StorageError)
            assert isinstance(exc.storage_error, self.MyStorage.MyError)
        else:
            assert isinstance(exc, self.MyStorage.MyError)

    def test_incr_exception(self, wrap_exceptions):
        with pytest.raises(Exception) as exc:
            self.MyStorage(wrap_exceptions=wrap_exceptions).incr("", 1)

        self.assert_exception(exc.value, wrap_exceptions)

    def test_get_exception(self, wrap_exceptions):
        with pytest.raises(Exception) as exc:
            self.MyStorage(wrap_exceptions=wrap_exceptions).get("")

        self.assert_exception(exc.value, wrap_exceptions)

    def test_get_expiry_exception(self, wrap_exceptions):
        with pytest.raises(Exception) as exc:
            self.MyStorage(wrap_exceptions=wrap_exceptions).get_expiry("")

        self.assert_exception(exc.value, wrap_exceptions)

    def test_reset_exception(self, wrap_exceptions):
        with pytest.raises(Exception) as exc:
            self.MyStorage(wrap_exceptions=wrap_exceptions).reset()

        self.assert_exception(exc.value, wrap_exceptions)

    def test_check_exception(self, wrap_exceptions):
        with pytest.raises(Exception) as exc:
            self.MyStorage(wrap_exceptions=wrap_exceptions).check()

        self.assert_exception(exc.value, wrap_exceptions)

    def test_clear_exception(self, wrap_exceptions):
        with pytest.raises(Exception) as exc:
            self.MyStorage(wrap_exceptions=wrap_exceptions).clear("")

        self.assert_exception(exc.value, wrap_exceptions)

    def test_acquire_entry_exception(self, wrap_exceptions):
        with pytest.raises(Exception) as exc:
            self.MyStorage(wrap_exceptions=wrap_exceptions).acquire_entry("", 1, 1)

        self.assert_exception(exc.value, wrap_exceptions)

    def test_get_moving_window_exception(self, wrap_exceptions):
        with pytest.raises(Exception) as exc:
            self.MyStorage(wrap_exceptions=wrap_exceptions).get_moving_window("", 1, 1)

        self.assert_exception(exc.value, wrap_exceptions)
