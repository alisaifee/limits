from functools import wraps
import platform
from nose.plugins.skip import SkipTest

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
