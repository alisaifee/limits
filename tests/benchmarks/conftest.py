from __future__ import annotations

import pytest

import limits


@pytest.hookimpl(hookwrapper=True)
def pytest_benchmark_generate_json(
    config, benchmarks, include_data, machine_info, commit_info
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
    yield
