############
Installation
############

Install the package with pip. You can also automatically install
the required dependencies with recommended versions for a specific storage
by using the extras notation:

.. note:: When using the methods below, we use version constraints for the
   storage packages based on compatibility with the supported Python versions
   and tests in CI.


.. tabbed:: Default

   .. code:: console

      $ pip install limits

.. tabbed:: Redis

   .. code:: bash

      $ pip install limits[redis]

   Dependencies

   .. literalinclude:: ../../requirements/storage/redis.txt

.. tabbed:: RedisCluster

   .. code:: bash

      $ pip install limits[rediscluster]

   Dependencies

   .. literalinclude:: ../../requirements/storage/rediscluster.txt

.. tabbed:: Memcached

   .. code:: bash

      $ pip install limits[memcached]

   Dependencies

   .. literalinclude:: ../../requirements/storage/memcached.txt

.. tabbed:: MongoDB

   .. code-block:: shell

      $ pip install limits[mongodb]

   Dependencies

   .. literalinclude:: ../../requirements/storage/mongodb.txt

More details around the specifics of each storage backend can be
found in :ref:`storage`


*************
Async Storage
*************

If you are using an async code base you can install
the storage dependencies along with the package.


.. tabbed:: Redis

   .. code:: bash

      $ pip install limits[async-redis]

   Dependencies

   .. literalinclude:: ../../requirements/storage/async-redis.txt

.. tabbed:: Memcached

   .. code:: bash

      $ pip install limits[async-memcached]

   Dependencies

   .. literalinclude:: ../../requirements/storage/async-memcached.txt


