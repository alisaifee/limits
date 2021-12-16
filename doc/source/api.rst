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

In-Memory
^^^^^^^^^
.. autoclass:: limits.storage.MemoryStorage

Redis
^^^^^
.. autoclass:: limits.storage.RedisStorage

Redis Cluster
^^^^^^^^^^^^^
.. autoclass:: limits.storage.RedisClusterStorage

Redis Sentinel
^^^^^^^^^^^^^^
.. autoclass:: limits.storage.RedisSentinelStorage

Memcached
^^^^^^^^^
.. autoclass:: limits.storage.MemcachedStorage

MongoDB
^^^^^^^
.. autoclass:: limits.storage.MongoDBStorage

Google App Engine Memcached
^^^^^^^^^^^^^^^^^^^^^^^^^^^
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

