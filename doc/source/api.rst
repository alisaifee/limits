
=============
API Reference
=============

.. autosummary::

   limits
   limits.strategies
   limits.storage
   limits.aio.strategies
   limits.aio.storage

.. currentmodule:: limits

Strategies
==========


.. tabbed:: Default

    The available built in rate limiting strategies which expect
    a single parameter: a subclass of :class:`~limits.storage.Storage`.

    .. currentmodule:: limits.strategies

    Provided by :mod:`limits.strategies`

    .. autoclass:: FixedWindowRateLimiter
    .. autoclass:: FixedWindowElasticExpiryRateLimiter
    .. autoclass:: MovingWindowRateLimiter

    All strategies implement the same abstract base class:

    .. autoclass:: RateLimiter

.. tabbed:: Async


    These variants should be used in for asyncio support. These strategies
    expose async variants and expect a subclass of :class:`limits.aio.storage.Storage`

    .. currentmodule:: limits.aio.strategies

    Provided by :mod:`limits.aio.strategies`

    .. autoclass:: FixedWindowRateLimiter
    .. autoclass:: FixedWindowElasticExpiryRateLimiter
    .. autoclass:: MovingWindowRateLimiter

    All strategies implement the same abstract base class:

    .. autoclass:: RateLimiter

Storage
=======

Storage Factory function
------------------------
Provided by :mod:`limits.storage`

.. autofunction:: limits.storage.storage_from_string


Synchronous Storage
-------------------

Provided by :mod:`limits.storage`

.. currentmodule:: limits.storage

In-Memory
^^^^^^^^^

.. autoclass:: MemoryStorage

Redis
^^^^^
.. autoclass:: RedisStorage

Redis Cluster
^^^^^^^^^^^^^

.. autoclass:: RedisClusterStorage

Redis Sentinel
^^^^^^^^^^^^^^

.. autoclass:: RedisSentinelStorage

Memcached
^^^^^^^^^

.. autoclass:: MemcachedStorage

MongoDB
^^^^^^^

.. autoclass:: MongoDBStorage


Async Storage
-------------
Provided by :mod:`limits.aio.storage`

.. currentmodule:: limits.aio.storage


In-Memory
^^^^^^^^^

.. autoclass:: MemoryStorage

Redis
^^^^^

.. autoclass:: RedisStorage

Redis Cluster
^^^^^^^^^^^^^

.. autoclass:: RedisClusterStorage

Redis Sentinel
^^^^^^^^^^^^^^

.. autoclass:: RedisSentinelStorage

Memcached
^^^^^^^^^

.. autoclass:: MemcachedStorage

MongoDB
^^^^^^^

.. autoclass:: MongoDBStorage

Abstract storage classes
------------------------

.. autoclass:: limits.storage.Storage
.. autoclass:: limits.storage.MovingWindowSupport


Async variants
^^^^^^^^^^^^^^

.. autoclass:: limits.aio.storage.Storage
.. autoclass:: limits.aio.storage.MovingWindowSupport


Rate Limits
===========

.. currentmodule:: limits

Provided by :mod:`limits`

Parsing functions
-----------------
.. autofunction:: parse
.. autofunction:: parse_many


Rate limit granularities
------------------------
All rate limit items implement :class:`RateLimitItem` by
declaring a :attr:`GRANULARITY`

.. autoclass:: RateLimitItem

------

.. autoclass:: RateLimitItemPerSecond
.. autoclass:: RateLimitItemPerMinute
.. autoclass:: RateLimitItemPerHour
.. autoclass:: RateLimitItemPerDay
.. autoclass:: RateLimitItemPerMonth
.. autoclass:: RateLimitItemPerYear



Exceptions
==========
.. autoexception:: limits.errors.ConfigurationError


