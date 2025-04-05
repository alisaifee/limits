==========
Quickstart
==========

.. note:: In an async context, simply substitute the imports
   from :mod:`limits` to :mod:`limits.aio` and use ``await`` in
   the storage and limiter methods.


Initialize the strategy & storage
=================================

Initialize the storage backend
------------------------------

.. tab:: In Memory

    .. code::

        from limits import storage
        limits_storage = storage.MemoryStorage()

.. tab:: Memcached

    .. code::

        from limits import storage
        limits_storage = storage.MemcachedStorage(
            "memcached://localhost:11211"
        )

.. tab:: Redis

    .. code::

        from limits import storage
        limits_storage = storage.RedisStorage("redis://localhost:6379/1")

Initialize a rate limiter
--------------------------

.. tab:: With the Fixed window strategy

    .. code::

        from limits import strategies
        limiter = strategies.FixedWindowRateLimiter(limits_storage)

.. tab:: With the Moving window strategy

    .. caution:: If the storage used does not support the moving window
       strategy, :exc:`NotImplementedError` will be raised

    .. code::

        from limits import strategies
        limiter = strategies.MovingWindowRateLimiter(limits_storage)

.. tab:: With the Sliding window counter strategy

    .. caution:: If the storage used does not support the sliding window
       counter strategy, :exc:`NotImplementedError` will be raised

    .. code::

        from limits import strategies
        limiter = strategies.SlidingWindowCounterRateLimiter(limits_storage)

Describe the rate limit
=======================

Initialize a rate limit using the :ref:`string notation<quickstart:rate limit string notation>`
-----------------------------------------------------------------------------------------------

.. code::

    from limits import parse
    one_per_minute = parse("1/minute")

Initialize a rate limit explicitly using a subclass of :class:`~limits.RateLimitItem`
-------------------------------------------------------------------------------------

.. code::

    from limits import RateLimitItemPerSecond
    one_per_second = RateLimitItemPerSecond(1, 1)


Test the limits
===============

Consume the limits
------------------

.. code::

    >>> limiter.hit(one_per_minute, "test_namespace", "foo")
    True
    >>> limiter.hit(one_per_minute, "test_namespace", "foo")
    False
    >>> limiter.hit(one_per_minute, "test_namespace", "bar")
    True

    >>> limiter.hit(one_per_second, "test_namespace", "foo")
    True
    >>> limiter.hit(one_per_second, "test_namespace", "foo")
    False
    >>> time.sleep(1)
    >>> limiter.hit(one_per_second, "test_namespace", "foo")
    True

Check without consuming
-----------------------

.. code::

    >>> limiter.hit(one_per_second, "test_namespace", "foo")
    True
    >>> while not limiter.test(one_per_second, "test_namespace", "foo"):
    ...     time.sleep(0.01)
    >>> limiter.hit(one_per_second, "test_namespace", "foo")
    True

Query available capacity and reset time
-----------------------------------------

.. code::

   >>> limiter.hit(one_per_minute, "test_namespace", "foo")
   True
   >>> window = limiter.get_window_stats(one_per_minute, "test_namespace", "foo")
   >>> window.remaining
   0
   >>> limiter.hit(one_per_minute, "test_namespace", "foo")
   False
   >>> time.sleep(window.reset_time - time.time())
   >>> limiter.hit(one_per_minute, "test_namespace", "foo")
   True


Clear a limit
=============

.. code::

    >>> limiter.hit(one_per_minute, "test_namespace", "foo")
    True
    >>> limiter.hit(one_per_minute, "test_namespace", "foo")
    False
    >>> limiter.clear(one_per_minute, "test_namespace", "foo")
    >>> limiter.hit(one_per_minute, "test_namespace", "foo")
    True



.. _ratelimit-string:

==========================
Rate limit string notation
==========================

Instead of manually constructing instances of :class:`~limits.RateLimitItem`
you can instead use the following :ref:`api:parsing functions`.

- :func:`~limits.parse`
- :func:`~limits.parse_many`

These functions accept rate limits specified as strings following the format::

    [count] [per|/] [n (optional)] [second|minute|hour|day|month|year]

You can combine rate limits by separating them with a delimiter of your
choice.

Examples
========

* ``10 per hour``
* ``10/hour``
* ``10/hour;100/day;2000 per year``
* ``100/day, 500/7days``
