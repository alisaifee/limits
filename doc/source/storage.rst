.. currentmodule:: limits

Storage Backends
----------------

.. _storage-scheme:

Storage scheme
==============
**limits** uses a url style storage scheme notation (similar to the JDBC driver
connection string notation) for configuring and initializing
storage backends. This notation additionally provides a simple
mechanism to both identify and configure the backend implementation based on
a single string argument.

The storage scheme follows the format :code:`{scheme}://{parameters}`

:func:`limits.storage.storage_from_string` is provided to
lookup and construct an instance of a storage based on the storage scheme. For example::

 import limits.storage
 uri = "redis://localhost:9999"
 options = {}
 redis_storage = limits.storage.storage_from_string(uri, **options)

The additional `options` key-word arguments are passed as is to the constructor of the storage
and handled differently by each implementation. Please refer to the class documentation of
:ref:`backend-implementation` for details.

Examples
========

=========
In-Memory
=========
The in-memory storage (:class:`limits.storage.MemoryStorage`) takes no parameters so the only relevant value is :code:`memory://`

.. _memcached:

=========
Memcached
=========

 Requires the location of the memcached server(s). As such
 the parameters is a comma separated list of :code:`{host}:{port}` locations such as
 :code:`memcached://localhost:11211` or
 :code:`memcached://localhost:11211,localhost:11212,192.168.1.1:11211` etc...
 or a path to a unix domain socket such as :code:`memcached:///var/tmp/path/to/sock`

 Depends on: `pymemcache <https://pymemcache.readthedocs.io/en/latest/>`__

.. _gae-memcached:

==============================
Memcached on Google App Engine
==============================

  Requires that you are working in the GAE SDK and have those API libraries available.
  :code: `gaememcached://`


.. _redis:

=====
Redis
=====

 Requires the location of the redis server and optionally the database number.
 :code:`redis://localhost:6379` or :code:`redis://localhost:6379/n` (for database `n`).

 If the redis server is listening over a unix domain socket you can use :code:`redis+unix:///path/to/sock`
 or :code:`redis+unix:///path/to/socket?db=n` (for database `n`).

 If the database is password protected the password can be provided in the url, for example
 :code:`redis://:foobared@localhost:6379` or :code:`redis+unix//:foobered/path/to/socket` if using a UDS..

 Depends on: `redis-py <https://redis-py.readthedocs.io/en/latest/>`_

.. _redis-ssl:

==============
Redis over SSL
==============

 Redis does not support SSL natively, but it is recommended to use stunnel to provide SSL suport.
 The official Redis client :code:`redis-py` supports redis connections over SSL with the scheme
 :code:`rediss`. :code:`rediss://localhost:6379/0` just like the normal redis connection, just
 with the new scheme.

 Depends on: `redis-py <https://redis-py.readthedocs.io/en/latest/>`_

.. _redis-sentinel:

===================
Redis with Sentinel
===================

 Requires the location(s) of the redis sentinal instances and the `service-name`
 that is monitored by the sentinels.
 :code:`redis+sentinel://localhost:26379/my-redis-service`
 or :code:`redis+sentinel://localhost:26379,localhost:26380/my-redis-service`.

 If the database is password protected the password can be provided in the url, for example
 :code:`redis+sentinel://:sekret@localhost:26379/my-redis-service`

 Depends on: `redis-py <https://redis-py.readthedocs.io/en/latest/>`_

.. _redis-cluster:

=============
Redis Cluster
=============

 Requires the location(s) of the redis cluster startup nodes (One is enough).
 :code:`redis+cluster://localhost:7000`
 or :code:`redis+cluster://localhost:7000,localhost:70001`

 Depends on: `redis-py-cluster <https://redis-py-cluster.readthedocs.io/en/latest/>`_
