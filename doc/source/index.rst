========
*limits*
========
.. container:: badges

   .. image:: https://img.shields.io/github/last-commit/alisaifee/limits?logo=github&style=for-the-badge&labelColor=#282828
      :target: https://github.com/alisaifee/limits
      :class: header-badge
   .. image:: https://img.shields.io/github/actions/workflow/status/alisaifee/limits/main.yml?logo=github&style=for-the-badge&labelColor=#282828
      :target: https://github.com/alisaifee/limits/actions/workflows/main.yml
   .. image:: https://img.shields.io/codecov/c/github/alisaifee/limits?logo=codecov&style=for-the-badge&labelColor=#282828
      :target: https://app.codecov.io/gh/alisaifee/limits
      :class: header-badge
   .. image:: https://img.shields.io/pypi/pyversions/limits?style=for-the-badge&logo=pypi
      :target: https://pypi.org/project/limits
      :class: header-badge

----

*limits* is a python library to perform rate limiting with commonly used
storage backends (Redis, Memcached & MongoDB).


Get started by taking a look at :ref:`installation:installation` and :ref:`quickstart:quickstart`.

To learn more about the different strategies refer to the :ref:`strategies:rate limiting strategies` section.

For an overview of supported backends refer to :ref:`storage:storage backends`.

.. toctree::
    :maxdepth: 3
    :hidden:

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
requires a a working `docker & docker-compose installation <https://docs.docker.com/compose/gettingstarted/>`_.

Running the tests will start the relevant containers automatically - but will leave them running
so as to not incur the overhead of starting up on each test run. To run the tests:

.. code:: console

   $ pytest

Once you're done - you will probably want to clean up the docker containers:

.. code:: console

   $ docker-compose down


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
