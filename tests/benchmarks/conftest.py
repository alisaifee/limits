from __future__ import annotations

import pytest

import limits

STORAGE_INFO = {}


@pytest.fixture(autouse=True, scope="session")
def get_storage_info(redis_basic_client, memcached_client, mongodb_client) -> None:
    redis_info = redis_basic_client.info()
    memcached_info = memcached_client.stats()
    mongodb_info = mongodb_client.server_info()
    STORAGE_INFO["redis"] = redis_info
    STORAGE_INFO["memcached"] = {
        k.decode(): v.decode() if isinstance(v, bytes) else v
        for k, v in memcached_info.items()
    }
    STORAGE_INFO["mongodb"] = mongodb_info


@pytest.hookimpl(hookwrapper=True)
def pytest_benchmark_generate_json(
    config,
    benchmarks,
    include_data,
    machine_info,
    commit_info,
):
    for bench in benchmarks:
        for name, param in list(bench.params.items()):
            if isinstance(param, limits.RateLimitItem):
                bench.params[name] = str(param)
            if isinstance(param, type) and issubclass(
                param,
                (limits.strategies.RateLimiter, limits.aio.strategies.RateLimiter),
            ):
                match param:
                    case (
                        limits.strategies.FixedWindowRateLimiter
                        | limits.aio.strategies.FixedWindowRateLimiter
                    ):
                        bench.params[name] = "fixed-window"
                    case (
                        limits.strategies.MovingWindowRateLimiter
                        | limits.aio.strategies.MovingWindowRateLimiter
                    ):
                        bench.params[name] = "moving-window"
                    case (
                        limits.strategies.SlidingWindowCounterRateLimiter
                        | limits.aio.strategies.SlidingWindowCounterRateLimiter
                    ):
                        bench.params[name] = "sliding-window"
            if name == "uri":
                scheme = limits.storage.storage_from_string(param).STORAGE_SCHEME[0]
                bench.params["async"] = "async" in scheme
                bench.params["storage_type"] = scheme.replace("async+", "")
    machine_info.update(STORAGE_INFO)
    yield
