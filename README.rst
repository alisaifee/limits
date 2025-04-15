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

######
limits
######
|docs| |ci| |codecov| |pypi| |pypi-versions| |license|


**limits** is a python library for rate limiting via multiple strategies
with commonly used storage backends (Redis, Memcached & MongoDB).

The library provides identical APIs for use in sync and
`async <https://limits.readthedocs.io/en/stable/async.html>`_ codebases.


Supported Strategies
====================

All strategies support the follow methods:

- `hit <https://limits.readthedocs.io/en/stable/api.html#limits.strategies.RateLimiter.hit>`_: consume a request.
- `test <https://limits.readthedocs.io/en/stable/api.html#limits.strategies.RateLimiter.test>`_: check if a request is allowed.
- `get_window_stats <https://limits.readthedocs.io/en/stable/api.html#limits.strategies.RateLimiter.get_window_stats>`_: retrieve remaining quota and reset time.

Fixed Window
------------
`Fixed Window <https://limits.readthedocs.io/en/latest/strategies.html#fixed-window>`_

This strategy is the most memory‑efficient because it uses a single counter per resource and
rate limit. When the first request arrives, a window is started for a fixed duration
(e.g., for a rate limit of 10 requests per minute the window expires in 60 seconds from the first request).
All requests in that window increment the counter and when the window expires, the counter resets.

Burst traffic that bypasses the rate limit may occur at window boundaries.

For example, with a rate limit of 10 requests per minute:

- At **00:00:45**, the first request arrives, starting a window from **00:00:45** to **00:01:45**.
- All requests between **00:00:45** and **00:01:45** count toward the limit.
- If 10 requests occur at any time in that window, any further request before **00:01:45** is rejected.
- At **00:01:45**, the counter resets and a new window starts which would allow 10 requests
  until **00:02:45**.

Moving Window
-------------
`Moving Window <https://limits.readthedocs.io/en/latest/strategies.html#moving-window>`_

This strategy adds each request’s timestamp to a log if the ``nth`` oldest entry (where ``n``
is the limit) is either not present or is older than the duration of the window (for example with a rate limit of
``10 requests per minute`` if there are either less than 10 entries or the 10th oldest entry is at least
60 seconds old). Upon adding a new entry to the log "expired" entries are truncated.

For example, with a rate limit of 10 requests per minute:

- At **00:00:10**, a client sends 1 requests which are allowed.
- At **00:00:20**, a client sends 2 requests which are allowed.
- At **00:00:30**, the client sends 4 requests which are allowed.
- At **00:00:50**, the client sends 3 requests which are allowed (total = 10).
- At **00:01:11**, the client sends 1 request. The strategy checks the timestamp of the
  10th oldest entry (**00:00:10**) which is now 61 seconds old and thus expired. The request
  is allowed.
- At **00:01:12**, the client sends 1 request. The 10th oldest entry's timestamp is **00:00:20**
  which is only 52 seconds old. The request is rejected.

Sliding Window Counter
------------------------
`Sliding Window Counter <https://limits.readthedocs.io/en/latest/strategies.html#sliding-window-counter>`_

This strategy approximates the moving window while using less memory by maintaining
two counters:

- **Current bucket:** counts requests in the ongoing period.
- **Previous bucket:** counts requests in the immediately preceding period.

When a request arrives, the effective request count is calculated as::

    weighted_count = current_count + floor(previous_count * weight)

The weight is based on how much time has elapsed in the current bucket::

    weight = (bucket_duration - elapsed_time) / bucket_duration

If ``weighted_count`` is below the limit, the request is allowed.

For example, with a rate limit of 10 requests per minute:

Assume:

- The current bucket (spanning **00:01:00** to **00:02:00**) has 8 hits.
- The previous bucket (spanning **00:00:00** to **00:01:00**) has 4 hits.

Scenario 1:

- A new request arrives at **00:01:30**, 30 seconds into the current bucket.
- ``weight = (60 - 30) / 60 = 0.5``.
- ``weighted_count = floor(8 + (4 * 0.5)) = floor(8 + 2) = 10``.
- Since the weighted count equals the limit, the request is rejected.

Scenario 2:

- A new request arrives at **00:01:40**, 40 seconds into the current bucket.
- ``weight = (60 - 40) / 60 ≈ 0.33``.
- ``weighted_count = floor(8 + (4 * 0.33)) = floor(8 + 1.32) = 9``.
- Since the weighted count is below the limit, the request is allowed.


Storage backends
================

- `Redis <https://limits.readthedocs.io/en/latest/storage.html#redis-storage>`_
- `Memcached <https://limits.readthedocs.io/en/latest/storage.html#memcached-storage>`_
- `MongoDB <https://limits.readthedocs.io/en/latest/storage.html#mongodb-storage>`_
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
* `Benchmarks <http://limits.readthedocs.org/en/latest/performance.html>`_
* `Changelog <http://limits.readthedocs.org/en/stable/changelog.html>`_

