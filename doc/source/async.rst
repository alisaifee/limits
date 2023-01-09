=============
Async Support
=============

.. versionadded:: 2.1

A new namespace ``limits.aio`` is available which mirrors the original
``limits.storage`` and ``limits.strategies`` packages.

The following async storage backends are implemented:

- In-Memory
- Redis (via `coredis <https://coredis.readthedocs.org>`_)
- Memcached (via `emcache <https://emcache.readthedocs.org>`_)
- MongoDB (via `motor <https://motor.readthedocs.org>`_)
- Etcd (via `aetcd <https://aetcd.readthedocs.org>`_)

Quick start
===========

This example demonstrates the subtle differences in the ``limits.aio`` namespace:

.. code::

   from limits import parse
   from limits.storage import storage_from_string
   from limits.aio.strategies import MovingWindowRateLimiter

   redis = storage_from_string("async+redis://localhost:6379")

   moving_window = MovingWindowRateLimiter(redis)
   one_per_minute = parse("1/minute")

   async def hit():
      return await moving_window.hit(one_per_minute, "test_namespace", "foo")


Refer to :ref:`api:async storage` for more implementation details of the async
storage backends, and :ref:`api:async strategies` for the async rate limit strategies API.

