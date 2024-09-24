.. |ci| image:: https://github.com/alisaifee/limits/workflows/CI/badge.svg?branch=master
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
`Fixed Window <https://limits.readthedocs.io/en/latest/strategies.html#fixed-window>`_
   This strategy resets at a fixed interval (start of minute, hour, day etc).
   For example, given a rate limit of ``10/minute`` the strategy will:

   - Allow 10 requests between ``00:01:00`` and ``00:02:00``
   - Allow 10 requests at ``00:00:59`` and 10 more requests at ``00:01:00``


`Fixed Window (Elastic) <https://limits.readthedocs.io/en/latest/strategies.html#fixed-window-with-elastic-expiry>`_
   Identical to Fixed window, except every breach of rate limit results in an extension
   to the time out. For example a rate limit of `1/minute` hit twice within a minute will
   result in a lock-out for two minutes.

`Moving Window <https://limits.readthedocs.io/en/latest/strategies.html#moving-window>`_
   Sliding window strategy enforces a rate limit of N/(m time units)
   on the **last m** time units at the second granularity.

   For example, with a rate limit of ``10/minute``:

   - Allow 9 requests that arrive at ``00:00:59``
   - Allow another request that arrives at ``00:01:00``
   - Reject the request that arrives at ``00:01:01``

`Concurrency limit`

   Limits the number of simultaneous or concurrent executions (or tokens in use)
   without focusing on the rate of requests over time. It enforces a maximum
   limit of tasks allowed to run in parallel.

   For example, with a concurrency limit of 5:

   - Allow up to 5 tasks or requests to be processed concurrently
   - Reject any further requests until one of the 5 tasks completes and releases a slot
   - Once a task finishes, the limit is reduced, allowing new tasks to be executed   

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
   memory_storage = storage.MemoryStorage()
   # or memcached
   memcached_storage = storage.MemcachedStorage("memcached://localhost:11211")
   # or redis
   redis_storage = storage.RedisStorage("redis://localhost:6379")
   # or use the factory
   storage_uri = "memcached://localhost:11211"
   some_storage = storage.storage_from_string(storage_uri)

Initialize a rate limiter with the Moving Window Strategy

.. code-block:: python

   from limits import strategies
   moving_window = strategies.MovingWindowRateLimiter(memory_storage)


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

    assert True == moving_window.hit(one_per_minute, "test_namespace", "foo")
    assert False == moving_window.hit(one_per_minute, "test_namespace", "foo")
    assert True == moving_window.hit(one_per_minute, "test_namespace", "bar")

    assert True == moving_window.hit(one_per_second, "test_namespace", "foo")
    assert False == moving_window.hit(one_per_second, "test_namespace", "foo")
    time.sleep(1)
    assert True == moving_window.hit(one_per_second, "test_namespace", "foo")

Check specific limits without hitting them

.. code-block:: python

    assert True == moving_window.hit(one_per_second, "test_namespace", "foo")
    while not moving_window.test(one_per_second, "test_namespace", "foo"):
        time.sleep(0.01)
    assert True == moving_window.hit(one_per_second, "test_namespace", "foo")

Links
=====

* `Documentation <http://limits.readthedocs.org/en/latest>`_
* `Changelog <http://limits.readthedocs.org/en/stable/changelog.html>`_

