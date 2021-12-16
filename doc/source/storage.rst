.. currentmodule:: limits

.. _storage:

################
Storage Backends
################

.. _storage-scheme:

**************
Storage scheme
**************

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
and handled differently by each implementation. Please refer to the API documentation in
the :ref:`api:storage` section for details.


********
Examples
********

In-Memory
---------
The in-memory storage (:class:`~limits.storage.MemoryStorage`) takes no parameters so the only relevant value is :code:`memory://`

Memcached
---------

 Requires the location of the memcached server(s). As such
 the parameters is a comma separated list of :code:`{host}:{port}` locations such as
 :code:`memcached://localhost:11211` or
 :code:`memcached://localhost:11211,localhost:11212,192.168.1.1:11211` etc...
 or a path to a unix domain socket such as :code:`memcached:///var/tmp/path/to/sock`

 Depends on: :pypi:`pymemcache`

Memcached on Google App Engine
------------------------------

  .. deprecated:: 2.0

  Requires that you are working in the GAE SDK and have those API libraries available.

  :code:`gaememcached://`


Redis
-----

 Requires the location of the redis server and optionally the database number.
 :code:`redis://localhost:6379` or :code:`redis://localhost:6379/n` (for database `n`).

 If the redis server is listening over a unix domain socket you can use :code:`redis+unix:///path/to/sock`
 or :code:`redis+unix:///path/to/socket?db=n` (for database `n`).

 If the database is password protected the password can be provided in the url, for example
 :code:`redis://:foobared@localhost:6379` or :code:`redis+unix//:foobered/path/to/socket` if using a UDS..

 Depends on: :pypi:`redis`

Redis over SSL
--------------

 The official Redis client :pypi:`redis` supports redis connections over SSL with the scheme
 You can add ssl related parameters in the url itself, for example:
 :code:`rediss://localhost:6379/0?ssl_ca_certs=./tls/ca.crt&ssl_keyfile=./tls/client.key`.


 Depends on: :pypi:`redis`

Redis with Sentinel
-------------------

 Requires the location(s) of the redis sentinal instances and the `service-name`
 that is monitored by the sentinels.
 :code:`redis+sentinel://localhost:26379/my-redis-service`
 or :code:`redis+sentinel://localhost:26379,localhost:26380/my-redis-service`.

 If the database is password protected the password can be provided in the url, for example
 :code:`redis+sentinel://:sekret@localhost:26379/my-redis-service`

 Depends on: :pypi:`redis`

Redis Cluster
-------------

 Requires the location(s) of the redis cluster startup nodes (One is enough).
 :code:`redis+cluster://localhost:7000`
 or :code:`redis+cluster://localhost:7000,localhost:70001`

 Depends on: :pypi:`redis-py-cluster`

MongoDB
-------

 Requires the location(s) of a mongodb installation using the uri schema
 described by the `Mongodb URI Specification <https://github.com/mongodb/specifications/blob/master/source/uri-options/uri-options.rst>`_

 Examples:

  - Local instance: ``mongodb://localhost:27017/``
  - Instance with SSL: ``mongodb://mymongo.com/?tls=true``
  - Local instance with SSL & self signed/invalid certificate: ``mongodb://localhost:27017/?tls=true&tlsAllowInvalidCertificates=true``

 Depends on: :pypi:`pymongo`

*************
Async Storage
*************

.. versionadded:: 2.1
.. danger:: Experimental

When using limits in an async code base the same uri schema can be used
to query for an async (limited support) implementation of the storage
by prefixing the scheme with ``async+``.

For example:

- ``async+redis://``
- ``async+memcached://``
- ``async+memory://``

For implementation details of currently supported async backends refer to :ref:`api:async storage`
