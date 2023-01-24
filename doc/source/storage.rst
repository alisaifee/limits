.. currentmodule:: limits

.. _storage:

================
Storage Backends
================

Supported versions
==================

.. image:: https://img.shields.io/github/actions/workflow/status/alisaifee/limits/compatibility.yml?logo=github&style=for-the-badge&labelColor=#282828
   :alt: GitHub Workflow Status
   :target: https://github.com/alisaifee/limits/actions/workflows/compatibility.yml

-----

**limits** is tested and known to work with the following versions of the
dependency libraries and the associated storage versions.

The CI tests against these versions on a nightly basis and you can see
the results in `github <https://github.com/alisaifee/limits/actions/workflows/compatibility.yml>`_.

.. tab:: Redis

   Dependency versions:

     .. literalinclude:: ../../requirements/storage/redis.txt

   Dependency versions (async):

     .. literalinclude:: ../../requirements/storage/async-redis.txt

   `Redis <https://redis.io>`_

     .. program-output:: bash -c "cat ../../.github/workflows/compatibility.yml | grep -o -P 'LIMITS_REDIS_SERVER_VERSION=[\d\.]+' | cut -d = -f 2"

   Redis with SSL

     .. program-output:: bash -c "cat ../../.github/workflows/compatibility.yml | grep -o -P 'LIMITS_REDIS_SERVER_SSL_VERSION=[\d\.]+' | cut -d = -f 2"

   `Redis Sentinel <https://redis.io/topics/sentinel>`_

     .. program-output:: bash -c "cat ../../.github/workflows/compatibility.yml | grep -o -P 'LIMITS_REDIS_SENTINEL_SERVER_VERSION=[\d\.]+' | cut -d = -f 2"

.. tab:: Redis Cluster

   Dependency versions:

     .. literalinclude:: ../../requirements/storage/rediscluster.txt

   Dependency versions (async):

     .. literalinclude:: ../../requirements/storage/async-redis.txt

   `Redis cluster <https://redis.io/topics/cluster-tutorial>`_

     .. program-output:: bash -c "cat ../../.github/workflows/compatibility.yml | grep -o -P 'LIMITS_REDIS_SERVER_VERSION=[\d\.]+' | cut -d = -f 2"

.. tab:: Memcached

   Dependency versions:

     .. literalinclude:: ../../requirements/storage/memcached.txt

   Dependency versions (async):

     .. literalinclude:: ../../requirements/storage/async-memcached.txt

   `Memcached <https://memcached.org/>`_

     .. program-output:: bash -c "cat ../../.github/workflows/compatibility.yml | grep -o -P 'LIMITS_MEMCACHED_SERVER_VERSION=[\d\.]+' | cut -d = -f 2"

.. tab:: MongoDB

   Dependency versions:

     .. literalinclude:: ../../requirements/storage/mongodb.txt

   Dependency versions (async):

     .. literalinclude:: ../../requirements/storage/async-mongodb.txt

   `MongoDB <https://www.mongodb.com/>`_

     .. program-output:: bash -c "cat ../../.github/workflows/compatibility.yml | grep -o -P 'LIMITS_MONGODB_SERVER_VERSION=[\d\.]+' | cut -d = -f 2"

.. tab:: Etcd

   Dependency versions:

     .. literalinclude:: ../../requirements/storage/etcd.txt

   Dependency versions (async):

     .. literalinclude:: ../../requirements/storage/async-etcd.txt

   `Etcd <https://www.etcd.io/>`_

     .. program-output:: bash -c "cat ../../.github/workflows/compatibility.yml | grep -o -P 'LIMITS_ETCD_SERVER_VERSION=[\d\.]+' | cut -d = -f 2"


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
and handled differently by each implementation. Please refer to the API documentation in
the :ref:`api:storage` section for details.


Examples
========

In-Memory Storage
-----------------
The in-memory storage (:class:`~limits.storage.MemoryStorage`) takes no parameters so the only relevant value is :code:`memory://`

Memcached Storage
-----------------

Requires the location of the memcached server(s). As such
the parameters is a comma separated list of :code:`{host}:{port}` locations such as
:code:`memcached://localhost:11211` or
:code:`memcached://localhost:11211,localhost:11212,192.168.1.1:11211` etc...
or a path to a unix domain socket such as :code:`memcached:///var/tmp/path/to/sock`

Depends on: :pypi:`pymemcache`

Redis Storage
-------------

Requires the location of the redis server and optionally the database number.
:code:`redis://localhost:6379` or :code:`redis://localhost:6379/n` (for database `n`).

If the redis server is listening over a unix domain socket you can use :code:`redis+unix:///path/to/sock`
or :code:`redis+unix:///path/to/socket?db=n` (for database `n`).

If the database is password protected the password can be provided in the url, for example
:code:`redis://:foobared@localhost:6379` or :code:`redis+unix://:foobered/path/to/socket` if using a UDS..

For scenarios where a redis connection pool is already available and can be reused, it can be provided
in :paramref:`~limits.storage.storage_from_string.options`, for example::

    pool = redis.connections.BlockingConnectionPool.from_url("redis://.....")
    storage_from_string("redis://", connection_pool=pool)

Depends on: :pypi:`redis`

Redis+SSL Storage
-----------------

The official Redis client :pypi:`redis` supports redis connections over SSL with the scheme
You can add ssl related parameters in the url itself, for example:
:code:`rediss://localhost:6379/0?ssl_ca_certs=./tls/ca.crt&ssl_keyfile=./tls/client.key`.


Depends on: :pypi:`redis`

Redis+Sentinel Storage
----------------------

Requires the location(s) of the redis sentinal instances and the `service-name`
that is monitored by the sentinels.
:code:`redis+sentinel://localhost:26379/my-redis-service`
or :code:`redis+sentinel://localhost:26379,localhost:26380/my-redis-service`.

If the sentinel is password protected the username and/or password can be provided in the url,
for example  :code:`redis+sentinel://:sekret@localhost:26379/my-redis-service`

When authentication details are provided in the url they will be used for both the sentinel
and as connection arguments for the underlying redis nodes managed by the sentinel.

If you need fine grained control it is recommended to use the additional :paramref:`~limits.storage.storage_from_string.options`
arguments. More details can be found in the API documentation for :class:`~limits.storage.RedisSentinelStorage` (or the aysnc version: :class:`~limits.aio.storage.RedisSentinelStorage`).

Depends on: :pypi:`redis`

Redis Cluster Storage
---------------------

Requires the location(s) of the redis cluster startup nodes (One is enough).
:code:`redis+cluster://localhost:7000`
or :code:`redis+cluster://localhost:7000,localhost:7001`

If the cluster is password protected the username and/or password can be provided in the url,
for example  :code:`redis+cluster://:sekret@localhost:7000,localhost:7001`

Depends on: :pypi:`redis`

MongoDB Storage
---------------

Requires the location(s) of a mongodb installation using the uri schema
described by the `Mongodb URI Specification <https://github.com/mongodb/specifications/blob/master/source/uri-options/uri-options.rst>`_

Examples:

  - Local instance: ``mongodb://localhost:27017/``
  - Instance with SSL: ``mongodb://mymongo.com/?tls=true``
  - Local instance with SSL & self signed/invalid certificate: ``mongodb://localhost:27017/?tls=true&tlsAllowInvalidCertificates=true``

Depends on: :pypi:`pymongo`

Etcd Storage
------------

Requires the location of an etcd node

Example: ``etcd://localhost:2379``

Depends on: :pypi:`etcd3`

Async Storage
=============

.. versionadded:: 2.1

When using limits in an async code base the same uri schema can be used
to query for an async implementation of the storage by prefixing the
scheme with ``async+``.

For example:

- ``async+redis://localhost:6379/0``
- ``async+rediss://localhost:6379/0``
- ``async+redis+cluster://localhost:7000,localhost:7001``
- ``async+redis+sentinel://:sekret@localhost:26379/my-redis-service``
- ``async+memcached://localhost:11211``
- ``async+etcd://localhost:2379``
- ``async+memory://``

For implementation details of currently supported async backends refer to :ref:`api:async storage`
