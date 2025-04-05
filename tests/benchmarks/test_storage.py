from __future__ import annotations

import functools
import random

import pytest

import limits.aio.strategies
from limits import (
    RateLimitItemPerDay,
    RateLimitItemPerMinute,
)
from limits.storage import storage_from_string
from limits.strategies import (
    FixedWindowRateLimiter,
    MovingWindowRateLimiter,
    SlidingWindowCounterRateLimiter,
)
from tests.utils import (
    ALL_STORAGES,
    ALL_STORAGES_ASYNC,
)

benchmark_limits = pytest.mark.parametrize(
    "limit",
    [
        RateLimitItemPerMinute(500),
        RateLimitItemPerMinute(1000),
        RateLimitItemPerDay(10000),
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
benchmark_moving_window_storages = pytest.mark.parametrize(
    "uri, args, fixture",
    [
        storage
        for name, storage in ALL_STORAGES.items()
        if name in {"memory", "redis", "mongodb"}
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
benchmark_moving_window_async_storages = pytest.mark.parametrize(
    "uri, args, fixture",
    [
        storage
        for name, storage in ALL_STORAGES_ASYNC.items()
        if name in {"memory", "redis", "mongodb"}
    ],
)


def hit_window(strategy, storage, limit):
    uid = int(random.random() * 100)
    strategy(storage).hit(limit, uid)


def get_window_stats(strategy, storage, limit):
    uid = int(random.random() * 100)
    strategy(storage).get_window_stats(limit, uid)


def hit_window_async(event_loop, strategy, storage, limit):
    uid = int(random.random() * 100)
    event_loop.run_until_complete(strategy(storage).hit(limit, uid))


def get_window_stats_async(event_loop, strategy, storage, limit):
    uid = int(random.random() * 100)
    event_loop.run_until_complete(strategy(storage).get_window_stats(limit, uid))


def seed_limit(limiter, limit):
    for uid in range(100):
        limiter.hit(limit, uid, cost=int(limit.amount / 2))


def seed_limit_async(limiter, limit, event_loop):
    for uid in range(100):
        event_loop.run_until_complete(
            limiter.hit(limit, uid, cost=int(limit.amount / 2))
        )


@benchmark_all_storages
@benchmark_limits
@pytest.mark.benchmark(group="fixed-window-hit")
def test_fixed_window_hit(benchmark, uri, args, limit, fixture):
    benchmark(
        functools.partial(
            hit_window, FixedWindowRateLimiter, storage_from_string(uri, **args), limit
        )
    )


@benchmark_all_storages
@benchmark_limits
@pytest.mark.benchmark(group="fixed-window-get-window-stats")
def test_fixed_window_get_stats(benchmark, uri, args, limit, fixture):
    storage = storage_from_string(uri, **args)
    seed_limit(FixedWindowRateLimiter(storage), limit)
    benchmark(
        functools.partial(get_window_stats, FixedWindowRateLimiter, storage, limit)
    )


@benchmark_all_storages
@benchmark_limits
@pytest.mark.benchmark(group="sliding-window-counter-hit")
def test_sliding_window_counter_hit(benchmark, uri, args, limit, fixture):
    benchmark(
        functools.partial(
            hit_window,
            SlidingWindowCounterRateLimiter,
            storage_from_string(uri, **args),
            limit,
        )
    )


@benchmark_all_storages
@benchmark_limits
@pytest.mark.benchmark(group="sliding-window-counter-get-window-stats")
def test_sliding_window_get_stats(benchmark, uri, args, limit, fixture):
    storage = storage_from_string(uri, **args)
    seed_limit(SlidingWindowCounterRateLimiter(storage), limit)
    benchmark(
        functools.partial(
            get_window_stats,
            SlidingWindowCounterRateLimiter,
            storage,
            limit,
        )
    )


@benchmark_moving_window_storages
@benchmark_limits
@pytest.mark.benchmark(group="moving-window-hit")
def test_moving_window_hit(benchmark, uri, args, limit, fixture):
    benchmark(
        functools.partial(
            hit_window, MovingWindowRateLimiter, storage_from_string(uri, **args), limit
        )
    )


@benchmark_moving_window_storages
@benchmark_limits
@pytest.mark.benchmark(group="moving-window-get-window-stats")
def test_moving_window_get_stats(benchmark, uri, args, limit, fixture):
    storage = storage_from_string(uri, **args)
    seed_limit(MovingWindowRateLimiter(storage), limit)
    benchmark(
        functools.partial(get_window_stats, MovingWindowRateLimiter, storage, limit)
    )


@benchmark_all_async_storages
@benchmark_limits
@pytest.mark.benchmark(group="async-fixed-window-hit")
def test_fixed_window_async(event_loop, benchmark, uri, args, limit, fixture):
    benchmark(
        functools.partial(
            hit_window_async,
            event_loop,
            limits.aio.strategies.FixedWindowRateLimiter,
            storage_from_string(uri, **args),
            limit,
        )
    )


@benchmark_all_async_storages
@benchmark_limits
@pytest.mark.benchmark(group="async-fixed-window-get-window-stats")
def test_fixed_window_get_stats_async(event_loop, benchmark, uri, args, limit, fixture):
    storage = storage_from_string(uri, **args)
    seed_limit_async(
        limits.aio.strategies.FixedWindowRateLimiter(storage), limit, event_loop
    )
    benchmark(
        functools.partial(
            get_window_stats_async,
            event_loop,
            limits.aio.strategies.FixedWindowRateLimiter,
            storage,
            limit,
        )
    )


@benchmark_moving_window_async_storages
@benchmark_limits
@pytest.mark.benchmark(group="async-moving-window-hit")
def test_moving_window_async(event_loop, benchmark, uri, args, limit, fixture):
    benchmark(
        functools.partial(
            hit_window_async,
            event_loop,
            limits.aio.strategies.MovingWindowRateLimiter,
            storage_from_string(uri, **args),
            limit,
        )
    )


@benchmark_moving_window_async_storages
@benchmark_limits
@pytest.mark.benchmark(group="async-moving-window-get-window-stats")
def test_moving_window_get_stats_async(
    event_loop, benchmark, uri, args, limit, fixture
):
    storage = storage_from_string(uri, **args)
    seed_limit_async(
        limits.aio.strategies.MovingWindowRateLimiter(storage), limit, event_loop
    )
    benchmark(
        functools.partial(
            get_window_stats_async,
            event_loop,
            limits.aio.strategies.MovingWindowRateLimiter,
            storage,
            limit,
        )
    )


@benchmark_all_async_storages
@benchmark_limits
@pytest.mark.benchmark(group="async-sliding-window-counter-hit")
def test_sliding_window_counter_async(event_loop, benchmark, uri, args, limit, fixture):
    benchmark(
        functools.partial(
            hit_window_async,
            event_loop,
            limits.aio.strategies.SlidingWindowCounterRateLimiter,
            storage_from_string(uri, **args),
            limit,
        )
    )


@benchmark_all_async_storages
@benchmark_limits
@pytest.mark.benchmark(group="async-sliding-window-counter-get-window-stats")
def test_sliding_window_counter_get_stats_async(
    event_loop, benchmark, uri, args, limit, fixture
):
    storage = storage_from_string(uri, **args)
    seed_limit_async(
        limits.aio.strategies.SlidingWindowCounterRateLimiter(storage),
        limit,
        event_loop,
    )
    benchmark(
        functools.partial(
            get_window_stats_async,
            event_loop,
            limits.aio.strategies.SlidingWindowCounterRateLimiter,
            storage,
            limit,
        )
    )
