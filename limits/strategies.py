"""
rate limiting strategies
"""

from abc import ABCMeta, abstractmethod
import weakref
import six
import time


@six.add_metaclass(ABCMeta)
class RateLimiter(object):
    def __init__(self, storage):
        self.storage = weakref.ref(storage)

    @abstractmethod
    def hit(self, item, *identifiers):
        """
        creates a hit on the rate limit and returns True if successful.

        :param item: a :class:`RateLimitItem` instance
        :param identifiers: variable list of strings to uniquely identify the
         limit
        :return: True/False
        """
        raise NotImplementedError

    @abstractmethod
    def test(self, item, *identifiers):
        """
        checks  the rate limit and returns True if it is not
        currently exceeded.

        :param item: a :class:`RateLimitItem` instance
        :param identifiers: variable list of strings to uniquely identify the
         limit
        :return: True/False
        """
        raise NotImplementedError

    @abstractmethod
    def get_window_stats(self, item, *identifiers):
        """
        returns the number of requests remaining and reset of this limit.

        :param item: a :class:`RateLimitItem` instance
        :param identifiers: variable list of strings to uniquely identify the
         limit
        :return: tuple (reset time (int), remaining (int))
        """
        raise NotImplementedError


class MovingWindowRateLimiter(RateLimiter):
    """
    Reference: :ref:`moving-window`
    """

    def __init__(self, storage):
        if not (
            hasattr(storage, "acquire_entry")
            or hasattr(storage, "get_moving_window")
        ):
            raise NotImplementedError(
                "MovingWindowRateLimiting is not implemented for storage of type %s"
                % storage.__class__
            )
        super(MovingWindowRateLimiter, self).__init__(storage)

    def hit(self, item, *identifiers):
        """
        creates a hit on the rate limit and returns True if successful.

        :param item: a :class:`RateLimitItem` instance
        :param identifiers: variable list of strings to uniquely identify the
         limit
        :return: True/False
        """
        return self.storage().acquire_entry(
            item.key_for(*identifiers), item.amount, item.get_expiry()
        )

    def test(self, item, *identifiers):
        """
        checks  the rate limit and returns True if it is not
        currently exceeded.

        :param item: a :class:`RateLimitItem` instance
        :param identifiers: variable list of strings to uniquely identify the
         limit
        :return: True/False
        """
        return self.storage().get_moving_window(
            item.key_for(*identifiers),
            item.amount,
            item.get_expiry(),
        )[1] < item.amount

    def get_window_stats(self, item, *identifiers):
        """
        returns the number of requests remaining within this limit.

        :param item: a :class:`RateLimitItem` instance
        :param identifiers: variable list of strings to uniquely identify the
         limit
        :return: tuple (reset time (int), remaining (int))
        """
        window_start, window_items = self.storage().get_moving_window(
            item.key_for(*identifiers), item.amount, item.get_expiry()
        )
        reset = window_start + item.get_expiry()
        return (reset, item.amount - window_items)


class FixedWindowRateLimiter(RateLimiter):
    """
    Reference: :ref:`fixed-window`
    """

    def hit(self, item, *identifiers):
        """
        creates a hit on the rate limit and returns True if successful.

        :param item: a :class:`RateLimitItem` instance
        :param identifiers: variable list of strings to uniquely identify the
         limit
        :return: True/False
        """
        return (
            self.storage().incr(item.key_for(*identifiers), item.get_expiry())
            <= item.amount
        )

    def test(self, item, *identifiers):
        """
        checks  the rate limit and returns True if it is not
        currently exceeded.

        :param item: a :class:`RateLimitItem` instance
        :param identifiers: variable list of strings to uniquely identify the
         limit
        :return: True/False
        """
        return self.storage().get(item.key_for(*identifiers)) < item.amount

    def get_window_stats(self, item, *identifiers):
        """
        returns the number of requests remaining and reset of this limit.

        :param item: a :class:`RateLimitItem` instance
        :param identifiers: variable list of strings to uniquely identify the
         limit
        :return: tuple (reset time (int), remaining (int))
        """
        remaining = max(
            0, item.amount - self.storage().get(item.key_for(*identifiers))
        )
        reset = self.storage().get_expiry(item.key_for(*identifiers))
        return (reset, remaining)


class FixedWindowElasticExpiryRateLimiter(FixedWindowRateLimiter):
    """
    Reference: :ref:`fixed-window-elastic`
    """

    def hit(self, item, *identifiers):
        """
        creates a hit on the rate limit and returns True if successful.

        :param item: a :class:`RateLimitItem` instance
        :param identifiers: variable list of strings to uniquely identify the
         limit
        :return: True/False
        """
        return (
            self.storage().incr(
                item.key_for(*identifiers), item.get_expiry(), True
            ) <= item.amount
        )
    
 
class TokenBucketRateLimiter(RateLimiter):
    """
    Reference: :ref:`token-bucket`
    """

    def __init__(self, storage):
        if not (
            hasattr(storage, "acquire_token")
            or hasattr(storage, "get_window_stats")
        ):
            raise NotImplementedError(
                "TokenBucketRateLimiter is not implemented for storage of type %s"
                % storage.__class__
            )
        super(TokenBucketRateLimiter, self).__init__(storage)

    def hit(self, item, *identifiers):
        """
        creates a hit on the rate limit and returns True if successful.
        :param item: a :class:`RateLimitItem` instance
        :param identifiers: variable list of strings to uniquely identify the
         limit
        :return: True/False
        """
        max_tokens = item.amount
        max_interval = item.get_expiry() * 1000
        init_tokens = int(max_tokens / 3) + 1
        interval_per_token = int(max_interval / max_tokens)
        return bool(
            self.storage().acquire_token(
                item.key_for(*identifiers),
                int(time.time() * 1000),
                interval_per_token,
                max_tokens,
                init_tokens,
                max_interval
            )
        )

    def test(self, item, *identifiers):
        """
        checks  the rate limit and returns True if it is not
        currently exceeded.
        :param item: a :class:`RateLimitItem` instance
        :param identifiers: variable list of strings to uniquely identify the
         limit
        :return: True/False
        """
        bucket = self.get_window_stats(item, *identifiers)
        tokens = bucket[1]
        return tokens > 0

    def get_window_stats(self, item, *identifiers):
        """
        returns the number of requests remaining and reset of this limit.
        :param item: a :class:`RateLimitItem` instance
        :param identifiers: variable list of strings to uniquely identify the
         limit
        :return: tuple (last refill time (int), remaining token (int))
        """
        max_tokens = item.amount
        max_interval = item.get_expiry() * 1000
        init_tokens = int(max_tokens / 3) + 1
        interval_per_token = int(max_interval / max_tokens)
        return self.storage().get_token_bucket(
                item.key_for(*identifiers),
                int(time.time() * 1000),
                interval_per_token,
                max_tokens,
                init_tokens,
                max_interval
            )


STRATEGIES = {
    "fixed-window": FixedWindowRateLimiter,
    "fixed-window-elastic-expiry": FixedWindowElasticExpiryRateLimiter,
    "moving-window": MovingWindowRateLimiter,
    "token-bucket": TokenBucketRateLimiter,
}
