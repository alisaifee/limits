.. :changelog:

Changelog
---------

1.5.1 2020-02-25
================
* Bug fix

  * Remove duplicate call to ttl in RedisStorage
  * Initialize master/slave connections for RedisSentinel once

1.5 2020-01-23
==============
* Bug fix for handling TTL response from Redis when key doesn’t exist
* Support Memcache over unix domain socket
* Support Memcache cluster
* Pass through constructor keyword arguments to underlying storage
  constructor(s)
* CI & test improvements

1.4.1 2019-12-15
================
* Bug fix for implementation of clear in MemoryStorage
  not working with MovingWindow

1.4 2019-12-14
==============
* Expose API for clearing individual limits
* Support for redis over unix domain socket
* Support extra arguments to redis storage

1.3 2018-01-28
==============
* Remove pinging redis on initialization

1.2.1 2017-01-02
================
* Fix regression with csv as multiple limits

1.2.0 2016-09-21
================
* Support reset for RedisStorage
* Improved rate limit string parsing

1.1.1 2016-03-14
================
* Support reset for MemoryStorage
* Support for `rediss://` storage scheme to connect to redis over ssl

1.1 2015-12-20
==============
* Redis Cluster support
* Authentiation for Redis Sentinel
* Bug fix for locking failures with redis.

1.0.9 2015-10-08
================
* Redis Sentinel storage support
* Drop support for python 2.6
* Documentation improvements

1.0.7 2015-06-07
================
* No functional change

1.0.6 2015-05-13
================
* Bug fixes for .test() logic

1.0.5 2015-05-12
================
* Add support for testing a rate limit before hitting it.

1.0.3 2015-03-20
================
* Add support for passing options to storage backend

1.0.2 2015-01-10
================
* Improved documentation
* Improved usability of API. Renamed RateLimitItem subclasses.

1.0.1 2015-01-08
================
* Example usage in docs.

1.0.0 2015-01-08
================
* Initial import of common rate limiting code from `Flask-Limiter <https://github.com/alisaifee/flask-limiter>`_

















