import functools
import uuid

import pytest

import limits.aio.strategies
from limits import RateLimitItemPerMinute
from limits.storage import storage_from_string
from limits.strategies import FixedWindowRateLimiter, MovingWindowRateLimiter
from tests.utils import (
    all_storage,
    async_all_storage,
    async_moving_window_storage,
    moving_window_storage,
)


def hit_window(strategy, storage):
    limit = RateLimitItemPerMinute(500)
    uid = uuid.uuid4().hex
    strategy(storage).hit(limit, uid)


def hit_window_async(event_loop, strategy, storage):
    limit = RateLimitItemPerMinute(500)
    uid = uuid.uuid4().hex
    event_loop.run_until_complete(strategy(storage).hit(limit, uid))


@all_storage
@pytest.mark.benchmark(group="fixed-window")
def test_fixed_window(benchmark, uri, args, fixture):
    benchmark(
        functools.partial(
            hit_window, FixedWindowRateLimiter, storage_from_string(uri, **args)
        )
    )


@moving_window_storage
@pytest.mark.benchmark(group="moving-window")
def test_moving_window(benchmark, uri, args, fixture):
    benchmark(
        functools.partial(
            hit_window, MovingWindowRateLimiter, storage_from_string(uri, **args)
        )
    )


@async_all_storage
@pytest.mark.benchmark(group="async-fixed-window")
def test_fixed_window_async(event_loop, benchmark, uri, args, fixture):
    benchmark(
        functools.partial(
            hit_window_async,
            event_loop,
            limits.aio.strategies.FixedWindowRateLimiter,
            storage_from_string(uri, **args),
        )
    )


@async_moving_window_storage
@pytest.mark.benchmark(group="async-moving-window")
def test_moving_window_async(event_loop, benchmark, uri, args, fixture):
    benchmark(
        functools.partial(
            hit_window_async,
            event_loop,
            limits.aio.strategies.MovingWindowRateLimiter,
            storage_from_string(uri, **args),
        )
    )
