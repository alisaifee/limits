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

class TokenBucketRateLimiter(RateLimiter):
    """
    Reference: :ref:`strategies:token bucket`
    """

    def hit(self, item: RateLimitItem, *identifiers: str, cost: int = 1) -> bool:
        """
        Consume tokens from the bucket if available.

        :param item: The rate limit item
        :param identifiers: variable list of strings to uniquely identify this
         instance of the limit
        :param cost: The cost of this hit, default 1
        :return: True if the request is allowed, False otherwise
        """
        key = item.key_for(*identifiers)
        tokens, last_refill = self._get_bucket_state(item, key)
        refill_rate = item.amount / item.get_expiry()  # tokens per second
        current_time = self.storage.get_current_time()

        # Refill tokens based on time since the last refill
        time_since_last_refill = current_time - last_refill
        new_tokens = min(item.amount, tokens + time_since_last_refill * refill_rate)

        if new_tokens >= cost:
            # Consume the tokens
            new_tokens -= cost
            self._set_bucket_state(item, key, new_tokens, current_time)
            return True
        else:
            # Not enough tokens, reject the request
            return False

    def test(self, item: RateLimitItem, *identifiers: str, cost: int = 1) -> bool:
        """
        Check if there are enough tokens available without consuming any.

        :param item: The rate limit item
        :param identifiers: variable list of strings to uniquely identify this
         instance of the limit
        :param cost: The expected cost to be consumed, default 1
        :return: True if there are enough tokens, False otherwise
        """
        key = item.key_for(*identifiers)
        tokens, last_refill = self._get_bucket_state(item, key)
        refill_rate = item.amount / item.get_expiry()
        current_time = self.storage.get_current_time()

        # Refill tokens based on time since the last refill
        time_since_last_refill = current_time - last_refill
        new_tokens = min(item.amount, tokens + time_since_last_refill * refill_rate)

        return new_tokens >= cost

    def get_window_stats(self, item: RateLimitItem, *identifiers: str) -> WindowStats:
        """
        Returns the current token count and the next refill time.

        :param item: The rate limit item
        :param identifiers: variable list of strings to uniquely identify this
         instance of the limit
        :return: tuple (next refill time, tokens remaining)
        """
        key = item.key_for(*identifiers)
        tokens, last_refill = self._get_bucket_state(item, key)
        refill_rate = item.amount / item.get_expiry()
        current_time = self.storage.get_current_time()

        time_since_last_refill = current_time - last_refill
        new_tokens = min(item.amount, tokens + time_since_last_refill * refill_rate)
        next_refill = last_refill + (1 / refill_rate if refill_rate > 0 else 0)

        return WindowStats(next_refill, new_tokens)

    def _get_bucket_state(self, item: RateLimitItem, key: str):
        """
        Helper function to get the current state of the token bucket.

        :param item: The rate limit item
        :param key: The key representing the bucket
        :return: A tuple of (current tokens, last refill timestamp)
        """
        stored = self.storage.get(key) or (item.amount, self.storage.get_current_time())
        tokens, last_refill = stored
        return float(tokens), last_refill

    def _set_bucket_state(self, item: RateLimitItem, key: str, tokens: float, timestamp: float):
        """
        Helper function to update the token bucket state.

        :param item: The rate limit item
        :param key: The key representing the bucket
        :param tokens: The number of tokens remaining
        :param timestamp: The last refill timestamp
        """
        self.storage.set(key, (tokens, timestamp), item.get_expiry())

KnownStrategy = Union[
    Type[FixedWindowRateLimiter],
    Type[FixedWindowElasticExpiryRateLimiter],
    Type[MovingWindowRateLimiter],
    Type[TokenBucketRateLimiter],
]

STRATEGIES: Dict[str, KnownStrategy] = {
    "fixed-window": FixedWindowRateLimiter,
    "fixed-window-elastic-expiry": FixedWindowElasticExpiryRateLimiter,
    "moving-window": MovingWindowRateLimiter,
    "token-bucket": TokenBucketRateLimiter,
}
