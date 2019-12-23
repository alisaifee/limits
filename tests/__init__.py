import platform
import sys
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


