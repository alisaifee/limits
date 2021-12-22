"""
Rate limiting with commonly used storage backends
"""

from . import aio, storage, strategies
from ._version import get_versions
from .limits import (
    RateLimitItem,
    RateLimitItemPerDay,
    RateLimitItemPerHour,
    RateLimitItemPerMinute,
    RateLimitItemPerMonth,
    RateLimitItemPerSecond,
    RateLimitItemPerYear,
)
from .util import parse, parse_many

__version__ = get_versions()["version"]
del get_versions

__all__ = [
    "RateLimitItem",
    "RateLimitItemPerYear",
    "RateLimitItemPerMonth",
    "RateLimitItemPerDay",
    "RateLimitItemPerHour",
    "RateLimitItemPerMinute",
    "RateLimitItemPerSecond",
    "aio",
    "storage",
    "strategies",
    "parse",
    "parse_many",
]
