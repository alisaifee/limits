import asyncio
import time

import pytest

from limits import RateLimitItemPerMinute, RateLimitItemPerSecond
from limits.aio.storage import RedisClusterStorage, RedisSentinelStorage, RedisStorage
from limits.aio.strategies import FixedWindowRateLimiter, MovingWindowRateLimiter
from limits.errors import ConfigurationError
from limits.storage import storage_from_string


@pytest.mark.asynchronous
class AsyncSharedRedisTests:
    @pytest.mark.asyncio
    async def test_fixed_window(self):
        limiter = FixedWindowRateLimiter(self.storage)
        per_second = RateLimitItemPerSecond(10)
        start = time.time()
        count = 0

        while time.time() - start < 0.5 and count < 10:
            assert await limiter.hit(per_second)
            count += 1
        assert not await limiter.hit(per_second)

        while time.time() - start <= 1:
            await asyncio.sleep(0.1)

        for _ in range(10):
            assert await limiter.hit(per_second)

    @pytest.mark.asyncio
    async def test_reset(self):
        limiter = FixedWindowRateLimiter(self.storage)

        for i in range(0, 10):
            rate = RateLimitItemPerMinute(i)
            await limiter.hit(rate)
        assert await self.storage.reset() == 10

    @pytest.mark.asyncio
    async def test_fixed_window_clear(self):
        limiter = FixedWindowRateLimiter(self.storage)
        per_min = RateLimitItemPerMinute(1)
        await limiter.hit(per_min)
        assert not await limiter.hit(per_min)
        await limiter.clear(per_min)
        assert await limiter.hit(per_min)

    @pytest.mark.asyncio
    async def test_moving_window_clear(self):
        limiter = MovingWindowRateLimiter(self.storage)
        per_min = RateLimitItemPerMinute(1)
        await limiter.hit(per_min)
        assert not await limiter.hit(per_min)
        await limiter.clear(per_min)
        assert await limiter.hit(per_min)

    @pytest.mark.asyncio
    async def test_moving_window_expiry(self):
        limiter = MovingWindowRateLimiter(self.storage)
        limit = RateLimitItemPerSecond(2)
        assert await limiter.hit(limit)
        await asyncio.sleep(0.9)
        assert await limiter.hit(limit)
        assert not await limiter.hit(limit)
        await asyncio.sleep(0.1)
        assert await limiter.hit(limit)
        last = time.time()

        while time.time() - last <= 1:
            await asyncio.sleep(0.05)
        assert await self.storage.storage.keys("%s/*" % limit.namespace) == []

    @pytest.mark.asyncio
    async def test_connectivity(self):
        assert await self.storage.check() is True


@pytest.mark.redis
class TestAsyncRedisStorage(AsyncSharedRedisTests):
    @pytest.fixture(autouse=True)
    def setup(self, redis_basic):
        self.real_storage_url = "redis://localhost:7379"
        self.storage_url = f"async+{self.real_storage_url}"
        self.storage = RedisStorage(self.storage_url)

    @pytest.mark.asyncio
    async def test_init_options(self, mocker):
        import coredis

        from_url = mocker.spy(coredis.StrictRedis, "from_url")
        assert await storage_from_string(self.storage_url, stream_timeout=1).check()
        assert (
            from_url.spy_return.connection_pool.connection_kwargs["stream_timeout"] == 1
        )


@pytest.mark.redis
class TestAsyncRedisUnixSocketStorage(AsyncSharedRedisTests):
    @pytest.fixture(autouse=True)
    def setup(self, redis_uds):
        self.storage_url = "async+redis+unix:///tmp/limits.redis.sock"
        self.storage = RedisStorage(self.storage_url)

    @pytest.mark.asyncio
    async def test_init_options(self, mocker):
        import coredis

        from_url = mocker.spy(coredis.StrictRedis, "from_url")
        assert await storage_from_string(self.storage_url, stream_timeout=1).check()
        assert (
            from_url.spy_return.connection_pool.connection_kwargs["stream_timeout"] == 1
        )


@pytest.mark.redis_cluster
class TestAsyncRedisClusterStorage(AsyncSharedRedisTests):
    @pytest.fixture(autouse=True)
    def setup(self, redis_cluster):
        self.storage_url = "redis+cluster://localhost:7001"
        self.storage = RedisClusterStorage(f"async+{self.storage_url}")

    @pytest.mark.asyncio
    async def test_init_options(self, mocker):
        import coredis

        constructor = mocker.spy(coredis, "StrictRedisCluster")
        assert await storage_from_string(
            f"async+{self.storage_url}", max_connections=10
        ).check()
        assert constructor.call_args[1]["max_connections"] == 10


@pytest.mark.redis_sentinel
class TestAsyncRedisSentinelStorage(AsyncSharedRedisTests):
    @pytest.fixture(autouse=True)
    def setup(self, redis_sentinel):
        self.storage_url = "redis+sentinel://localhost:26379"
        self.service_name = "localhost-redis-sentinel"
        self.storage = RedisSentinelStorage(
            f"async+{self.storage_url}", service_name=self.service_name
        )

    @pytest.mark.asyncio
    async def test_init_no_service_name(self, mocker):
        lib = mocker.Mock()
        mocker.patch("limits.util.get_dependency", return_value=lib)
        with pytest.raises(ConfigurationError):
            await storage_from_string(f"async+{self.storage_url}", stream_timeout=1)

    @pytest.mark.asyncio
    async def test_init_options(self, mocker):
        import coredis

        constructor = mocker.spy(coredis.sentinel, "Sentinel")
        assert await storage_from_string(
            f"async+{self.storage_url}/{self.service_name}",
            stream_timeout=42,
            sentinel_kwargs={"stream_timeout": 1},
        ).check()
        assert constructor.call_args[1]["sentinel_kwargs"]["stream_timeout"] == 1
        assert constructor.call_args[1]["stream_timeout"] == 42

    @pytest.mark.parametrize(
        "username, password, opts",
        [
            ("", "", {}),
            ("username", "", {"username": "username"}),
            ("", "sekret", {"password": "sekret"}),
        ],
    )
    @pytest.mark.asyncio
    async def test_auth(self, mocker, username, password, opts):
        lib = mocker.Mock()
        mocker.patch("limits.util.get_dependency", return_value=lib)
        storage_url = (
            f"async+redis+sentinel://{username}:{password}@localhost:26379/service_name"
        )
        storage_from_string(storage_url)
        assert lib.Sentinel.call_args[1]["sentinel_kwargs"] == opts

    @pytest.mark.parametrize(
        "username, sentinel_password, password, success",
        [
            ("", "", "", False),
            ("username", "", "", False),
            ("", "", "sekret", False),
            ("", "sekret", "", True),
            ("", "sekret", "sekret", True),
        ],
    )
    @pytest.mark.asyncio
    async def test_auth_connect(
        self, username, sentinel_password, password, success, redis_sentinel_auth
    ):
        storage_url = (
            f"async+redis+sentinel://{username}:{sentinel_password}@localhost:36379/"
            "localhost-redis-sentinel"
        )
        args = {}
        if password:
            args["password"] = password
        assert success == await storage_from_string(storage_url, **args).check()
