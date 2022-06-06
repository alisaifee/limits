==========
Quickstart
==========

Initialize the strategy & storage
=================================

Initialize the storage backend
------------------------------

.. tab:: In Memory

    .. code::

        from limits import storage
        memory_storage = storage.MemoryStorage()

.. tab:: Memcached

    .. code::

        from limits import storage
        memory_storage = storage.MemcachedStorage(
            "memcached://localhost:11211"
        )

.. tab:: Redis

    .. code::

        from limits import storage
        memory_storage = storage.RedisStorage("redis://localhost:6379/1")

Initialize a rate limiter with the :ref:`Moving Window<strategies:moving window>` Strategy
------------------------------------------------------------------------------------------

.. code::

    from limits import strategies
    moving_window = strategies.MovingWindowRateLimiter(memory_storage)


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

    assert True == moving_window.hit(one_per_minute, "test_namespace", "foo")
    assert False == moving_window.hit(one_per_minute, "test_namespace", "foo")
    assert True == moving_window.hit(one_per_minute, "test_namespace", "bar")

    assert True == moving_window.hit(one_per_second, "test_namespace", "foo")
    assert False == moving_window.hit(one_per_second, "test_namespace", "foo")
    time.sleep(1)
    assert True == moving_window.hit(one_per_second, "test_namespace", "foo")

Check without consuming
-----------------------

.. code::

    assert True == moving_window.hit(one_per_second, "test_namespace", "foo")
    while not moving_window.test(one_per_second, "test_namespace", "foo"):
        time.sleep(0.01)
    assert True == moving_window.hit(one_per_second, "test_namespace", "foo")

Clear a limit
=============

.. code::

    assert True == moving_window.hit(one_per_minute, "test_namespace", "foo")
    assert False == moving_window.hit(one_per_minute, "test_namespace", "foo")
    moving_window.clear(one_per_minute, "test_namespace", "foo")
    assert True == moving_window.hit(one_per_minute, "test_namespace", "foo")



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
