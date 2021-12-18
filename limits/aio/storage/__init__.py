"""
Implementations of storage backends to be used with
:class:`limits.aio.strategies.RateLimiter` strategies
"""

from .base import Storage
from .base import MovingWindowSupport
from .memcached import MemcachedStorage
from .memory import MemoryStorage
from .mongodb import MongoDBStorage
from .redis import RedisClusterStorage
from .redis import RedisSentinelStorage
from .redis import RedisStorage


__all__ = [
    "Storage",
    "MovingWindowSupport",
    "MemcachedStorage",
    "MemoryStorage",
    "MongoDBStorage",
    "RedisStorage",
    "RedisClusterStorage",
    "RedisSentinelStorage",
]
