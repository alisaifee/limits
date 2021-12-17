.. currentmodule:: limits

####
API
####

**********
Strategies
**********

.. tabbed:: Default

    .. autoclass:: limits.strategies.FixedWindowRateLimiter
    .. autoclass:: limits.strategies.FixedWindowElasticExpiryRateLimiter
    .. autoclass:: limits.strategies.MovingWindowRateLimiter

    All strategies implement the same base class:

    .. autoclass:: limits.strategies.RateLimiter

.. tabbed:: Async


    For asyncio support use the ``limits.aio`` namespace. This
    will expose async methods and expect a subclass of :class:`limits.aio.storage.Storage`

    .. autoclass:: limits.aio.strategies.FixedWindowRateLimiter
    .. autoclass:: limits.aio.strategies.FixedWindowElasticExpiryRateLimiter
    .. autoclass:: limits.aio.strategies.MovingWindowRateLimiter

    All strategies implement the same base class:

    .. autoclass:: limits.aio.strategies.RateLimiter

*******
Storage
*******

Synchronous Storage
===================

In-Memory
---------

.. autoclass:: limits.storage.MemoryStorage

Redis
-----
.. autoclass:: limits.storage.RedisStorage

Redis Cluster
-------------

.. autoclass:: limits.storage.RedisClusterStorage

Redis Sentinel
--------------

.. autoclass:: limits.storage.RedisSentinelStorage

Memcached
---------

.. autoclass:: limits.storage.MemcachedStorage

MongoDB
-------

.. autoclass:: limits.storage.MongoDBStorage


Async Storage
=============

In-Memory
---------

.. autoclass:: limits.aio.storage.MemoryStorage

Redis
-----

.. autoclass:: limits.aio.storage.RedisStorage

Redis Cluster
-------------

.. autoclass:: limits.aio.storage.RedisClusterStorage

Redis Sentinel
--------------

.. autoclass:: limits.aio.storage.RedisSentinelStorage

Memcached
---------

.. autoclass:: limits.aio.storage.MemcachedStorage

Abstract storage classes
========================

.. autoclass:: limits.storage.Storage
.. autoclass:: limits.storage.MovingWindowSupport


Async variants
--------------

.. autoclass:: limits.aio.storage.Storage
.. autoclass:: limits.aio.storage.MovingWindowSupport


************************
Storage Factory function
************************
.. autofunction:: limits.storage.storage_from_string


***********
Rate Limits
***********

Rate limit granularities
========================

.. autoclass:: RateLimitItemPerSecond
.. autoclass:: RateLimitItemPerMinute
.. autoclass:: RateLimitItemPerHour
.. autoclass:: RateLimitItemPerDay
.. autoclass:: RateLimitItemPerMonth
.. autoclass:: RateLimitItemPerYear

Abstract base class in case you have custom needs
-------------------------------------------------

.. autoclass:: RateLimitItem

Parsing functions
=================
.. autofunction:: parse
.. autofunction:: parse_many


**********
Exceptions
**********
.. autoexception:: limits.errors.ConfigurationError
