.. :changelog:

Changelog
=========

v2.6.0
------
Release Date: 2022-04-25

* Deprecation

  * Removed tests for rediscluster using the :pypi:`redis-py-cluster` library

* Bug Fix

  * Fix incorrect ``__slots__`` declaration in :class:`limits.RateLimitItem`
    and it's subclasses (`Issue #121 <https://github.com/alisaifee/limits/issues/121>`__)

v2.5.3
------
Release Date: 2022-04-22

* Chore

  * Automate Github releases

v2.5.2
------
Release Date: 2022-04-17

* Chore

  * Increase strictness of type checking and annotations
  * Ensure installations from source distributions are PEP-561
    compliant

v2.5.1
------
Release Date: 2022-04-15

* Chore

  * Ensure storage reset methods have consistent signature

v2.5.0
------
Release Date: 2022-04-13

* Feature

  * Add support for using redis cluster via the official redis client
  * Update coredis dependency to use 3.x

* Deprecations

  * Deprecate using redis-py-cluster

* Chores

  * Remove beta tags for async support
  * Update code base to remove legacy syntax
  * Tighten up CI test dependencies

v2.4.0
------
Release Date: 2022-03-10

* Feature

  * Allow passing an explicit connection pool to redis storage.
    Addresses `Issue 77 <https://github.com/alisaifee/limits/issues/77>`_

v2.3.3
------
Release Date: 2022-02-03

* Feature

  * Add support for dns seed list when using mongodb

v2.3.2
------
Release Date: 2022-01-30

* Chores

  * Improve authentication tests for redis
  * Update documentation theme
  * Pin pip version for CI

v2.3.1
------
Release Date: 2022-01-21

* Bug fix

  * Fix backward incompatible change that separated sentinel
    and connection args for redis sentinel (introduced in 2.1.0).
    Addresses `Issue 97 <https://github.com/alisaifee/limits/issues/97>`_


v2.3.0
------
Release Date: 2022-01-15

* Feature

  * Add support for custom cost per hit

* Bug fix

  * Fix installation issues with missing setuptools

v2.2.0
------
Release Date: 2022-01-05

* Feature

  * Enable async redis for python 3.10 via coredis

* Chore

  * Fix typing issue with strategy constructors

v2.1.1
------
Release Date: 2022-01-02

* Feature

  * Enable async memcache for python 3.10

* Bug fix

  * Ensure window expiry is reported in local time for mongodb
  * Fix inconsistent expiry for fixed window with memcached

* Chore

  * Improve strategy tests

v2.1.0
------
Release Date: 2021-12-22

* Feature

  * Add beta asyncio support
  * Add beta mongodb support
  * Add option to install with extras for different storages

* Bug fix

  * Fix custom option for cluster client in memcached
  * Fix separation of sentinel & connection args in :class:`limits.storage.RedisSentinelStorage`

* Deprecation

  * Deprecate GAEMemcached support
  * Remove use of unused `no_add` argument in :meth:`limits.storage.MovingWindowSupport.acquire_entry`

* Chore

  * Documentation theme upgrades
  * Code linting
  * Add compatibility CI workflow



v2.0.3
------
Release Date: 2021-11-28

* Chore

  * Ensure package is marked PEP-561 compliant

v2.0.1
------
Release Date: 2021-11-28

* Chore

  * Added type annotations

v2.0.0
------
Release Date: 2021-11-27

* Chore

  * Drop support for python < 3.7

v1.6
----
Release Date: 2021-11-27

* Chore

  * Final release for python < 3.7

v1.5.1
------
Release Date: 2020-02-25

* Bug fix

  * Remove duplicate call to ttl in RedisStorage
  * Initialize master/slave connections for RedisSentinel once

v1.5
----
Release Date: 2020-01-23

* Bug fix for handling TTL response from Redis when key doesn’t exist
* Support Memcache over unix domain socket
* Support Memcache cluster
* Pass through constructor keyword arguments to underlying storage
  constructor(s)
* CI & test improvements

v1.4.1
------
Release Date: 2019-12-15

* Bug fix for implementation of clear in MemoryStorage
  not working with MovingWindow

v1.4
----
Release Date: 2019-12-14

* Expose API for clearing individual limits
* Support for redis over unix domain socket
* Support extra arguments to redis storage

v1.3
------
Release Date: 2018-01-28

* Remove pinging redis on initialization

v1.2.1
------
Release Date: 2017-01-02

* Fix regression with csv as multiple limits

v1.2.0
------
Release Date: 2016-09-21

* Support reset for RedisStorage
* Improved rate limit string parsing

v1.1.1
------
Release Date: 2016-03-14

* Support reset for MemoryStorage
* Support for `rediss://` storage scheme to connect to redis over ssl

v1.1
----
Release Date: 2015-12-20

* Redis Cluster support
* Authentiation for Redis Sentinel
* Bug fix for locking failures with redis.

v1.0.9
------
Release Date: 2015-10-08

* Redis Sentinel storage support
* Drop support for python 2.6
* Documentation improvements

v1.0.7
------
Release Date: 2015-06-07

* No functional change

v1.0.6
------
Release Date: 2015-05-13

* Bug fixes for .test() logic

v1.0.5
------
Release Date: 2015-05-12

* Add support for testing a rate limit before hitting it.

v1.0.3
------
Release Date: 2015-03-20

* Add support for passing options to storage backend

v1.0.2
------
Release Date: 2015-01-10

* Improved documentation
* Improved usability of API. Renamed RateLimitItem subclasses.

v1.0.1
------
Release Date: 2015-01-08

* Example usage in docs.

v1.0.0
------
Release Date: 2015-01-08

* Initial import of common rate limiting code from `Flask-Limiter <https://github.com/alisaifee/flask-limiter>`_








































