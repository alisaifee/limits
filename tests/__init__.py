from functools import wraps
import platform
import unittest

import sys
from nose.plugins.skip import SkipTest

RUN_GAE = (
    sys.version_info[:2] == (2, 7)
    and platform.python_implementation() == 'CPython'
)


def test_import():
    import limits


def test_module_version():
    import limits
    assert limits.__version__ is not None


def skip_if(cond):
    def _inner(fn):
        @wraps(fn)
        def __inner(*a, **k):
            if cond() if callable(cond) else cond:
                raise SkipTest
            return fn(*a, **k)

        return __inner

    return _inner


def skip_if_pypy(fn):
    return skip_if(platform.python_implementation().lower() == 'pypy')(fn)
