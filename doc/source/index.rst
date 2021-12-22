========
*limits*
========
.. container:: badges

   .. image:: https://img.shields.io/github/last-commit/alisaifee/limits?logo=github&style=flat-square&labelColor=#282828
      :target: https://github.com/alisaifee/limits
      :class: header-badge
   .. image:: https://img.shields.io/github/workflow/status/alisaifee/limits/CI?logo=github&style=flat-square&labelColor=#282828
      :target: https://github.com/alisaifee/limits/actions/workflows/main.yml
   .. image:: https://img.shields.io/codecov/c/github/alisaifee/limits?logo=codecov&style=flat-square&labelColor=#282828
      :target: https://app.codecov.io/gh/alisaifee/limits
      :class: header-badge
   .. image:: https://img.shields.io/pypi/pyversions/limits?style=flat-square&logo=pypi
      :target: https://pypi.org/project/limits
      :class: header-badge

*limits* is a python library to perform rate limiting with commonly used
storage backends (Redis, Memcached & MongoDB).

----

Take a look at :ref:`installation:installation` and :ref:`quickstart:quickstart`
to start using *limits*.

To learn more about the different strategies refer to the
:ref:`strategies:rate limiting strategies` section.

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

----


Development
===========

The source is available on `Github <https://github.com/alisaifee/limits>`_

To get started

.. code:: console

   $ git clone git://github.com/alisaifee/limits.git
   $ cd limits
   $ pip install -r requirements/dev.txt

Since `limits` integrates with various backend storages, local development and running tests
can require some setup.

You can use the provided Makefile to set up all the backends.
This will require a working `docker & docker-compose installation <https://docs.docker.com/compose/gettingstarted/>`_.

.. note:: On OSX you'll also need a working installation of `redis` & `memcached`

.. code:: console

   $ make setup-test-backends
   $ # hack hack hack
   $ pytest
   $ make teardown-test-backends



Projects using *limits*
=======================

   - `Flask-Limiter <http://flask-limiter.readthedocs.org>`_ : Rate limiting extension for Flask applications.
   - `djlimiter <http://djlimiter.readthedocs.org>`_: Rate limiting middleware for Django applications.
   - `sanic-limiter <https://github.com/bohea/sanic-limiter>`_: Rate limiting middleware for Sanic applications.
   - `Falcon-Limiter <https://falcon-limiter.readthedocs.org>`_ : Rate limiting extension for Falcon applications.

References
==========

   - `Redis rate limiting pattern #2 <http://redis.io/commands/INCR>`_
   - `DomainTools redis rate limiter <https://github.com/DomainTools/rate-limit>`_

.. include:: ../../CONTRIBUTIONS.rst
