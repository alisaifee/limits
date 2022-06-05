import asyncio
import contextlib
import functools
import math
import time
from typing import Optional

import pytest


def fixed_start(fn):
    @functools.wraps(fn)
    def __inner(*a, **k):
        start = time.time()

        while time.time() < math.ceil(start):
            time.sleep(0.01)

        return fn(*a, **k)

    return __inner


@contextlib.contextmanager
def window(delay_end: float, delay: Optional[float] = None):
    start = time.time()

    if delay is not None:
        while time.time() - start < delay:
            time.sleep(0.001)
    yield (int(start), int(start + delay_end))

    while time.time() - start < delay_end:
        time.sleep(0.001)


@contextlib.asynccontextmanager
async def async_window(delay_end: float, delay: Optional[float] = None):
    start = time.time()

    if delay is not None:
        while time.time() - start < delay:
            await asyncio.sleep(0.001)

    yield (int(start), int(start + delay_end))

    while time.time() - start < delay_end:
        await asyncio.sleep(0.001)


all_storage = pytest.mark.parametrize(
    "uri, args, fixture",
    [
        ("memory://", {}, None),
        pytest.param(
            "redis://localhost:7379",
            {},
            pytest.lazy_fixture("redis_basic"),
            marks=pytest.mark.redis,
        ),
        pytest.param(
            "memcached://localhost:22122",
            {},
            pytest.lazy_fixture("memcached"),
            marks=[pytest.mark.memcached, pytest.mark.flaky],
        ),
        pytest.param(
            "memcached://localhost:22122,localhost:22123",
            {},
            pytest.lazy_fixture("memcached_cluster"),
            marks=[pytest.mark.memcached, pytest.mark.flaky],
        ),
        pytest.param(
            "redis+cluster://localhost:7001/",
            {},
            pytest.lazy_fixture("redis_cluster"),
            marks=pytest.mark.redis_cluster,
        ),
        pytest.param(
            "redis+sentinel://localhost:26379/localhost-redis-sentinel",
            {"use_replicas": False},
            pytest.lazy_fixture("redis_sentinel"),
            marks=pytest.mark.redis_sentinel,
        ),
        pytest.param(
            "mongodb://localhost:37017/",
            {},
            pytest.lazy_fixture("mongodb"),
            marks=pytest.mark.mongodb,
        ),
    ],
)

moving_window_storage = pytest.mark.parametrize(
    "uri, args, fixture",
    [
        ("memory://", {}, None),
        pytest.param(
            "redis://localhost:7379",
            {},
            pytest.lazy_fixture("redis_basic"),
            marks=pytest.mark.redis,
        ),
        pytest.param(
            "redis+cluster://localhost:7001/",
            {},
            pytest.lazy_fixture("redis_cluster"),
            marks=pytest.mark.redis_cluster,
        ),
        pytest.param(
            "redis+sentinel://localhost:26379/localhost-redis-sentinel",
            {"use_replicas": False},
            pytest.lazy_fixture("redis_sentinel"),
            marks=pytest.mark.redis_sentinel,
        ),
        pytest.param(
            "mongodb://localhost:37017/",
            {},
            pytest.lazy_fixture("mongodb"),
            marks=pytest.mark.mongodb,
        ),
    ],
)

async_all_storage = pytest.mark.parametrize(
    "uri, args, fixture",
    [
        ("async+memory://", {}, None),
        pytest.param(
            "async+redis://localhost:7379",
            {},
            pytest.lazy_fixture("redis_basic"),
            marks=pytest.mark.redis,
        ),
        pytest.param(
            "async+memcached://localhost:22122",
            {},
            pytest.lazy_fixture("memcached"),
            marks=[pytest.mark.memcached, pytest.mark.flaky],
        ),
        pytest.param(
            "async+memcached://localhost:22122,localhost:22123",
            {},
            pytest.lazy_fixture("memcached_cluster"),
            marks=[pytest.mark.memcached, pytest.mark.flaky],
        ),
        pytest.param(
            "async+redis+cluster://localhost:7001/",
            {},
            pytest.lazy_fixture("redis_cluster"),
            marks=pytest.mark.redis_cluster,
        ),
        pytest.param(
            "async+redis+sentinel://localhost:26379/localhost-redis-sentinel",
            {"use_replicas": False},
            pytest.lazy_fixture("redis_sentinel"),
            marks=pytest.mark.redis_sentinel,
        ),
        pytest.param(
            "async+mongodb://localhost:37017/",
            {},
            pytest.lazy_fixture("mongodb"),
            marks=pytest.mark.mongodb,
        ),
    ],
)

async_moving_window_storage = pytest.mark.parametrize(
    "uri, args, fixture",
    [
        ("async+memory://", {}, None),
        pytest.param(
            "async+redis://localhost:7379",
            {},
            pytest.lazy_fixture("redis_basic"),
            marks=pytest.mark.redis,
        ),
        pytest.param(
            "async+redis+cluster://localhost:7001/",
            {},
            pytest.lazy_fixture("redis_cluster"),
            marks=pytest.mark.redis_cluster,
        ),
        pytest.param(
            "async+redis+sentinel://localhost:26379/localhost-redis-sentinel",
            {"use_replicas": False},
            pytest.lazy_fixture("redis_sentinel"),
            marks=pytest.mark.redis_sentinel,
        ),
        pytest.param(
            "async+mongodb://localhost:37017/",
            {},
            pytest.lazy_fixture("mongodb"),
            marks=pytest.mark.mongodb,
        ),
    ],
)
