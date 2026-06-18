============
Installation
============

Install the package with pip:

.. code:: console

   $ pip install limits

.. tab:: Redis

   .. code:: console

      $ pip install limits[redis]

   Includes

   .. code:: text

      redis>3,!=4.5.2,!=4.5.3,<8.0.0

.. tab:: RedisCluster

   .. code:: console

      $ pip install limits[rediscluster]

   Includes

   .. code:: text

      redis>=4.2.0,!=4.5.2,!=4.5.3

.. tab:: Memcached

   .. code:: console

      $ pip install limits[memcached]

   Includes

   .. code:: text

      pymemcache>3,<5.0.0

.. tab:: MongoDB

   .. code:: console

      $ pip install limits[mongodb]

   Includes:

   .. code:: text

      pymongo>4.1,<5

.. tab:: Valkey

   .. code:: console

      $ pip install limits[valkey]

   Includes:

   .. code:: text

      valkey>=6

More details around the specifics of each storage backend can be
found in :ref:`storage`


Async Storage
=============

If you are using an async code base you can install the storage dependencies
along with the package using the following extras:


.. tab:: Redis

   .. code:: console

      $ pip install limits[async-redis]

   Includes:

   .. code:: text

      coredis>=3.4.0,<6

   .. versionadded:: 4.2
      :pypi:`redis` if installed can be used instead of :pypi:`coredis` by setting
      :paramref:`~limits.aio.storage.RedisStorage.implementation` to ``redispy``.
      See :class:`limits.aio.storage.RedisStorage` for more details.


.. tab:: Memcached

   .. code:: console

      $ pip install limits[async-memcached]

   Includes:

   .. code:: text

      memcachio>=0.3

   .. versionchanged:: 5.0
      :pypi:`emcache` if installed can be used instead of the new default
      :pypi:`memcachio` by setting :paramref:`~limits.aio.storage.MemcachedStorage.implementation`
      to ``emcache``.

.. tab:: MongoDB

   .. code:: console

      $ pip install limits[async-mongodb]

   Includes:

   .. code:: text

      motor>=3,<4

.. tab:: Valkey

   .. code:: console

      $ pip install limits[async-valkey]

   Includes:

   .. code:: text

      valkey>=6


