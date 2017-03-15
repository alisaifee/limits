from functools import wraps
import platform
import unittest

from google.appengine.ext import testbed
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


def skip_if_pypy(fn):
    @wraps(fn)
    def __inner(*a, **k):
        if platform.python_implementation().lower() == "pypy":
            raise SkipTest
        return fn(*a, **k)
    return __inner


class StorageTests(unittest.TestCase):
    def setUp(self):
        pymemcache.client.Client(('localhost', 11211)).flush_all()
        redis.Redis().flushall()
        redis.sentinel.Sentinel([("localhost", 26379)]).master_for(
            "localhost-redis-sentinel"
        ).flushall()
        rediscluster.RedisCluster("localhost", 7000).flushall()
        tb = testbed.Testbed()
        tb.activate()
        tb.init_memcache_stub()
