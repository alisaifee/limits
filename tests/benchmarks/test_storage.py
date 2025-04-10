from __future__ import annotations

import functools
import random

import pytest

import limits.aio.strategies
from limits import RateLimitItemPerDay, RateLimitItemPerMinute
from limits.storage import storage_from_string
from limits.strategies import (
    FixedWindowRateLimiter,
    MovingWindowRateLimiter,
    SlidingWindowCounterRateLimiter,
)
from tests.utils import ALL_STORAGES, ALL_STORAGES_ASYNC

benchmark_limits = pytest.mark.parametrize(
    "limit",
    [
        RateLimitItemPerMinute(500),
        RateLimitItemPerMinute(1000),
        RateLimitItemPerDay(10000),
        RateLimitItemPerDay(100000),
    ],
    ids=lambda limit: str(limit),
)


benchmark_all_storages = pytest.mark.parametrize(
    "uri, args, fixture",
    [
        storage
        for name, storage in ALL_STORAGES.items()
        if name in {"memory", "redis", "memcached", "mongodb"}
    ],
)
benchmark_all_async_storages = pytest.mark.parametrize(
    "uri, args, fixture",
    [
        storage
        for name, storage in ALL_STORAGES_ASYNC.items()
        if name in {"memory", "redis", "memcached", "mongodb"}
    ],
)


@pytest.fixture(autouse=True)
def ensure_supported(strategy, uri):
    storage = storage_from_string(uri)
    try:
        strategy(storage)
    except NotImplementedError:
        return pytest.skip(
            f"{strategy.__name__} not supported by {storage.__class__.__name__}"
        )


def call_hit(strategy, storage, limit, event_loop=None):
    uid = int(random.random() * 100)
    call = strategy(storage).hit(limit, uid)

    if isinstance(storage, limits.aio.storage.Storage):
        event_loop.run_until_complete(call)


def call_test(strategy, storage, limit, event_loop=None):
    uid = int(random.random() * 100)
    call = strategy(storage).test(limit, uid)

    if isinstance(storage, limits.aio.storage.Storage):
        event_loop.run_until_complete(call)


def call_get_window_stats(strategy, storage, limit, event_loop=None):
    uid = int(random.random() * 100)
    call = strategy(storage).get_window_stats(limit, uid)

    if isinstance(storage, limits.aio.storage.Storage):
        event_loop.run_until_complete(call)


def seed_limit(limiter, limit, event_loop=None):
    for uid in range(100):
        call = limiter.hit(limit, uid, cost=int(limit.amount / 2))

        if isinstance(limiter, limits.aio.strategies.RateLimiter):
            event_loop.run_until_complete(call)


@benchmark_all_storages
@benchmark_limits
@pytest.mark.benchmark(group="hit")
@pytest.mark.parametrize(
    "strategy",
    [
        FixedWindowRateLimiter,
        SlidingWindowCounterRateLimiter,
        MovingWindowRateLimiter,
    ],
    ids=["fixed-window", "sliding-window", "moving-window"],
)
def test_hit(benchmark, strategy, uri, args, limit, fixture):
    benchmark.extra_info["async"] = False
    benchmark(
        functools.partial(call_hit, strategy, storage_from_string(uri, **args), limit)
    )


@benchmark_all_storages
@benchmark_limits
@pytest.mark.parametrize(
    "strategy",
    [
        FixedWindowRateLimiter,
        SlidingWindowCounterRateLimiter,
        MovingWindowRateLimiter,
    ],
    ids=["fixed-window", "sliding-window", "moving-window"],
)
@pytest.mark.benchmark(group="get-window-stats")
def test_get_window_stats(benchmark, strategy, uri, args, limit, fixture):
    storage = storage_from_string(uri, **args)
    seed_limit(strategy(storage), limit)
    benchmark(functools.partial(call_get_window_stats, strategy, storage, limit))


@benchmark_all_storages
@benchmark_limits
@pytest.mark.parametrize(
    "strategy",
    [
        FixedWindowRateLimiter,
        SlidingWindowCounterRateLimiter,
        MovingWindowRateLimiter,
    ],
    ids=["fixed-window", "sliding-window", "moving-window"],
)
@pytest.mark.benchmark(group="test")
def test_test(benchmark, strategy, uri, args, limit, fixture):
    storage = storage_from_string(uri, **args)
    seed_limit(strategy(storage), limit)
    benchmark(functools.partial(call_test, strategy, storage, limit))


@benchmark_all_async_storages
@benchmark_limits
@pytest.mark.parametrize(
    "strategy",
    [
        limits.aio.strategies.FixedWindowRateLimiter,
        limits.aio.strategies.SlidingWindowCounterRateLimiter,
        limits.aio.strategies.MovingWindowRateLimiter,
    ],
    ids=["fixed-window", "sliding-window", "moving-window"],
)
@pytest.mark.benchmark(group="hit")
def test_hit_async(event_loop, benchmark, strategy, uri, args, limit, fixture):
    benchmark(
        functools.partial(
            call_hit,
            strategy,
            storage_from_string(uri, **args),
            limit,
            event_loop,
        )
    )


@benchmark_all_async_storages
@benchmark_limits
@pytest.mark.parametrize(
    "strategy",
    [
        limits.aio.strategies.FixedWindowRateLimiter,
        limits.aio.strategies.SlidingWindowCounterRateLimiter,
        limits.aio.strategies.MovingWindowRateLimiter,
    ],
    ids=["fixed-window", "sliding-window", "moving-window"],
)
@pytest.mark.benchmark(group="get-window-stats")
def test_get_window_stats_async(
    event_loop, benchmark, strategy, uri, args, limit, fixture
):
    storage = storage_from_string(uri, **args)
    seed_limit(strategy(storage), limit, event_loop)
    benchmark(
        functools.partial(
            call_get_window_stats,
            strategy,
            storage,
            limit,
            event_loop,
        )
    )


@benchmark_all_async_storages
@benchmark_limits
@pytest.mark.parametrize(
    "strategy",
    [
        limits.aio.strategies.FixedWindowRateLimiter,
        limits.aio.strategies.SlidingWindowCounterRateLimiter,
        limits.aio.strategies.MovingWindowRateLimiter,
    ],
    ids=["fixed-window", "sliding-window", "moving-window"],
)
@pytest.mark.benchmark(group="test")
def test_test_async(event_loop, benchmark, strategy, uri, args, limit, fixture):
    storage = storage_from_string(uri, **args)
    seed_limit(strategy(storage), limit, event_loop)
    benchmark(
        functools.partial(
            call_test,
            strategy,
            storage,
            limit,
            event_loop,
        )
    )
