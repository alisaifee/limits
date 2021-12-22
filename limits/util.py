"""

"""
import re
import sys
from typing import Any, Dict, List, Type

import pkg_resources

from .errors import ConfigurationError
from .limits import GRANULARITIES, RateLimitItem

SEPARATORS = re.compile(r"[,;|]{1}")
SINGLE_EXPR = re.compile(
    r"""
    \s*([0-9]+)
    \s*(/|\s*per\s*)
    \s*([0-9]+)
    *\s*(hour|minute|second|day|month|year)s?\s*""",
    re.IGNORECASE | re.VERBOSE,
)
EXPR = re.compile(
    r"^{SINGLE}(:?{SEPARATORS}{SINGLE})*$".format(
        SINGLE=SINGLE_EXPR.pattern, SEPARATORS=SEPARATORS.pattern
    ),
    re.IGNORECASE | re.VERBOSE,
)


class LazyDependency:
    """
    Simple utility that provides an :attr:`dependency`
    to the child class to fetch any dependencies
    without having to import them explicitly.
    """

    DEPENDENCIES: List[str] = []
    """
    The python modules this class has a dependency on.
    Used to lazily populate the :attr:`dependencies`
    """

    def __init__(self):
        self._dependencies = {}

    @property
    def dependencies(self) -> Dict[str, Any]:
        """
        Cached mapping of the modules this storage depends on. This is done so that the module
        is only imported lazily when the storage is instantiated.
        """
        if not getattr(self, "_dependencies", {}):
            dependencies = {}
            for name in self.DEPENDENCIES:
                dependency = get_dependency(name)

                if not dependency:
                    raise ConfigurationError(
                        f"{name} prerequisite not available"
                    )  # pragma: no cover
                dependencies[name] = dependency
            self._dependencies = dependencies
        return self._dependencies


def get_dependency(dep) -> Any:
    """
    safe function to import a module at runtime
    """
    try:
        if dep not in sys.modules:
            __import__(dep)

        return sys.modules[dep]
    except ImportError:  # pragma: no cover
        return None


def get_package_data(path: str) -> bytes:
    return pkg_resources.resource_string(__name__, path)


def parse_many(limit_string: str) -> List[RateLimitItem]:
    """
    parses rate limits in string notation containing multiple rate limits
    (e.g. ``1/second; 5/minute``)

    :param limit_string: rate limit string using :ref:`ratelimit-string`
    :raise ValueError: if the string notation is invalid.

    """

    if not (isinstance(limit_string, str) and EXPR.match(limit_string)):
        raise ValueError("couldn't parse rate limit string '%s'" % limit_string)
    limits = []

    for limit in SEPARATORS.split(limit_string):
        match = SINGLE_EXPR.match(limit)

        if match:
            amount, _, multiples, granularity_string = match.groups()
            granularity = granularity_from_string(granularity_string)
            limits.append(
                granularity(int(amount), multiples and int(multiples) or None)
            )

    return limits


def parse(limit_string: str) -> RateLimitItem:
    """
    parses a single rate limit in string notation
    (e.g. ``1/second`` or ``1 per second``)

    :param limit_string: rate limit string using :ref:`ratelimit-string`
    :raise ValueError: if the string notation is invalid.

    """

    return list(parse_many(limit_string))[0]


def granularity_from_string(granularity_string) -> Type[RateLimitItem]:
    """

    :param granularity_string:
    :raise ValueError:
    """

    for granularity in GRANULARITIES.values():
        if granularity.check_granularity_string(granularity_string):
            return granularity
    raise ValueError("no granularity matched for %s" % granularity_string)
