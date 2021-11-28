"""
rate limiting strategies
"""

from abc import ABCMeta, abstractmethod
import weakref
from typing import Tuple

from .limits import RateLimitItem
from .storage import Storage


class RateLimiter(metaclass=ABCMeta):
    def __init__(self, storage: Storage):
        self.storage: weakref.ReferenceType[Storage] = weakref.ref(storage)

    @abstractmethod
    def hit(self, item: RateLimitItem, *identifiers) -> bool:
        """
        creates a hit on the rate limit and returns True if successful.

        :param item: a :class:`RateLimitItem` instance
        :param identifiers: variable list of strings to uniquely identify the
         limit
        """
        raise NotImplementedError

    @abstractmethod
    def test(self, item: RateLimitItem, *identifiers) -> bool:
        """
        checks  the rate limit and returns True if it is not
        currently exceeded.

        :param item: The rate limit item
        :param identifiers: variable list of strings to uniquely identify the
         limit
        """
        raise NotImplementedError

    @abstractmethod
    def get_window_stats(self, item: RateLimitItem, *identifiers) -> Tuple[int, int]:
        """
        returns the number of requests remaining and reset of this limit.

        :param item: The rate limit item
        :param identifiers: variable list of strings to uniquely identify the
         limit
        :return: (reset time, remaining)
        """
        raise NotImplementedError

    def clear(self, item: RateLimitItem, *identifiers) -> None:
        return self.storage().clear(item.key_for(*identifiers))


class MovingWindowRateLimiter(RateLimiter):
    """
    Reference: :ref:`moving-window`
    """

    def __init__(self, storage: Storage):
        if not (
            hasattr(storage, "acquire_entry") or hasattr(storage, "get_moving_window")
        ):
            raise NotImplementedError(
                "MovingWindowRateLimiting is not implemented for storage "
                "of type %s" % storage.__class__
            )
        super(MovingWindowRateLimiter, self).__init__(storage)

    def hit(self, item: RateLimitItem, *identifiers) -> bool:
        """
        creates a hit on the rate limit and returns True if successful.

        :param item: The rate limit item
        :param identifiers: variable list of strings to uniquely identify the
         limit
        """

        return self.storage().acquire_entry(  # type: ignore
            item.key_for(*identifiers), item.amount, item.get_expiry()
        )

    def test(self, item: RateLimitItem, *identifiers) -> bool:
        """
        checks  the rate limit and returns True if it is not
        currently exceeded.

        :param item: The rate limit item
        :param identifiers: variable list of strings to uniquely identify the
         limit
        """

        return (
            self.storage().get_moving_window(  # type: ignore
                item.key_for(*identifiers),
                item.amount,
                item.get_expiry(),
            )[1]
            < item.amount
        )

    def get_window_stats(self, item: RateLimitItem, *identifiers) -> Tuple[int, int]:
        """
        returns the number of requests remaining within this limit.

        :param item: The rate limit item
        :param identifiers: variable list of strings to uniquely identify the
         limit
        :return: tuple (reset time, remaining)
        """
        window_start, window_items = self.storage().get_moving_window(  # type: ignore
            item.key_for(*identifiers), item.amount, item.get_expiry()
        )
        reset = window_start + item.get_expiry()

        return (reset, item.amount - window_items)


class FixedWindowRateLimiter(RateLimiter):
    """
    Reference: :ref:`fixed-window`
    """

    def hit(self, item: RateLimitItem, *identifiers) -> bool:
        """
        creates a hit on the rate limit and returns True if successful.

        :param item: The rate limit item
        :param identifiers: variable list of strings to uniquely identify the
         limit
        """

        return (
            self.storage().incr(item.key_for(*identifiers), item.get_expiry())
            <= item.amount
        )

    def test(self, item: RateLimitItem, *identifiers) -> bool:
        """
        checks  the rate limit and returns True if it is not
        currently exceeded.

        :param item: The rate limit item
        :param identifiers: variable list of strings to uniquely identify the
         limit
        """

        return self.storage().get(item.key_for(*identifiers)) < item.amount

    def get_window_stats(self, item: RateLimitItem, *identifiers) -> Tuple[int, int]:
        """
        returns the number of requests remaining and reset of this limit.

        :param item: The rate limit item
        :param identifiers: variable list of strings to uniquely identify the
         limit
        :return: (reset time, remaining)
        """
        remaining = max(0, item.amount - self.storage().get(item.key_for(*identifiers)))
        reset = self.storage().get_expiry(item.key_for(*identifiers))

        return (reset, remaining)


class FixedWindowElasticExpiryRateLimiter(FixedWindowRateLimiter):
    """
    Reference: :ref:`fixed-window-elastic`
    """

    def hit(self, item: RateLimitItem, *identifiers) -> bool:
        """
        creates a hit on the rate limit and returns True if successful.

        :param item: The rate limit item
        :param identifiers: variable list of strings to uniquely identify the
         limit
        """

        return (
            self.storage().incr(item.key_for(*identifiers), item.get_expiry(), True)
            <= item.amount
        )


STRATEGIES = {
    "fixed-window": FixedWindowRateLimiter,
    "fixed-window-elastic-expiry": FixedWindowElasticExpiryRateLimiter,
    "moving-window": MovingWindowRateLimiter,
}
