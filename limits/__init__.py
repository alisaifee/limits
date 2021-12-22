"""
Rate limiting with commonly used storage backends
"""

from ._version import get_versions
from .util import parse, parse_many

from .limits import (
    RateLimitItem,
    RateLimitItemPerYear,
    RateLimitItemPerMonth,
    RateLimitItemPerDay,
    RateLimitItemPerHour,
    RateLimitItemPerMinute,
    RateLimitItemPerSecond,
)

from . import aio
from . import storage
from . import strategies


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
