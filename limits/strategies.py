"""
Rate limiting strategies
"""

import time
from abc import ABCMeta, abstractmethod
from math import floor
from typing import Dict, Type, Union, cast

from deprecated.sphinx import versionadded

from limits.storage.base import SlidingWindowCounterSupport

from .limits import RateLimitItem
from .storage import MovingWindowSupport, Storage, StorageTypes
from .util import WindowStats


class RateLimiter(metaclass=ABCMeta):
    def __init__(self, storage: StorageTypes):
        assert isinstance(storage, Storage)
        self.storage: Storage = storage

    @abstractmethod
    def hit(self, item: RateLimitItem, *identifiers: str, cost: int = 1) -> bool:
        """
        Consume the rate limit

        :param item: The rate limit item
        :param identifiers: variable list of strings to uniquely identify this
         instance of the limit
        :param cost: The cost of this hit, default 1
        """
        raise NotImplementedError

    @abstractmethod
    def test(self, item: RateLimitItem, *identifiers: str, cost: int = 1) -> bool:
        """
        Check the rate limit without consuming from it.

        :param item: The rate limit item
        :param identifiers: variable list of strings to uniquely identify this
          instance of the limit
        :param cost: The expected cost to be consumed, default 1
        """
        raise NotImplementedError

    @abstractmethod
    def get_window_stats(self, item: RateLimitItem, *identifiers: str) -> WindowStats:
        """
        Query the reset time and remaining amount for the limit

        :param item: The rate limit item
        :param identifiers: variable list of strings to uniquely identify this
         instance of the limit
        :return: (reset time, remaining)
        """
        raise NotImplementedError

    def clear(self, item: RateLimitItem, *identifiers: str) -> None:
        return self.storage.clear(item.key_for(*identifiers))


class MovingWindowRateLimiter(RateLimiter):
    """
    Reference: :ref:`strategies:moving window`
    """

    def __init__(self, storage: StorageTypes):
        if not (
            hasattr(storage, "acquire_entry") or hasattr(storage, "get_moving_window")
        ):
            raise NotImplementedError(
                "MovingWindowRateLimiting is not implemented for storage "
                "of type %s" % storage.__class__
            )
        super().__init__(storage)

    def hit(self, item: RateLimitItem, *identifiers: str, cost: int = 1) -> bool:
        """
        Consume the rate limit

        :param item: The rate limit item
        :param identifiers: variable list of strings to uniquely identify this
         instance of the limit
        :param cost: The cost of this hit, default 1
        :return: (reset time, remaining)
        """

        return cast(MovingWindowSupport, self.storage).acquire_entry(
            item.key_for(*identifiers), item.amount, item.get_expiry(), amount=cost
        )

    def test(self, item: RateLimitItem, *identifiers: str, cost: int = 1) -> bool:
        """
        Check if the rate limit can be consumed

        :param item: The rate limit item
        :param identifiers: variable list of strings to uniquely identify this
         instance of the limit
        :param cost: The expected cost to be consumed, default 1
        """

        return (
            cast(MovingWindowSupport, self.storage).get_moving_window(
                item.key_for(*identifiers),
                item.amount,
                item.get_expiry(),
            )[1]
            <= item.amount - cost
        )

    def get_window_stats(self, item: RateLimitItem, *identifiers: str) -> WindowStats:
        """
        returns the number of requests remaining within this limit.

        :param item: The rate limit item
        :param identifiers: variable list of strings to uniquely identify this
         instance of the limit
        :return: tuple (reset time, remaining)
        """
        window_start, window_items = cast(
            MovingWindowSupport, self.storage
        ).get_moving_window(item.key_for(*identifiers), item.amount, item.get_expiry())
        reset = window_start + item.get_expiry()

        return WindowStats(reset, item.amount - window_items)


class FixedWindowRateLimiter(RateLimiter):
    """
    Reference: :ref:`strategies:fixed window`
    """

    def hit(self, item: RateLimitItem, *identifiers: str, cost: int = 1) -> bool:
        """
        Consume the rate limit

        :param item: The rate limit item
        :param identifiers: variable list of strings to uniquely identify this
         instance of the limit
        :param cost: The cost of this hit, default 1
        """

        return (
            self.storage.incr(
                item.key_for(*identifiers),
                item.get_expiry(),
                elastic_expiry=False,
                amount=cost,
            )
            <= item.amount
        )

    def test(self, item: RateLimitItem, *identifiers: str, cost: int = 1) -> bool:
        """
        Check if the rate limit can be consumed

        :param item: The rate limit item
        :param identifiers: variable list of strings to uniquely identify this
         instance of the limit
        :param cost: The expected cost to be consumed, default 1
        """

        return self.storage.get(item.key_for(*identifiers)) < item.amount - cost + 1

    def get_window_stats(self, item: RateLimitItem, *identifiers: str) -> WindowStats:
        """
        Query the reset time and remaining amount for the limit

        :param item: The rate limit item
        :param identifiers: variable list of strings to uniquely identify this
         instance of the limit
        :return: (reset time, remaining)
        """
        remaining = max(0, item.amount - self.storage.get(item.key_for(*identifiers)))
        reset = self.storage.get_expiry(item.key_for(*identifiers))

        return WindowStats(reset, remaining)


@versionadded(version="4.1")
class SlidingWindowCounterRateLimiter(RateLimiter):
    """
    Reference: :ref:`strategies:sliding window counter`
    """

    def __init__(self, storage: StorageTypes):
        if not hasattr(storage, "get_sliding_window") or not hasattr(
            storage, "acquire_sliding_window_entry"
        ):
            raise NotImplementedError(
                "SlidingWindowCounterRateLimiting is not implemented for storage "
                "of type %s" % storage.__class__
            )
        super().__init__(storage)

    def _weighted_count(
        self,
        item: RateLimitItem,
        previous_count: int,
        previous_expires_in: float,
        current_count: int,
    ) -> float:
        """
        Return the approximated by weighting the previous window count and adding the current window count.
        """
        return previous_count * previous_expires_in / item.get_expiry() + current_count

    def hit(self, item: RateLimitItem, *identifiers: str, cost: int = 1) -> bool:
        """
        Consume the rate limit

        :param item: The rate limit item
        :param identifiers: variable list of strings to uniquely identify this
         instance of the limit
        :param cost: The cost of this hit, default 1
        """
        return cast(
            SlidingWindowCounterSupport, self.storage
        ).acquire_sliding_window_entry(
            item.key_for(*identifiers),
            item.amount,
            item.get_expiry(),
            cost,
        )

    def test(self, item: RateLimitItem, *identifiers: str, cost: int = 1) -> bool:
        """
        Check if the rate limit can be consumed

        :param item: The rate limit item
        :param identifiers: variable list of strings to uniquely identify this
         instance of the limit
        :param cost: The expected cost to be consumed, default 1
        """
        previous_count, previous_expires_in, current_count, _ = cast(
            SlidingWindowCounterSupport, self.storage
        ).get_sliding_window(item.key_for(*identifiers), item.get_expiry())

        return (
            self._weighted_count(
                item, previous_count, previous_expires_in, current_count
            )
            < item.amount - cost + 1
        )

    def get_window_stats(self, item: RateLimitItem, *identifiers: str) -> WindowStats:
        """
        Query the reset time and remaining amount for the limit.

        :param item: The rate limit item
        :param identifiers: variable list of strings to uniquely identify this
         instance of the limit
        :return: (reset time, remaining)
        """
        previous_count, previous_expires_in, current_count, current_expires_in = cast(
            SlidingWindowCounterSupport, self.storage
        ).get_sliding_window(item.key_for(*identifiers), item.get_expiry())
        remaining = max(
            0,
            item.amount
            - floor(
                self._weighted_count(
                    item, previous_count, previous_expires_in, current_count
                )
            ),
        )
        now = time.time()
        if previous_count >= 1 and current_count == 0:
            previous_window_reset_period = item.get_expiry() / previous_count
            reset = previous_expires_in % previous_window_reset_period + now
        elif previous_count >= 1 and current_count >= 1:
            previous_window_reset_period = item.get_expiry() / previous_count
            previous_reset = previous_expires_in % previous_window_reset_period + now
            current_reset = current_expires_in % item.get_expiry() + now
            reset = min(previous_reset, current_reset)
        elif previous_count == 0 and current_count >= 1:
            reset = current_expires_in % item.get_expiry() + now
        else:
            reset = now

        return WindowStats(reset, remaining)


class FixedWindowElasticExpiryRateLimiter(FixedWindowRateLimiter):
    """
    Reference: :ref:`strategies:fixed window with elastic expiry`
    """

    def hit(self, item: RateLimitItem, *identifiers: str, cost: int = 1) -> bool:
        """
        Consume the rate limit

        :param item: The rate limit item
        :param identifiers: variable list of strings to uniquely identify this
         instance of the limit
        :param cost: The cost of this hit, default 1
        """

        return (
            self.storage.incr(
                item.key_for(*identifiers),
                item.get_expiry(),
                elastic_expiry=True,
                amount=cost,
            )
            <= item.amount
        )


KnownStrategy = Union[
    Type[SlidingWindowCounterRateLimiter],
    Type[FixedWindowRateLimiter],
    Type[FixedWindowElasticExpiryRateLimiter],
    Type[MovingWindowRateLimiter],
]

STRATEGIES: Dict[str, KnownStrategy] = {
    "sliding-window-counter": SlidingWindowCounterRateLimiter,
    "fixed-window": FixedWindowRateLimiter,
    "fixed-window-elastic-expiry": FixedWindowElasticExpiryRateLimiter,
    "moving-window": MovingWindowRateLimiter,
}
