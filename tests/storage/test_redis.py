import time

import pytest
import redis

from limits import RateLimitItemPerMinute, RateLimitItemPerSecond
from limits.storage import RedisStorage, storage_from_string
from limits.strategies import FixedWindowRateLimiter, MovingWindowRateLimiter


class SharedRedisTests:
    def test_fixed_window(self):
        limiter = FixedWindowRateLimiter(self.storage)
        per_second = RateLimitItemPerSecond(10)
        start = time.time()
        count = 0

        while time.time() - start < 0.5 and count < 10:
            assert limiter.hit(per_second)
            count += 1
        assert not limiter.hit(per_second)

        while time.time() - start <= 1:
            time.sleep(0.1)
        assert all(limiter.hit(per_second) for _ in range(10))

    def test_reset(self):
        limiter = FixedWindowRateLimiter(self.storage)

        for i in range(0, 10):
            rate = RateLimitItemPerMinute(i)
            limiter.hit(rate)
        assert self.storage.reset() == 10

    def test_fixed_window_clear(self):
        limiter = FixedWindowRateLimiter(self.storage)
        per_min = RateLimitItemPerMinute(1)
        limiter.hit(per_min)
        assert not limiter.hit(per_min)
        limiter.clear(per_min)
        assert limiter.hit(per_min)

    def test_moving_window_clear(self):
        limiter = MovingWindowRateLimiter(self.storage)
        per_min = RateLimitItemPerMinute(1)
        limiter.hit(per_min)
        assert not limiter.hit(per_min)
        limiter.clear(per_min)
        assert limiter.hit(per_min)

    def test_moving_window_expiry(self):
        limiter = MovingWindowRateLimiter(self.storage)
        limit = RateLimitItemPerSecond(1)
        assert limiter.hit(limit)
        assert not limiter.hit(limit)
        time.sleep(1.1)
        assert self.storage.storage.keys("%s/*" % limit.namespace) == []


@pytest.mark.redis
class TestRedisAuthStorage(SharedRedisTests):
    @pytest.fixture(autouse=True)
    def setup(self, redis_auth):
        self.storage_url = "redis://:sekret@localhost:7389"
        self.storage = RedisStorage(self.storage_url)


@pytest.mark.redis
class TestRedisStorage(SharedRedisTests):
    @pytest.fixture(autouse=True)
    def setup(self, redis_basic):
        self.storage_url = "redis://localhost:7379"
        self.storage = RedisStorage(self.storage_url)

    def test_init_options(self, mocker):
        from_url = mocker.spy(redis, "from_url")
        assert storage_from_string(self.storage_url, socket_timeout=1).check()
        assert from_url.call_args[1]["socket_timeout"] == 1

    def test_custom_connection_pool(self):
        pool = redis.connection.BlockingConnectionPool.from_url(self.storage_url)
        storage = storage_from_string("redis://", connection_pool=pool)

        assert storage.check()


@pytest.mark.redis
class TestRedisUnixSocketStorage(SharedRedisTests):
    @pytest.fixture(autouse=True)
    def setup(self, redis_uds):
        self.storage_url = "redis+unix:///tmp/limits.redis.sock"
        self.storage = RedisStorage(self.storage_url)

    def test_init_options(self, mocker):
        from_url = mocker.spy(redis, "from_url")
        assert storage_from_string(self.storage_url, socket_timeout=1).check()
        assert from_url.call_args[1]["socket_timeout"] == 1


@pytest.mark.redis
class TestRedisSSLStorage(SharedRedisTests):
    @pytest.fixture(autouse=True)
    def setup(self, redis_ssl):
        self.storage_url = (
            "rediss://localhost:8379/0?ssl_cert_reqs=required"
            "&ssl_keyfile=./tests/tls/client.key"
            "&ssl_certfile=./tests/tls/client.crt"
            "&ssl_ca_certs=./tests/tls/ca.crt"
        )
        self.storage = RedisStorage(self.storage_url)

    def test_init_options(self, mocker):
        from_url = mocker.spy(redis, "from_url")
        assert storage_from_string(self.storage_url, socket_timeout=1).check()
        assert from_url.call_args[1]["socket_timeout"] == 1
