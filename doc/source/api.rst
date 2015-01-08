API
----

Storage
=======
.. autoclass:: limits.storage.Storage
.. autoclass:: limits.storage.MemoryStorage
.. autoclass:: limits.storage.RedisStorage
.. autoclass:: limits.storage.MemcachedStorage

Strategies
==========
.. autoclass:: limits.strategies.RateLimiter
.. autoclass:: limits.strategies.FixedWindowRateLimiter
.. autoclass:: limits.strategies.FixedWindowElasticExpiryRateLimiter
.. autoclass:: limits.strategies.MovingWindowRateLimiter

Exceptions
==========
.. autoexception:: limits.errors.ConfigurationError

