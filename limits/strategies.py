"""
Rate limiting strategies
"""

from __future__ import annotations

import time
from abc import ABCMeta, abstractmethod
from math import floor, inf

from deprecated.sphinx import versionadded

from limits.storage.base import ConcurrencyLimitSupport, SlidingWindowCounterSupport

from .limits import RateLimitItem
from .storage import MovingWindowSupport, Storage, StorageTypes
from .typing import cast
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

        :return: True if ``cost`` could be deducted from the rate limit without exceeding it
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

        :return: True if the rate limit is not depleted
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
                f"of type {storage.__class__}"
            )
        super().__init__(storage)

    def hit(self, item: RateLimitItem, *identifiers: str, cost: int = 1) -> bool:
        """
        Consume the rate limit

        :param item: The rate limit item
        :param identifiers: variable list of strings to uniquely identify this
         instance of the limit
        :param cost: The cost of this hit, default 1

        :return: True if ``cost`` could be deducted from the rate limit without exceeding it
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

        :return: True if the rate limit is not depleted
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

        :return: True if ``cost`` could be deducted from the rate limit without exceeding it
        """

        return (
            self.storage.incr(
                item.key_for(*identifiers),
                item.get_expiry(),
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

        :return: True if the rate limit is not depleted
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
                f"of type {storage.__class__}"
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

        :return: True if ``cost`` could be deducted from the rate limit without exceeding it
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

        :return: True if the rate limit is not depleted
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
        :return: WindowStats(reset time, remaining)
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

        if not (previous_count or current_count):
            return WindowStats(now, remaining)

        expiry = item.get_expiry()

        previous_reset_in, current_reset_in = inf, inf
        if previous_count:
            previous_reset_in = previous_expires_in % (expiry / previous_count)
        if current_count:
            current_reset_in = current_expires_in % expiry

        return WindowStats(now + min(previous_reset_in, current_reset_in), remaining)

    def clear(self, item: RateLimitItem, *identifiers: str) -> None:
        return cast(SlidingWindowCounterSupport, self.storage).clear_sliding_window(
            item.key_for(*identifiers), item.get_expiry()
        )


@versionadded(version="5.9")
class ConcurrencyLimitRateLimiter(RateLimiter):
    """
    Reference: :ref:`strategies:concurrency limit`
    """

    def __init__(self, storage: StorageTypes):
        if not hasattr(storage, "decr"):
            raise NotImplementedError(
                "ConcurrencyLimiting is not implemented for storage "
                f"of type {storage.__class__}"
            )
        super().__init__(storage)

    def hit(self, item: RateLimitItem, *identifiers: str, cost: int = 1) -> bool:
        """
        Acquire ``cost`` concurrency slots if doing so does not exceed the
        limit. Slots are held until :meth:`release` is called (a safety expiry
        of ``item.get_expiry()`` guards against slots leaked by callers that
        never release).

        :param item: The rate limit item
        :param identifiers: variable list of strings to uniquely identify this
         instance of the limit
        :param cost: The number of slots to acquire, default 1

        :return: True if the slots could be acquired without exceeding the limit
        """
        key = item.key_for(*identifiers)

        if self.storage.incr(key, item.get_expiry(), amount=cost) <= item.amount:
            return True
        # Overshot the limit: roll back the slots we just acquired.
        cast(ConcurrencyLimitSupport, self.storage).decr(key, amount=cost)

        return False

    def release(self, item: RateLimitItem, *identifiers: str, cost: int = 1) -> None:
        """
        Release ``cost`` concurrency slots previously acquired with
        :meth:`hit`. The underlying counter is floored at zero.

        :param item: The rate limit item
        :param identifiers: variable list of strings to uniquely identify this
         instance of the limit
        :param cost: The number of slots to release, default 1
        """
        cast(ConcurrencyLimitSupport, self.storage).decr(
            item.key_for(*identifiers), amount=cost
        )

    def test(self, item: RateLimitItem, *identifiers: str, cost: int = 1) -> bool:
        """
        Check whether ``cost`` slots could be acquired without consuming them.

        :param item: The rate limit item
        :param identifiers: variable list of strings to uniquely identify this
         instance of the limit
        :param cost: The number of slots to test for, default 1

        :return: True if there is room for ``cost`` more concurrent slots
        """

        return self.storage.get(item.key_for(*identifiers)) + cost <= item.amount

    def get_window_stats(self, item: RateLimitItem, *identifiers: str) -> WindowStats:
        """
        Query the safety reset time and remaining number of concurrency slots.

        :param item: The rate limit item
        :param identifiers: variable list of strings to uniquely identify this
         instance of the limit
        :return: (reset time, remaining)
        """
        key = item.key_for(*identifiers)
        remaining = max(0, item.amount - self.storage.get(key))
        reset = self.storage.get_expiry(key)

        return WindowStats(reset, remaining)


KnownStrategy = (
    type[SlidingWindowCounterRateLimiter]
    | type[FixedWindowRateLimiter]
    | type[MovingWindowRateLimiter]
    | type[ConcurrencyLimitRateLimiter]
)

STRATEGIES: dict[str, KnownStrategy] = {
    "sliding-window-counter": SlidingWindowCounterRateLimiter,
    "fixed-window": FixedWindowRateLimiter,
    "moving-window": MovingWindowRateLimiter,
    "concurrency-limit": ConcurrencyLimitRateLimiter,
}
