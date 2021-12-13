"""

"""
import re
import sys
from typing import Any
from typing import List
from typing import Type

from .limits import RateLimitItem
from .limits import GRANULARITIES

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


def get_dependency(dep) -> Any:
    """
    safe function to import a module programmatically
    """
    try:
        __import__(dep)

        return sys.modules[dep]
    except ImportError:  # pragma: no cover
        return None


def parse_many(limit_string: str) -> List[RateLimitItem]:
    """
    parses rate limits in string notation containing multiple rate limits
    (e.g. '1/second; 5/minute')

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
            limits.append(granularity(int(amount), multiples and int(multiples) or None))

    return limits


def parse(limit_string: str) -> RateLimitItem:
    """
    parses a single rate limit in string notation
    (e.g. '1/second' or '1 per second'

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
