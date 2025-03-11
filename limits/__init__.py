"""
Rate limiting with commonly used storage backends
"""

from __future__ import annotations

from . import _version, aio, storage, strategies
from .limits import (
    RateLimitItem,
    RateLimitItemPerDay,
    RateLimitItemPerHour,
    RateLimitItemPerMinute,
    RateLimitItemPerMonth,
    RateLimitItemPerSecond,
    RateLimitItemPerYear,
)
from .util import WindowStats, parse, parse_many

__all__ = [
    "RateLimitItem",
    "RateLimitItemPerDay",
    "RateLimitItemPerHour",
    "RateLimitItemPerMinute",
    "RateLimitItemPerMonth",
    "RateLimitItemPerSecond",
    "RateLimitItemPerYear",
    "WindowStats",
    "aio",
    "parse",
    "parse_many",
    "storage",
    "strategies",
]

__version__ = _version.get_versions()["version"]
