.. :changelog:

Changelog
=========

v5.4.0
------
Release Date: 2025-06-16

* Feature

  * Relax regular expression used in ``limits.parse`` and
    ``limits.parse_many`` to capture any granularity instead of
    just the hardcoded ones so that custom rate limits can
    also be extracted using the utility functions.
    `Issue 279 <https://github.com/alisaifee/limits/issues/279>`_

* Compatibility

  * Add redis 8.0 to CI

v5.3.0
------
Release Date: 2025-06-13

* Bug Fix

  * Fix race condition during expiration of in-memory
    moving window limits that resulted in incorrectly removing
    unexpired entries.
    `Issue 277 <https://github.com/alisaifee/limits/issues/277>`_

v5.2.0
------
Release Date: 2025-05-16

* Bug Fix

  * Fix incorrect behavior of the ``clear`` method for sliding window
    counter which effectively did not clear the sliding window for
    redis, memcached & in memory storage implementations.
    `Issue 276 <https://github.com/alisaifee/limits/issues/276>`_

v5.1.0
------
Release Date: 2025-04-23

* Features

  * Expose ``key_prefix`` constructor argument for all redis storage
    implementations to simplify customizing the prefix used for all
    keys created in redis.

v5.0.0
------
Release Date: 2025-04-15

* Backward incompatible changes

  * Dropped support for Fixed Window with Elastic Expiry strategy
  * Dropped support for etcd
  * Changed the default implementation for async+memached from :pypi:`emcache`
    to :pypi`:memcachio`

* Performance

  * Improved performance of redis moving window ``test`` and ``get_window_stats`` operations
    especially when dealing with large rate limits.
  * Improved performance of mongodb moving window ``test`` and ``get_window_stats`` operations.
  * Improved performance of in-memory moving window ``test`` and ``get_window_stats`` operations.
  * Reduced load on event loop when expiring limits with async in-memory implementations

v4.7.3
------
Release Date: 2025-04-12

* Documentation

  * Expand benchmark results to included preseeded limits

* Bug Fix

  * Handle clearing missing key with memcache + async

v4.7.2
------
Release Date: 2025-04-09

* Documentation

  * Improve presentation of benchmark docs

v4.7.1
------
Release Date: 2025-04-08

* Testing

  * Fix incorrect benchmark for async test method

v4.7
----
Release Date: 2025-04-08

* Documentation

  * Add benchmarking results in documentation

v4.6
----
Release Date: 2025-04-03

* Bug Fix

  * Ensure mongo clients are closed on storage destruction.
    `Issue 264 <https://github.com/alisaifee/limits/issues/264>`_

v4.5
----
Release Date: 2025-04-03

* Bug Fix

  * Fix concurrent update error when expiring moving window entries.
    `Issue 267 <https://github.com/alisaifee/limits/issues/267>`_

v4.4.1
------
Release Date: 2025-03-14

* Documentation

  * Fix deprecation documentation for etcd

v4.4
----
Release Date: 2025-03-14

* Compatibility

  * Deprecate support for ``etcd``

v4.3
----
Release Date: 2025-03-14

* Feature

  * Add support for ``valkey://`` schemas and using ``valkey-py``
    dependency

* Compatibility

  * Drop support for python 3.9
  * Improve typing to use python 3.10+ features


v4.2
----
Release Date: 2025-03-11

  * Feature

    * Add support for using ``redis-py`` instead of ``coredis``
      which asyncio + redis storages

v4.1
----
Release Date: 2025-03-07

  * Feature

    * Add new Sliding Window Counter strategy

  * Deprecation

    * Deprecate the Fixed window with elastic expiry strategy

  * Documentation

    * Re-write strategy documentation with concrete examples

v4.0.1
------
Release Date: 2025-01-16

Security

  * Change pypi release to use trusted publishing

v4.0.0
------
Release Date: 2025-01-05

* Breaking change

  * Change definition of ``reset_time`` in ``get_window_stats``
    to use a precise floating point value instead of truncating
    to the previous second.


v3.14.1
-------
Release Date: 2024-11-30

* Chore

  * Fix benchmark artifact upload/download issue during release
    creation

v3.14.0
-------
Release Date: 2024-11-29

* Feature

  * Allow custom collection names in mongodb storage

* Compatibility

  * Add support for python 3.13
  * Drop support for python 3.8

* Deprecations

  * Remove fallback support to use redis-py-cluster

v3.13.0
-------
Release Date: 2024-06-22

* Feature

  * Add ``cost`` parameter to ``test`` methods in strategies.

v3.12.0
-------
Release Date: 2024-05-12

* Enhancements

  * Lazily initialize pymongo client

* Documentation

  * Add django-ratelimiter in docs

* Chores

  * Update development dependencies
  * Update github actions to latest


v3.11.0
-------
Release Date: 2024-04-20

* Compatibility

  * Add support for python 3.12

v3.10.1
-------
Release Date: 2024-03-17

* Compatibility

  * Relax dependency constraint on packaging

v3.10.0
-------
Release Date: 2024-03-08

* Bug Fix

  * Fix incorrect mapping of coredis exceptions
  * Fix calculation of reset_time

v3.9.0
------
Release Date: 2024-02-17

* Bug Fix

  * Remove excessively low defaults for mongodb storage and instead
    delegate to the underlying dependency (pymongo, motor)


v3.8.0
------
Release Date: 2024-02-14

* Features

  * Add option to wrap storage errors with a ``StorageError``
    exception


v3.7.0
------
Release Date: 2023-11-24

* Features

  * Ensure rate limit keys in redis use are prefixed
    with a `LIMITS` prefix. This allows for resetting
    all keys generated by the library without implicit
    knowledge of the key structure.

v3.6.0
------
Release Date: 2023-08-31

* Bug Fix

  * Remove default socket timeout from mongo storage
  * Ensure _version.py has stable content when generated
    using `git archive` from a tag regardless of when it is
    run.

* Compatibility

  * Remove references to python 3.7
  * Remove unnecessary setuptools dependency

v3.5.0
------
Release Date: 2023-05-16

* Bug Fix

  * Handle ``cost`` > 8000 when using redis
  * Remove arbitrary default timeout for redis+sentinel

v3.4.0
------
Release Date: 2023-04-17

* Bug Fix

  * Remove use of weakreferences to storages in strategy
    classes as this was not documented or required and
    led to usability issues.

* Chores

  * Update documentation dependencies
  * Remove unused gcra lua script

v3.3.1
------
Release Date: 2023-03-22

* Compatibility

  * Block incompatible versions of redis-py

* Chores

  * Force error on warnings in tests

v3.3.0
------
Release Date: 2023-03-20

* Compatibility

  * Remove deprecated use of `pkg_resources` and switch
    to `importlib_resource`

* Chores

  * Update documentation dependencies
  * Update github actions versions

v3.2.0
------
Release Date: 2023-01-24

* Bug Fix

  * Fix handling of authentication details in storage url of redis cluster

* Chores

  * Add test coverage for redis cluster with auth required

v3.1.6
------
Release Date: 2023-01-16

* Bug Fix

  * Disallow acquiring amounts > limit in moving window

* Usability

  * Use a named tuple for the response from `RateLimiter.get_window_stats`

v3.1.5
------
Release Date: 2023-01-12

* Performance

  * Reduce rpc calls to etcd for counter increment

* Compatibility

  * Relax version requirements for packaging dependency

* Chores

  * Improve benchmark outputs
  * Improve documentation for etcd

v3.1.4
------
Release Date: 2023-01-06

* Chores

  * Fix benchmark result artifact capture

v3.1.3
------
Release Date: 2023-01-06

* Chores

  * Fix benchmark result artifact capture

v3.1.2
------
Release Date: 2023-01-06

* Chores

  * Collapse benchmark & ci workflows

v3.1.1
------
Release Date: 2023-01-06

* Chores

  * Fix compatibility tests for etcd in CI
  * Improve visual identifiers of tests
  * Add benchmark tests in CI

v3.1.0
------
Release Date: 2023-01-05

* Compatibility

  * Increase minimum version of pymongo to 4.1

* Chores

  * Refactor storage tests
  * Improve test coverage across python versions in CI

v3.0.0
------
Release Date: 2023-01-04

* Features

  * Added etcd storage support for fixed window strategies

* Compatibility

  * Removed deprecated GAE Memcached storage
  * Updated minimum dependencies for mongodb
  * Updated dependency for async memcached on python 3.11


v2.8.0
------
Release Date: 2022-12-23

* Chores

  * Make rate limit items hashable
  * Update test certificates

v2.7.2
------
Release Date: 2022-12-11

* Compatibility Updates

  * Update documentation dependencies
  * Relax version constraint for packaging dependency
  * Bump CI to use python 3.11 final


v2.7.1
------
Release Date: 2022-10-20

* Compatibility Updates

  * Increase pymemcached dependency range to in include 4.x
  * Add python 3.11 rc2 to CI


v2.7.0
------
Release Date: 2022-07-16

* Compatibility Updates

  * Update :pypi:`coredis` requirements to include 4.x versions
  * Remove CI / support for redis < 6.0
  * Remove python 3.7 from CI
  * Add redis 7.0 in CI

v2.6.3
------
Release Date: 2022-06-05

* Chores

  * Update development dependencies
  * Add CI for python 3.11
  * Increase test coverage for redis sentinel

v2.6.2
------
Release Date: 2022-05-12

* Compatibility Updates

  * Update :pypi:`motor` requirements to include 3.x version
  * Update async redis sentinel implementation to remove use of deprecated methods.
  * Fix compatibility issue with asyncio redis ``reset`` method in cluster mode
    when used with :pypi:`coredis` versions >= 3.5.0

v2.6.1
------
Release Date: 2022-04-25

* Bug Fix

  * Fix typing regression with strategy constructors `Issue 88 <https://github.com/alisaifee/limits/issues/88>`_


v2.6.0
------
Release Date: 2022-04-25

* Deprecation

  * Removed tests for rediscluster using the :pypi:`redis-py-cluster` library

* Bug Fix

  * Fix incorrect ``__slots__`` declaration in :class:`limits.RateLimitItem`
    and it's subclasses (`Issue #121 <https://github.com/alisaifee/limits/issues/121>`__)

v2.5.4
------
Release Date: 2022-04-25

* Bug Fix

  * Fix typing regression with strategy constructors `Issue 88 <https://github.com/alisaifee/limits/issues/88>`_

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






