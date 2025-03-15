from __future__ import annotations

import asyncio
import contextlib
import functools
import math
import os
import time

import pytest
from pytest_lazy_fixtures import lf

from limits.limits import RateLimitItem

ASYNC_REDIS_IMPLEMENTATION = os.environ.get("ASYNC_REDIS_IMPLEMENTATION", "coredis")


def fixed_start(fn):
    @functools.wraps(fn)
    def __inner(*a, **k):
        start = time.time()

        while time.time() < math.ceil(start):
            time.sleep(0.01)

        return fn(*a, **k)

    return __inner


def timestamp_based_key_ttl(item: RateLimitItem, now: float | None = None) -> float:
    """
    Return the current timestamp-based key TTL.

    Used for some implementations of thesliding window counter that generates keys based on the timestamp.

    Args:
        item (RateLimitItem): the rate limit item
        now (Optional[float], optional): the current timestamp. If None, generates the current timestamp
    """
    if now is None:
        now = time.time()
    return item.get_expiry() - (now % item.get_expiry())


def async_fixed_start(fn):
    @functools.wraps(fn)
    async def __inner(*a, **k):
        start = time.time()

        while time.time() < math.ceil(start):
            time.sleep(0.01)

        return await fn(*a, **k)

    return __inner


@contextlib.contextmanager
def window(delay_end: float, delay: float | None = None):
    start = time.time()

    if delay is not None:
        while time.time() - start < delay:
            time.sleep(0.001)
    yield (start, start + delay_end)

    while time.time() - start < delay_end:
        time.sleep(0.001)


@contextlib.asynccontextmanager
async def async_window(delay_end: float, delay: float | None = None):
    start = time.time()

    if delay is not None:
        while time.time() - start < delay:
            await asyncio.sleep(0.001)

    yield (start, start + delay_end)

    while time.time() - start < delay_end:
        await asyncio.sleep(0.001)


all_storage = pytest.mark.parametrize(
    "uri, args, fixture",
    [
        pytest.param("memory://", {}, None, marks=pytest.mark.memory, id="in-memory"),
        pytest.param(
            "redis://localhost:7379",
            {},
            lf("redis_basic"),
            marks=pytest.mark.redis,
            id="redis_basic",
        ),
        pytest.param(
            "memcached://localhost:22122",
            {},
            lf("memcached"),
            marks=[pytest.mark.memcached, pytest.mark.flaky],
            id="memcached",
        ),
        pytest.param(
            "memcached://localhost:22122,localhost:22123",
            {},
            lf("memcached_cluster"),
            marks=[pytest.mark.memcached, pytest.mark.flaky],
            id="memcached-cluster",
        ),
        pytest.param(
            "redis+cluster://localhost:7001/",
            {},
            lf("redis_cluster"),
            marks=pytest.mark.redis_cluster,
            id="redis-cluster",
        ),
        pytest.param(
            "redis+cluster://:sekret@localhost:8400/",
            {},
            lf("redis_auth_cluster"),
            marks=pytest.mark.redis_cluster,
            id="redis-cluster-auth",
        ),
        pytest.param(
            "redis+cluster://localhost:8301",
            {
                "ssl": True,
                "ssl_cert_reqs": "required",
                "ssl_keyfile": "./tests/tls/client.key",
                "ssl_certfile": "./tests/tls/client.crt",
                "ssl_ca_certs": "./tests/tls/ca.crt",
            },
            lf("redis_ssl_cluster"),
            marks=pytest.mark.redis_cluster,
            id="redis-ssl-cluster",
        ),
        pytest.param(
            "redis+sentinel://localhost:26379/mymaster",
            {"use_replicas": False},
            lf("redis_sentinel"),
            marks=pytest.mark.redis_sentinel,
            id="redis-sentinel",
        ),
        pytest.param(
            "mongodb://localhost:37017/",
            {},
            lf("mongodb"),
            marks=pytest.mark.mongodb,
            id="mongodb",
        ),
        pytest.param(
            "valkey://localhost:12379",
            {},
            lf("valkey_basic"),
            marks=pytest.mark.valkey,
            id="valkey_basic",
        ),
        pytest.param(
            "valkey+cluster://localhost:2001/",
            {},
            lf("valkey_cluster"),
            marks=pytest.mark.valkey_cluster,
            id="valkey-cluster",
        ),
    ],
)

moving_window_storage = pytest.mark.parametrize(
    "uri, args, fixture",
    [
        pytest.param("memory://", {}, None, marks=pytest.mark.memory, id="in-memory"),
        pytest.param(
            "redis://localhost:7379",
            {},
            lf("redis_basic"),
            marks=pytest.mark.redis,
            id="redis",
        ),
        pytest.param(
            "redis+cluster://localhost:7001/",
            {},
            lf("redis_cluster"),
            marks=pytest.mark.redis_cluster,
            id="redis-cluster",
        ),
        pytest.param(
            "redis+cluster://:sekret@localhost:8400/",
            {},
            lf("redis_auth_cluster"),
            marks=pytest.mark.redis_cluster,
            id="redis-cluster-auth",
        ),
        pytest.param(
            "redis+cluster://localhost:8301",
            {
                "ssl": True,
                "ssl_cert_reqs": "required",
                "ssl_keyfile": "./tests/tls/client.key",
                "ssl_certfile": "./tests/tls/client.crt",
                "ssl_ca_certs": "./tests/tls/ca.crt",
            },
            lf("redis_ssl_cluster"),
            marks=pytest.mark.redis_cluster,
            id="redis-ssl-cluster",
        ),
        pytest.param(
            "redis+sentinel://localhost:26379/mymaster",
            {"use_replicas": False},
            lf("redis_sentinel"),
            marks=pytest.mark.redis_sentinel,
            id="redis-sentinel",
        ),
        pytest.param(
            "mongodb://localhost:37017/",
            {},
            lf("mongodb"),
            marks=pytest.mark.mongodb,
            id="mongodb",
        ),
        pytest.param(
            "valkey://localhost:12379",
            {},
            lf("valkey_basic"),
            marks=pytest.mark.valkey,
            id="valkey_basic",
        ),
        pytest.param(
            "valkey+cluster://localhost:2001/",
            {},
            lf("valkey_cluster"),
            marks=pytest.mark.valkey_cluster,
            id="valkey-cluster",
        ),
    ],
)

sliding_window_counter_storage = pytest.mark.parametrize(
    "uri, args, fixture",
    [
        pytest.param("memory://", {}, None, marks=pytest.mark.memory, id="in-memory"),
        pytest.param(
            "redis://localhost:7379",
            {},
            lf("redis_basic"),
            marks=pytest.mark.redis,
            id="redis",
        ),
        pytest.param(
            "memcached://localhost:22122",
            {},
            lf("memcached"),
            marks=[pytest.mark.memcached, pytest.mark.flaky],
            id="memcached",
        ),
        pytest.param(
            "memcached://localhost:22122,localhost:22123",
            {},
            lf("memcached_cluster"),
            marks=[pytest.mark.memcached, pytest.mark.flaky],
            id="memcached-cluster",
        ),
        pytest.param(
            "redis+cluster://localhost:7001/",
            {},
            lf("redis_cluster"),
            marks=pytest.mark.redis_cluster,
            id="redis-cluster",
        ),
        pytest.param(
            "redis+cluster://:sekret@localhost:8400/",
            {},
            lf("redis_auth_cluster"),
            marks=pytest.mark.redis_cluster,
            id="redis-cluster-auth",
        ),
        pytest.param(
            "redis+cluster://localhost:8301",
            {
                "ssl": True,
                "ssl_cert_reqs": "required",
                "ssl_keyfile": "./tests/tls/client.key",
                "ssl_certfile": "./tests/tls/client.crt",
                "ssl_ca_certs": "./tests/tls/ca.crt",
            },
            lf("redis_ssl_cluster"),
            marks=pytest.mark.redis_cluster,
            id="redis-ssl-cluster",
        ),
        pytest.param(
            "redis+sentinel://localhost:26379/mymaster",
            {"use_replicas": False},
            lf("redis_sentinel"),
            marks=pytest.mark.redis_sentinel,
            id="redis-sentinel",
        ),
        pytest.param(
            "mongodb://localhost:37017/",
            {},
            lf("mongodb"),
            marks=pytest.mark.mongodb,
            id="mongodb",
        ),
        pytest.param(
            "valkey://localhost:12379",
            {},
            lf("valkey_basic"),
            marks=pytest.mark.valkey,
            id="valkey_basic",
        ),
        pytest.param(
            "valkey+cluster://localhost:2001/",
            {},
            lf("valkey_cluster"),
            marks=pytest.mark.valkey_cluster,
            id="valkey-cluster",
        ),
    ],
)

async_all_storage = pytest.mark.parametrize(
    "uri, args, fixture",
    [
        pytest.param(
            "async+memory://", {}, None, marks=pytest.mark.memory, id="in-memory"
        ),
        pytest.param(
            "async+redis://localhost:7379",
            {
                "implementation": ASYNC_REDIS_IMPLEMENTATION,
            },
            lf("redis_basic"),
            marks=pytest.mark.redis,
            id="redis",
        ),
        pytest.param(
            "async+memcached://localhost:22122",
            {},
            lf("memcached"),
            marks=[pytest.mark.memcached, pytest.mark.flaky],
            id="memcached",
        ),
        pytest.param(
            "async+memcached://localhost:22122,localhost:22123",
            {},
            lf("memcached_cluster"),
            marks=[pytest.mark.memcached, pytest.mark.flaky],
            id="memcached-cluster",
        ),
        pytest.param(
            "async+redis+cluster://localhost:7001/",
            {
                "implementation": ASYNC_REDIS_IMPLEMENTATION,
            },
            lf("redis_cluster"),
            marks=pytest.mark.redis_cluster,
            id="redis-cluster",
        ),
        pytest.param(
            "async+redis+cluster://:sekret@localhost:8400/",
            {
                "implementation": ASYNC_REDIS_IMPLEMENTATION,
            },
            lf("redis_auth_cluster"),
            marks=pytest.mark.redis_cluster,
            id="redis-cluster-auth",
        ),
        pytest.param(
            "async+redis+cluster://localhost:8301",
            {
                "ssl": True,
                "ssl_cert_reqs": "required",
                "ssl_keyfile": "./tests/tls/client.key",
                "ssl_certfile": "./tests/tls/client.crt",
                "ssl_ca_certs": "./tests/tls/ca.crt",
                "implementation": ASYNC_REDIS_IMPLEMENTATION,
            },
            lf("redis_ssl_cluster"),
            marks=pytest.mark.redis_cluster,
            id="redis-ssl-cluster",
        ),
        pytest.param(
            "async+redis+sentinel://localhost:26379/mymaster",
            {
                "use_replicas": False,
                "implementation": ASYNC_REDIS_IMPLEMENTATION,
            },
            lf("redis_sentinel"),
            marks=pytest.mark.redis_sentinel,
            id="redis-sentinel",
        ),
        pytest.param(
            "async+mongodb://localhost:37017/",
            {},
            lf("mongodb"),
            marks=pytest.mark.mongodb,
            id="mongodb",
        ),
        pytest.param(
            "async+valkey://localhost:12379",
            {},
            lf("valkey_basic"),
            marks=pytest.mark.valkey,
            id="valkey_basic",
        ),
        pytest.param(
            "async+valkey+cluster://localhost:2001/",
            {},
            lf("valkey_cluster"),
            marks=pytest.mark.valkey_cluster,
            id="valkey-cluster",
        ),
    ],
)

async_moving_window_storage = pytest.mark.parametrize(
    "uri, args, fixture",
    [
        pytest.param(
            "async+memory://", {}, None, marks=pytest.mark.memory, id="in-memory"
        ),
        pytest.param(
            "async+redis://localhost:7379",
            {
                "implementation": ASYNC_REDIS_IMPLEMENTATION,
            },
            lf("redis_basic"),
            marks=pytest.mark.redis,
            id="redis",
        ),
        pytest.param(
            "async+redis+cluster://localhost:7001/",
            {
                "implementation": ASYNC_REDIS_IMPLEMENTATION,
            },
            lf("redis_cluster"),
            marks=pytest.mark.redis_cluster,
            id="redis-cluster",
        ),
        pytest.param(
            "async+redis+cluster://:sekret@localhost:8400/",
            {
                "implementation": ASYNC_REDIS_IMPLEMENTATION,
            },
            lf("redis_auth_cluster"),
            marks=pytest.mark.redis_cluster,
            id="redis-cluster-auth",
        ),
        pytest.param(
            "async+redis+cluster://localhost:8301",
            {
                "ssl": True,
                "ssl_cert_reqs": "required",
                "ssl_keyfile": "./tests/tls/client.key",
                "ssl_certfile": "./tests/tls/client.crt",
                "ssl_ca_certs": "./tests/tls/ca.crt",
                "implementation": ASYNC_REDIS_IMPLEMENTATION,
            },
            lf("redis_ssl_cluster"),
            marks=pytest.mark.redis_cluster,
            id="redis-ssl-cluster",
        ),
        pytest.param(
            "async+redis+sentinel://localhost:26379/mymaster",
            {
                "use_replicas": False,
                "implementation": ASYNC_REDIS_IMPLEMENTATION,
            },
            lf("redis_sentinel"),
            marks=pytest.mark.redis_sentinel,
            id="redis-sentinel",
        ),
        pytest.param(
            "async+mongodb://localhost:37017/",
            {},
            lf("mongodb"),
            marks=pytest.mark.mongodb,
            id="mongodb",
        ),
        pytest.param(
            "async+valkey://localhost:12379",
            {},
            lf("valkey_basic"),
            marks=pytest.mark.valkey,
            id="valkey_basic",
        ),
        pytest.param(
            "async+valkey+cluster://localhost:2001/",
            {},
            lf("valkey_cluster"),
            marks=pytest.mark.valkey_cluster,
            id="valkey-cluster",
        ),
    ],
)

async_sliding_window_counter_storage = pytest.mark.parametrize(
    "uri, args, fixture",
    [
        pytest.param(
            "async+memory://", {}, None, marks=pytest.mark.memory, id="in-memory"
        ),
        pytest.param(
            "async+redis://localhost:7379",
            {"implementation": ASYNC_REDIS_IMPLEMENTATION},
            lf("redis_basic"),
            marks=pytest.mark.redis,
            id="redis",
        ),
        pytest.param(
            "async+memcached://localhost:22122",
            {},
            lf("memcached"),
            marks=[pytest.mark.memcached, pytest.mark.flaky],
            id="memcached",
        ),
        pytest.param(
            "async+memcached://localhost:22122,localhost:22123",
            {},
            lf("memcached_cluster"),
            marks=[pytest.mark.memcached, pytest.mark.flaky],
            id="memcached-cluster",
        ),
        pytest.param(
            "async+redis+cluster://localhost:7001/",
            {"implementation": ASYNC_REDIS_IMPLEMENTATION},
            lf("redis_cluster"),
            marks=pytest.mark.redis_cluster,
            id="redis-cluster",
        ),
        pytest.param(
            "async+redis+cluster://:sekret@localhost:8400/",
            {"implementation": ASYNC_REDIS_IMPLEMENTATION},
            lf("redis_auth_cluster"),
            marks=pytest.mark.redis_cluster,
            id="redis-cluster-auth",
        ),
        pytest.param(
            "async+redis+cluster://localhost:8301",
            {
                "ssl": True,
                "ssl_cert_reqs": "required",
                "ssl_keyfile": "./tests/tls/client.key",
                "ssl_certfile": "./tests/tls/client.crt",
                "ssl_ca_certs": "./tests/tls/ca.crt",
                "implementation": ASYNC_REDIS_IMPLEMENTATION,
            },
            lf("redis_ssl_cluster"),
            marks=pytest.mark.redis_cluster,
            id="redis-ssl-cluster",
        ),
        pytest.param(
            "async+redis+sentinel://localhost:26379/mymaster",
            {
                "use_replicas": False,
                "implementation": ASYNC_REDIS_IMPLEMENTATION,
            },
            lf("redis_sentinel"),
            marks=pytest.mark.redis_sentinel,
            id="redis-sentinel",
        ),
        pytest.param(
            "async+mongodb://localhost:37017/",
            {},
            lf("mongodb"),
            marks=pytest.mark.mongodb,
            id="mongodb",
        ),
        pytest.param(
            "async+valkey://localhost:12379",
            {},
            lf("valkey_basic"),
            marks=pytest.mark.valkey,
            id="valkey_basic",
        ),
        pytest.param(
            "async+valkey+cluster://localhost:2001/",
            {},
            lf("valkey_cluster"),
            marks=pytest.mark.valkey_cluster,
            id="valkey-cluster",
        ),
    ],
)
