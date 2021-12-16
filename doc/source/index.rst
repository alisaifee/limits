.. role:: bash(code)
   :language: bash
   :class: highlight

######
limits
######

A high level python API to perform rate limiting using :ref:`strategies:fixed window`
or :ref:`strategies:moving window` strategies and some commonly used storage backends
(Redis, Memcached & MongoDB at the moment).

Take a look at :ref:`installation:installation` and :ref:`quickstart:quickstart` to start using the library.

To learn more about the different strategies refer to the :ref:`strategies:rate limiting strategies`
section.


.. toctree::
    :maxdepth: 1

    installation
    quickstart
    strategies
    storage
    async
    api
    custom-storage
    changelog

.. currentmodule:: limits

###########
Development
###########

Since `limits` integrates with various backend storages, local development and running tests
can require some setup.

You can use the provided Makefile to set up all the backends. This will require a working
docker installation. Additionally on OSX you will require the ``memcached`` and
``redis-server`` executables to be on the path::

    make setup-test-backends
    # hack hack hack
    # run tests
    pytest

#######################
Projects using *limits*
#######################

   - `Flask-Limiter <http://flask-limiter.readthedocs.org>`_ : Rate limiting extension for Flask applications.
   - `djlimiter <http://djlimiter.readthedocs.org>`_: Rate limiting middleware for Django applications.
   - `sanic-limiter <https://github.com/bohea/sanic-limiter>`_: Rate limiting middleware for Sanic applications.
   - `Falcon-Limiter <https://falcon-limiter.readthedocs.org>`_ : Rate limiting extension for Falcon applications.

##########
References
##########

   - `Redis rate limiting pattern #2 <http://redis.io/commands/INCR>`_
   - `DomainTools redis rate limiter <https://github.com/DomainTools/rate-limit>`_

.. include:: ../../CONTRIBUTIONS.rst
