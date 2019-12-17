.. currentmodule:: limits

API
----

Storage
=======

======================
Abstract storage class
======================
.. autoclass:: limits.storage.Storage

.. _backend-implementation:

=======================
Backend Implementations
=======================
.. autoclass:: limits.storage.MemoryStorage
.. autoclass:: limits.storage.RedisStorage
.. autoclass:: limits.storage.RedisClusterStorage
.. autoclass:: limits.storage.RedisSentinelStorage
.. autoclass:: limits.storage.MemcachedStorage
.. autoclass:: limits.storage.GAEMemcachedStorage

===============
Utility Methods
===============
.. autofunction:: limits.storage.storage_from_string

Strategies
==========
.. autoclass:: limits.strategies.RateLimiter
.. autoclass:: limits.strategies.FixedWindowRateLimiter
.. autoclass:: limits.strategies.FixedWindowElasticExpiryRateLimiter
.. autoclass:: limits.strategies.MovingWindowRateLimiter

Rate Limits
===========

========================
Rate limit granularities
========================

.. autoclass:: RateLimitItem
.. autoclass:: RateLimitItemPerYear
.. autoclass:: RateLimitItemPerMonth
.. autoclass:: RateLimitItemPerDay
.. autoclass:: RateLimitItemPerHour
.. autoclass:: RateLimitItemPerMinute
.. autoclass:: RateLimitItemPerSecond

===============
Utility Methods
===============
.. autofunction:: parse
.. autofunction:: parse_many


Exceptions
==========
.. autoexception:: limits.errors.ConfigurationError

