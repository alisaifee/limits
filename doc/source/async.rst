#############
Async Support
#############
.. versionadded:: 2.1
.. danger:: Experimental

A new namespace ``limits.aio`` is available which mirrors the original
``limits.storage`` and ``limits.strategies`` packages.

Limits supports the following storage options:

 - Redis (via `aredis <https://aredis.readthedocs.org>`_)
 - Memcached (via `emcache <https://emcache.readthedocs.org>`_)

***********
Quick start
***********

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
storage backends, and :ref:`api:strategies` (Async) for the async rate limit strategies
API.

