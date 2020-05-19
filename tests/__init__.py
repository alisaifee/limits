import functools
import math
import platform
import sys
import time
import unittest

RUN_GAE = (
    sys.version_info[:2] == (2, 7)
    and platform.python_implementation() == 'CPython'
)


def skip_if_pypy(fn):
    return unittest.skipIf(
        platform.python_implementation().lower() == 'pypy',
        reason='Skipped for pypy'
    )(fn)


def fixed_start(fn):
    @functools.wraps(fn)
    def __inner(*a, **k):
        start = time.time()
        while time.time() < math.ceil(start):
            time.sleep(0.01)
        return fn(*a, **k)
    return __inner
