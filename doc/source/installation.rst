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

   .. literalinclude:: ../../requirements/storage/redis.txt

.. tab:: RedisCluster

   .. code:: console

      $ pip install limits[rediscluster]

   Includes

   .. literalinclude:: ../../requirements/storage/rediscluster.txt

.. tab:: Memcached

   .. code:: console

      $ pip install limits[memcached]

   Includes

   .. literalinclude:: ../../requirements/storage/memcached.txt

.. tab:: MongoDB

   .. code:: console

      $ pip install limits[mongodb]

   Includes:

   .. literalinclude:: ../../requirements/storage/mongodb.txt

.. tab:: Valkey

   .. code:: console

      $ pip install limits[valkey]

   Includes:

   .. literalinclude:: ../../requirements/storage/valkey.txt

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

   .. literalinclude:: ../../requirements/storage/async-redis.txt

   .. versionadded:: 4.2
      :pypi:`redis` if installed can be used instead of :pypi:`coredis` by setting
      :paramref:`~limits.aio.storage.RedisStorage.implementation` to ``redispy``.
      See :class:`limits.aio.storage.RedisStorage` for more details.


.. tab:: Memcached

   .. code:: console

      $ pip install limits[async-memcached]

   Includes:

   .. literalinclude:: ../../requirements/storage/async-memcached.txt

   .. versionchanged:: 5.0
      :pypi:`emcache` if installed can be used instead of the new default
      :pypi:`memcachio` by setting :paramref:`~limits.aio.storage.MemcachedStorage.implementation`
      to ``emcache``.

.. tab:: MongoDB

   .. code:: console

      $ pip install limits[async-mongodb]

   Includes:

   .. literalinclude:: ../../requirements/storage/async-mongodb.txt

.. tab:: Valkey

   .. code:: console

      $ pip install limits[async-valkey]

   Includes:

   .. literalinclude:: ../../requirements/storage/async-valkey.txt


