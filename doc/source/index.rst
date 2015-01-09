limits Documentation
--------------------

**limits** provides utilities to implement rate limiting using various strategies
and storage backends such as redis & memcached.

.. toctree::
    :hidden:

    string-notation
    strategies
    api

.. currentmodule:: limits

Quickstart
----------

Build the storage backend::

    from limits import storage
    memory_storage = storage.MemoryStorage()

Build a rate limiter with the :ref:`moving-window`::

    from limits import strategies
    moving_window = strategies.MovingWindowRateLimiter(memory_storage)


Build a rate limit using the :ref:`ratelimit-string`::

    from limits.util import parse
    one_per_minute = parse("1/minute")

Build a rate limit explicitely::

    from limits.limits import GRANULARITIES
    one_per_second = GRANULARITIES["second"](1)

Test the limits::

    assert True == moving_window.hit(one_per_minute, "test_namespace", "foo")
    assert False == moving_window.hit(one_per_minute, "test_namespace", "foo")
    assert True == moving_window.hit(one_per_minute, "test_namespace", "bar")

    assert True == moving_window.hit(one_per_second, "test_namespace", "foo")
    assert False == moving_window.hit(one_per_second, "test_namespace", "foo")
    time.sleep(1)
    assert True == moving_window.hit(one_per_second, "test_namespace", "foo")


Projects using *limits*
-------------------------
* `Flask-Limiter <http://flask-limiter.readthedocs.org>`_ : Rate limiting extension for Flask applications.
* `djlimiter <http://djlimiter.readthedocs.org>`_: Rate limiting middleware for Django applications.

References
----------
* `Redis rate limiting pattern #2 <http://redis.io/commands/INCR>`_
* `DomainTools redis rate limiter <https://github.com/DomainTools/rate-limit>`_

.. include:: ../../HISTORY.rst
.. include:: ../../CONTRIBUTIONS.rst
