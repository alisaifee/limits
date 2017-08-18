from functools import wraps
import platform
import unittest

import sys
from nose.plugins.skip import SkipTest
import pymemcache.client
import redis
import redis.sentinel
import rediscluster


def test_import():
    import limits

def test_module_version():
    import limits
    assert limits.__version__ is not None


def skip_if(cond, fn):
    @wraps(fn)
    def __inner(*a, **k):
        if cond() if callable(cond) else cond:
            raise SkipTest
        return fn(*a, **k)
    return __inner


def skip_if_pypy(fn):
    return skip_if(platform.python_implementation().lower() == 'pypy', fn)


PY3 = sys.version_info >= (3,)


def skip_if_py3(fn):
    return skip_if(PY3, fn)


class StorageTests(unittest.TestCase):
    def setUp(self):
        pymemcache.client.Client(('localhost', 11211)).flush_all()
        redis.Redis().flushall()
        redis.sentinel.Sentinel([("localhost", 26379)]).master_for(
            "localhost-redis-sentinel"
        ).flushall()
        rediscluster.RedisCluster("localhost", 7000).flushall()
        if not PY3:
            from google.appengine.ext import testbed
            tb = testbed.Testbed()
            tb.activate()
            tb.init_memcache_stub()
