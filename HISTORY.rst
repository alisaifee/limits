.. :changelog:

Changelog
---------

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











