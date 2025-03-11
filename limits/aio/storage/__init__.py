"""
Implementations of storage backends to be used with
:class:`limits.aio.strategies.RateLimiter` strategies
"""

from __future__ import annotations

from .base import MovingWindowSupport, SlidingWindowCounterSupport, Storage
from .etcd import EtcdStorage
from .memcached import MemcachedStorage
from .memory import MemoryStorage
from .mongodb import MongoDBStorage
from .redis import RedisClusterStorage, RedisSentinelStorage, RedisStorage

__all__ = [
    "EtcdStorage",
    "MemcachedStorage",
    "MemoryStorage",
    "MongoDBStorage",
    "MovingWindowSupport",
    "RedisClusterStorage",
    "RedisSentinelStorage",
    "RedisStorage",
    "SlidingWindowCounterSupport",
    "Storage",
]
