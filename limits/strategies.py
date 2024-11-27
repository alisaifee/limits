"""
Rate limiting strategies
"""

from abc import ABCMeta, abstractmethod
from typing import Dict, Type, Union, cast

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

class ConcurrencyLimitRateLimiter(RateLimiter):
    """
    Reference: :ref:`strategies:concurrency limit`
    """

    def hit(self, item: RateLimitItem, *identifiers: str, cost: int = 1) -> bool:
        """
        Attempt to consume tokens if the concurrency limit has not been reached.
        
        :param item: The rate limit item
        :param identifiers: variable list of strings to uniquely identify this
         instance of the limit
        :param cost: The cost of this hit, default 1
        :return: True if the request is allowed (tokens consumed), False otherwise
        """
        key = item.key_for(*identifiers)
        current_concurrency = self._get_concurrency(key)

        # If current concurrency is less than the allowed limit, proceed
        if current_concurrency + cost <= item.amount:
            # Increment the concurrency count
            self.storage.incr(key, item.get_expiry(), amount=cost)
            return True
        else:
            # Limit reached, reject the request
            return False

    def release(self, item: RateLimitItem, *identifiers: str, cost: int = 1) -> None:
        """
        Release tokens (i.e., reduce concurrency) when a task/request is finished.

        :param item: The rate limit item
        :param identifiers: variable list of strings to uniquely identify this
         instance of the limit
        :param cost: The cost to release, default 1
        """
        key = item.key_for(*identifiers)
        current_concurrency = self._get_concurrency(key)

        # Decrement the concurrency count
        new_concurrency = max(0, current_concurrency - cost)
        self.storage.set(key, new_concurrency, item.get_expiry())

    def test(self, item: RateLimitItem, *identifiers: str, cost: int = 1) -> bool:
        """
        Check if there is room for more concurrent tasks without consuming tokens.

        :param item: The rate limit item
        :param identifiers: variable list of strings to uniquely identify this
         instance of the limit
        :param cost: The expected cost to be consumed, default 1
        :return: True if there is room for more concurrent tasks, False otherwise
        """
        key = item.key_for(*identifiers)
        current_concurrency = self._get_concurrency(key)

        return current_concurrency + cost <= item.amount

    def get_window_stats(self, item: RateLimitItem, *identifiers: str) -> WindowStats:
        """
        Returns the current concurrency level and remaining capacity.

        :param item: The rate limit item
        :param identifiers: variable list of strings to uniquely identify this
         instance of the limit
        :return: tuple (reset time, remaining capacity)
        """
        key = item.key_for(*identifiers)
        current_concurrency = self._get_concurrency(key)

        remaining_capacity = max(0, item.amount - current_concurrency)
        reset_time = self.storage.get_expiry(key)

        return WindowStats(reset_time, remaining_capacity)

    def _get_concurrency(self, key: str) -> int:
        """
        Helper function to retrieve the current number of concurrent tasks.

        :param key: The key representing the concurrency state
        :return: The current concurrency level
        """
        return self.storage.get(key) or 0

KnownStrategy = Union[
    Type[FixedWindowRateLimiter],
    Type[FixedWindowElasticExpiryRateLimiter],
    Type[MovingWindowRateLimiter],
    Type[ConcurrencyLimitRateLimiter],
]

STRATEGIES: Dict[str, KnownStrategy] = {
    "fixed-window": FixedWindowRateLimiter,
    "fixed-window-elastic-expiry": FixedWindowElasticExpiryRateLimiter,
    "moving-window": MovingWindowRateLimiter,
    "concurrency-limit": ConcurrencyLimitRateLimiter,
}
