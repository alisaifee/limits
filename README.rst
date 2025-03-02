.. |ci| image:: https://github.com/alisaifee/limits/actions/workflows/main.yml/badge.svg?branch=master
    :target: https://github.com/alisaifee/limits/actions?query=branch%3Amaster+workflow%3ACI
.. |codecov| image:: https://codecov.io/gh/alisaifee/limits/branch/master/graph/badge.svg
   :target: https://codecov.io/gh/alisaifee/limits
.. |pypi| image:: https://img.shields.io/pypi/v/limits.svg?style=flat-square
    :target: https://pypi.python.org/pypi/limits
.. |pypi-versions| image:: https://img.shields.io/pypi/pyversions/limits?style=flat-square
    :target: https://pypi.python.org/pypi/limits
.. |license| image:: https://img.shields.io/pypi/l/limits.svg?style=flat-square
    :target: https://pypi.python.org/pypi/limits
.. |docs| image:: https://readthedocs.org/projects/limits/badge/?version=latest
   :target: https://limits.readthedocs.org

limits
------
|docs| |ci| |codecov| |pypi| |pypi-versions| |license|


**limits** is a python library to perform rate limiting with commonly used storage backends (Redis, Memcached, MongoDB & Etcd).

Supported Strategies
====================

All strategies implement a common set of methods:

- ``hit`` (i.e., consume a request)
- ``test`` (check if a request can be allowed), and
- ``get_window_stats`` (to determine remaining quota and reset time).

These operations provide consistent behavior across different implementations.

Fixed Window
------------
`Fixed Window <https://limits.readthedocs.io/en/latest/strategies.html#fixed-window>`_

This strategy is the most memory & compute efficient because it uses a single counter
per resource and rate limit. When the first request arrives, a window is started for a fixed duration
(e.g., 60 seconds for a 10/minute limit). All requests within that window increment the counter,
and when the window expires, the counter resets. Burst traffic near window boundaries
may occur.

For example, with a rate limit of 10/minute:

- 10 requests are allowed between 00:00:00 and 00:01:00 if the first request arrives at 00:00:00.
- It is possible to have 1 request at 00:00:00, 9 requests at 00:00:59 and then 10 more at 00:01:00.

Moving Window
-------------
`Moving Window <https://limits.readthedocs.io/en/latest/strategies.html#moving-window>`_

This strategy records each request’s timestamp and enforces the limit by counting only
the requests within the last fixed duration (e.g., 60 seconds for a 10/minute limit).
This creates a continuously sliding window that strictly applies the rate limit based
on recent activity.

For example, with a rate limit of 10/minute:

- Only requests in the last 60 seconds are counted.
- A new request is allowed only if the earliest request has expired.

Sliding Window Counter
------------------------
`Sliding Window Counter <https://limits.readthedocs.io/en/latest/strategies.html#sliding-window-counter>`_

This strategy approximates the moving window while using less memory by maintaining
two counters (for the current and previous buckets). It computes a weighted sum of these
counters—based on the elapsed time since the previous bucket shifted—to determine the
effective count. If the weighted count is below the limit, the request is allowed.

For example, with a rate limit of 10/minute:

- The effective count is calculated by combining the counts from the current and
  previous buckets using a weight factor.
- If the weighted sum is below the limit, the new request is accepted.

Storage backends
================

- `Redis <https://limits.readthedocs.io/en/latest/storage.html#redis-storage>`_
- `Memcached <https://limits.readthedocs.io/en/latest/storage.html#memcached-storage>`_
- `MongoDB <https://limits.readthedocs.io/en/latest/storage.html#mongodb-storage>`_
- `Etcd <https://limits.readthedocs.io/en/latest/storage.html#etcd-storage>`_
- `In-Memory <https://limits.readthedocs.io/en/latest/storage.html#in-memory-storage>`_

Dive right in
=============

Initialize the storage backend

.. code-block:: python

   from limits import storage
   backend = storage.MemoryStorage()
   # or memcached
   backend = storage.MemcachedStorage("memcached://localhost:11211")
   # or redis
   backend = storage.RedisStorage("redis://localhost:6379")
   # or mongodb
   backend = storage.MongoDbStorage("mongodb://localhost:27017")
   # or use the factory
   storage_uri = "memcached://localhost:11211"
   backend = storage.storage_from_string(storage_uri)

Initialize a rate limiter with a strategy

.. code-block:: python

   from limits import strategies
   strategy = strategies.MovingWindowRateLimiter(backend)
   # or fixed window
   strategy = strategies.FixedWindowRateLimiter(backend)
   # or sliding window
   strategy = strategies.SlidingWindowCounterRateLimiter(backend)


Initialize a rate limit

.. code-block:: python

    from limits import parse
    one_per_minute = parse("1/minute")

Initialize a rate limit explicitly

.. code-block:: python

    from limits import RateLimitItemPerSecond
    one_per_second = RateLimitItemPerSecond(1, 1)

Test the limits

.. code-block:: python

    import time
    assert True == strategy.hit(one_per_minute, "test_namespace", "foo")
    assert False == strategy.hit(one_per_minute, "test_namespace", "foo")
    assert True == strategy.hit(one_per_minute, "test_namespace", "bar")

    assert True == strategy.hit(one_per_second, "test_namespace", "foo")
    assert False == strategy.hit(one_per_second, "test_namespace", "foo")
    time.sleep(1)
    assert True == strategy.hit(one_per_second, "test_namespace", "foo")

Check specific limits without hitting them

.. code-block:: python

    assert True == strategy.hit(one_per_second, "test_namespace", "foo")
    while not strategy.test(one_per_second, "test_namespace", "foo"):
        time.sleep(0.01)
    assert True == strategy.hit(one_per_second, "test_namespace", "foo")

Query available capacity and reset time for a limit

.. code-block:: python

   assert True == strategy.hit(one_per_minute, "test_namespace", "foo")
   window = strategy.get_window_stats(one_per_minute, "test_namespace", "foo")
   assert window.remaining == 0
   assert False == strategy.hit(one_per_minute, "test_namespace", "foo")
   time.sleep(window.reset_time - time.time())
   assert True == strategy.hit(one_per_minute, "test_namespace", "foo")


Links
=====

* `Documentation <http://limits.readthedocs.org/en/latest>`_
* `Changelog <http://limits.readthedocs.org/en/stable/changelog.html>`_

