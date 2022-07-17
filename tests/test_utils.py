import pytest
from packaging.version import Version

from limits.errors import ConfigurationError
from limits.util import LazyDependency


def test_lazy_dependency_found():
    class Demo(LazyDependency):
        DEPENDENCIES = ["redis"]

    d = Demo()
    assert d.dependencies["redis"].version_found


def test_lazy_dependency_version_low():
    class Demo(LazyDependency):
        DEPENDENCIES = {
            "redis": Version("999.999"),
            "maythisneverexist": Version("1.0"),
        }

    d = Demo()
    with pytest.raises(
        ConfigurationError,
        match="minimum version of 999.999 of redis could not be found",
    ):
        assert d.dependencies["redis"].version_found
    with pytest.raises(
        ConfigurationError, match="maythisneverexist prerequisite not available"
    ):
        assert d.dependencies["maythisneverexist"].version_found
