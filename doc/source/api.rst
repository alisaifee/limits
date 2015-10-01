.. currentmodule:: limits

API
----

Storage
=======
.. autoclass:: limits.storage.Storage
.. autoclass:: limits.storage.MemoryStorage
.. autoclass:: limits.storage.RedisStorage
.. autoclass:: limits.storage.RedisSentinelStorage
.. autoclass:: limits.storage.MemcachedStorage
.. autofunction:: limits.storage.storage_from_string

Strategies
==========
.. autoclass:: limits.strategies.RateLimiter
.. autoclass:: limits.strategies.FixedWindowRateLimiter
.. autoclass:: limits.strategies.FixedWindowElasticExpiryRateLimiter
.. autoclass:: limits.strategies.MovingWindowRateLimiter

Rate Limits
===========

.. autoclass:: RateLimitItem
.. autoclass:: RateLimitItemPerYear
.. autoclass:: RateLimitItemPerMonth
.. autoclass:: RateLimitItemPerDay
.. autoclass:: RateLimitItemPerHour
.. autoclass:: RateLimitItemPerMinute
.. autoclass:: RateLimitItemPerSecond
.. autofunction:: parse
.. autofunction:: parse_many


Exceptions
==========
.. autoexception:: limits.errors.ConfigurationError

