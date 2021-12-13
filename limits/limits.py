"""

"""
from __future__ import annotations
from functools import total_ordering
from typing import cast, Dict, Optional, Tuple, Type, Union


def safe_string(value: Union[bytes, str, int]) -> str:
    """
    converts a byte/str or int to a str
    """

    if isinstance(value, bytes):
        return value.decode()

    return str(value)


TIME_TYPES = dict(
    day=(60 * 60 * 24, "day"),
    month=(60 * 60 * 24 * 30, "month"),
    year=(60 * 60 * 24 * 30 * 12, "year"),
    hour=(60 * 60, "hour"),
    minute=(60, "minute"),
    second=(1, "second"),
)

GRANULARITIES: Dict[str, Type[RateLimitItem]] = {}


class RateLimitItemMeta(type):
    def __new__(cls, name, parents, dct):
        granularity = super(RateLimitItemMeta, cls).__new__(cls, name, parents, dct)

        if "granularity" in dct:
            GRANULARITIES[dct["granularity"][1]] = cast(
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
    :param multiples: multiple of the 'per' granularity
     (e.g. 'n' per 'm' seconds)
    :param namespace: category for the specific rate limit
    """

    __slots__ = ["namespace", "amount", "multiples", "granularity"]

    def __init__(self, amount: int, multiples: Optional[int] = 1, namespace: str = "LIMITER"):
        self.namespace = namespace
        self.amount = int(amount)
        self.multiples = int(multiples or 1)
        self.granularity: Tuple[int, str]

    @classmethod
    def check_granularity_string(cls, granularity_string: str) -> bool:
        """
        checks if this instance matches a granularity string
        of type 'n per hour' etc.
        """

        return granularity_string.lower() in cls.granularity[1:]

    def get_expiry(self) -> int:
        """
        :return: the size of the window in seconds.
        """

        return self.granularity[0] * self.multiples

    def key_for(self, *identifiers) -> str:
        """
        :param identifiers: a list of strings to append to the key
        :return: a string key identifying this resource with
         each identifier appended with a '/' delimiter.
        """
        remainder = "/".join(
            [safe_string(k) for k in identifiers]
            + [
                safe_string(self.amount),
                safe_string(self.multiples),
                self.granularity[1],
            ]
        )

        return "%s/%s" % (self.namespace, remainder)

    def __eq__(self, other):
        return self.amount == other.amount and self.granularity == other.granularity

    def __repr__(self):
        return "%d per %d %s" % (self.amount, self.multiples, self.granularity[1])

    def __lt__(self, other):
        return self.granularity[0] < other.granularity[0]


class RateLimitItemPerYear(RateLimitItem):
    """
    per year rate limited resource.
    """

    granularity = TIME_TYPES["year"]


class RateLimitItemPerMonth(RateLimitItem):
    """
    per month rate limited resource.
    """

    granularity = TIME_TYPES["month"]


class RateLimitItemPerDay(RateLimitItem):
    """
    per day rate limited resource.
    """

    granularity = TIME_TYPES["day"]


class RateLimitItemPerHour(RateLimitItem):
    """
    per hour rate limited resource.
    """

    granularity = TIME_TYPES["hour"]


class RateLimitItemPerMinute(RateLimitItem):
    """
    per minute rate limited resource.
    """

    granularity = TIME_TYPES["minute"]


class RateLimitItemPerSecond(RateLimitItem):
    """
    per second rate limited resource.
    """

    granularity = TIME_TYPES["second"]
