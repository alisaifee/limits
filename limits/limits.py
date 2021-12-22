"""

"""
from __future__ import annotations

from functools import total_ordering
from typing import Dict, NamedTuple, Optional, Type, Union, cast


def safe_string(value: Union[bytes, str, int]) -> str:
    """
    converts a byte/str or int to a str
    """

    if isinstance(value, bytes):
        return value.decode()

    return str(value)


class Granularity(NamedTuple):
    seconds: int
    name: str


TIME_TYPES = dict(
    day=Granularity(60 * 60 * 24, "day"),
    month=Granularity(60 * 60 * 24 * 30, "month"),
    year=Granularity(60 * 60 * 24 * 30 * 12, "year"),
    hour=Granularity(60 * 60, "hour"),
    minute=Granularity(60, "minute"),
    second=Granularity(1, "second"),
)

GRANULARITIES: Dict[str, Type[RateLimitItem]] = {}


class RateLimitItemMeta(type):
    def __new__(cls, name, parents, dct):
        granularity = super(RateLimitItemMeta, cls).__new__(cls, name, parents, dct)

        if "GRANULARITY" in dct:
            GRANULARITIES[dct["GRANULARITY"][1]] = cast(
                Type[RateLimitItem], granularity
            )

        return granularity


# pylint: disable=no-member
@total_ordering
class RateLimitItem(metaclass=RateLimitItemMeta):
    """
    defines a Rate limited resource which contains the characteristic
    namespace, amount and granularity multiples of the rate limiting window.

    :param amount: the rate limit amount
    :param multiples: multiple of the 'per' :attr:`GRANULARITY`
     (e.g. 'n' per 'm' seconds)
    :param namespace: category for the specific rate limit
    """

    __slots__ = ["namespace", "amount", "multiples", "granularity"]

    GRANULARITY: Granularity
    """
    A tuple describing the granularity of this limit as
    (number of seconds, name)
    """

    def __init__(
        self, amount: int, multiples: Optional[int] = 1, namespace: str = "LIMITER"
    ):
        self.namespace = namespace
        self.amount = int(amount)
        self.multiples = int(multiples or 1)

    @classmethod
    def check_granularity_string(cls, granularity_string: str) -> bool:
        """
        Checks if this instance matches a *granularity_string*
        of type ``n per hour``, ``n per minute`` etc,
        by comparing with :attr:`GRANULARITY`

        """

        return granularity_string.lower() in cls.GRANULARITY.name

    def get_expiry(self) -> int:
        """
        :return: the duration the limit is enforced for in seconds.
        """

        return self.GRANULARITY.seconds * self.multiples

    def key_for(self, *identifiers) -> str:
        """
        Constructs a key for the current limit and any additional
        identifiers provided.

        :param identifiers: a list of strings to append to the key
        :return: a string key identifying this resource with
         each identifier appended with a '/' delimiter.
        """
        remainder = "/".join(
            [safe_string(k) for k in identifiers]
            + [
                safe_string(self.amount),
                safe_string(self.multiples),
                self.GRANULARITY.name,
            ]
        )

        return "%s/%s" % (self.namespace, remainder)

    def __eq__(self, other):
        return self.amount == other.amount and self.GRANULARITY == other.GRANULARITY

    def __repr__(self):
        return "%d per %d %s" % (self.amount, self.multiples, self.GRANULARITY.name)

    def __lt__(self, other):
        return self.GRANULARITY.seconds < other.GRANULARITY.seconds


class RateLimitItemPerYear(RateLimitItem):
    """
    per year rate limited resource.
    """

    GRANULARITY = TIME_TYPES["year"]
    """A year"""


class RateLimitItemPerMonth(RateLimitItem):
    """
    per month rate limited resource.
    """

    GRANULARITY = TIME_TYPES["month"]
    """A month"""


class RateLimitItemPerDay(RateLimitItem):
    """
    per day rate limited resource.
    """

    GRANULARITY = TIME_TYPES["day"]
    """A day"""


class RateLimitItemPerHour(RateLimitItem):
    """
    per hour rate limited resource.
    """

    GRANULARITY = TIME_TYPES["hour"]
    """An hour"""


class RateLimitItemPerMinute(RateLimitItem):
    """
    per minute rate limited resource.
    """

    GRANULARITY = TIME_TYPES["minute"]
    """A minute"""


class RateLimitItemPerSecond(RateLimitItem):
    """
    per second rate limited resource.
    """

    GRANULARITY = TIME_TYPES["second"]
    """A second"""
