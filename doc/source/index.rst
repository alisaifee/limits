limits Documentation
--------------------

**limits** provides utilities to implement rate limiting using various strategies
and storage backends such as redis & memcached.

.. toctree::
    :hidden:

    string-notation
    custom-storage
    storage
    strategies
    api
    changelog

.. currentmodule:: limits

Quickstart
----------

Initialize the storage backend::

    from limits import storage
    memory_storage = storage.MemoryStorage()

Initialize a rate limiter with the :ref:`moving-window` strategy::

    from limits import strategies
    moving_window = strategies.MovingWindowRateLimiter(memory_storage)


Initialize a rate limit using the :ref:`ratelimit-string`::

    from limits import parse
    one_per_minute = parse("1/minute")

Initialize a rate limit explicitly using a subclass of :class:`RateLimitItem`::

    from limits import RateLimitItemPerSecond
    one_per_second = RateLimitItemPerSecond(1, 1)

Test the limits::

    assert True == moving_window.hit(one_per_minute, "test_namespace", "foo")
    assert False == moving_window.hit(one_per_minute, "test_namespace", "foo")
    assert True == moving_window.hit(one_per_minute, "test_namespace", "bar")

    assert True == moving_window.hit(one_per_second, "test_namespace", "foo")
    assert False == moving_window.hit(one_per_second, "test_namespace", "foo")
    time.sleep(1)
    assert True == moving_window.hit(one_per_second, "test_namespace", "foo")

Check specific limits without hitting them::

    assert True == moving_window.hit(one_per_second, "test_namespace", "foo")
    while not moving_window.test(one_per_second, "test_namespace", "foo"):
        time.sleep(0.01)
    assert True == moving_window.hit(one_per_second, "test_namespace", "foo")

Clear a limit::

    assert True == moving_window.hit(one_per_minute, "test_namespace", "foo")
    assert False == moving_window.hit(one_per_minute, "test_namespace", "foo")
    moving_window.clear(one_per_minute, "test_namespace", "foo")
    assert True == moving_window.hit(one_per_minute, "test_namespace", "foo")


Development
-----------
Since `limits` integrates with various backend storages, local development and running tests
can require some setup. Basic `redis` & `memcached` installations are expected to be available in your environment.
If you are working with :ref:`redis-cluster`, :ref:`redis-sentinel` or :ref:`gae-memcached` you can use the makefile
``Makefile.tests`` to help with setting up development dependencies::

    make -f Makefile.tests redis-start memcached-gae-install
    # hack hack hack
    # run tests
    make -f Makefile.tests redis-stop

Projects using *limits*
-------------------------
* `Flask-Limiter <http://flask-limiter.readthedocs.org>`_ : Rate limiting extension for Flask applications.
* `djlimiter <http://djlimiter.readthedocs.org>`_: Rate limiting middleware for Django applications.
* `sanic-limiter <https://github.com/bohea/sanic-limiter>`_: Rate limiting middleware for Sanic applications.

References
----------
* `Redis rate limiting pattern #2 <http://redis.io/commands/INCR>`_
* `DomainTools redis rate limiter <https://github.com/DomainTools/rate-limit>`_

.. include:: ../../CONTRIBUTIONS.rst
