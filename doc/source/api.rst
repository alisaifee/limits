:tocdepth: 4

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

Synchronous Strategies
----------------------

The available built in rate limiting strategies which expect
a single parameter: a subclass of :class:`~limits.storage.Storage`.

.. currentmodule:: limits.strategies

Provided by :mod:`limits.strategies`

.. autoclass:: FixedWindowRateLimiter
.. autoclass:: FixedWindowElasticExpiryRateLimiter
.. autoclass:: MovingWindowRateLimiter

All strategies implement the same abstract base class:

.. autoclass:: RateLimiter

Async Strategies
----------------

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

In-Memory Storage
^^^^^^^^^^^^^^^^^

.. autoclass:: MemoryStorage

Redis Storage
^^^^^^^^^^^^^
.. autoclass:: RedisStorage

Redis Cluster Storage
^^^^^^^^^^^^^^^^^^^^^

.. autoclass:: RedisClusterStorage

Redis Sentinel Storage
^^^^^^^^^^^^^^^^^^^^^^

.. autoclass:: RedisSentinelStorage

Memcached Storage
^^^^^^^^^^^^^^^^^

.. autoclass:: MemcachedStorage

MongoDB Storage
^^^^^^^^^^^^^^^

.. autoclass:: MongoDBStorage

Etcd Storage
^^^^^^^^^^^^

.. autoclass:: EtcdStorage


Async Storage
-------------
Provided by :mod:`limits.aio.storage`

.. currentmodule:: limits.aio.storage


Async In-Memory Storage
^^^^^^^^^^^^^^^^^^^^^^^

.. autoclass:: MemoryStorage

Async Redis Storage
^^^^^^^^^^^^^^^^^^^

.. autoclass:: RedisStorage

Async Redis Cluster Storage
^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. autoclass:: RedisClusterStorage

Async Redis Sentinel Storage
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. autoclass:: RedisSentinelStorage

Async Memcached Storage
^^^^^^^^^^^^^^^^^^^^^^^

.. autoclass:: MemcachedStorage

Async MongoDB Storage
^^^^^^^^^^^^^^^^^^^^^

.. autoclass:: MongoDBStorage

Async Etcd Storage
^^^^^^^^^^^^^^^^^^

.. autoclass:: EtcdStorage

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


Structures
==========
.. autoclass:: limits.WindowStats
   :no-inherited-members:


Exceptions
==========
.. autoexception:: limits.errors.ConfigurationError
   :no-inherited-members:
.. autoexception:: limits.errors.ConcurrentUpdateError
   :no-inherited-members:
.. autoexception:: limits.errors.StorageError
   :no-inherited-members:
