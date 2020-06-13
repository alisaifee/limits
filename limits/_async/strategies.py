"""
Async rate limiting strategies
"""

from abc import ABC, abstractmethod
from typing import Tuple
import weakref

from limits import RateLimitItem
from limits._async.storage import AsyncStorage


class AsyncRateLimiter(ABC):
    def __init__(self, storage: AsyncStorage):
        self.storage = weakref.ref(storage)

    @abstractmethod
    async def hit(self, item: RateLimitItem, *identifiers) -> bool:
        """
        creates a hit on the rate limit and returns True if successful.

        :param item: a :class:`RateLimitItem` instance
        :param identifiers: variable list of strings to uniquely identify the
         limit
        :return: True/False
        """
        raise NotImplementedError

    @abstractmethod
    async def test(self, item: RateLimitItem, *identifiers) -> None:
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
    async def get_window_stats(
        self, item: RateLimitItem, *identifiers
    ) -> Tuple[int, int]:
        """
        returns the number of requests remaining and reset of this limit.

        :param item: a :class:`RateLimitItem` instance
        :param identifiers: variable list of strings to uniquely identify the
         limit
        :return: tuple (reset time (int), remaining (int))
        """
        raise NotImplementedError

    async def clear(self, item: RateLimitItem, *identifiers):
        return await self.storage().clear(item.key_for(*identifiers))


class AsyncMovingWindowRateLimiter(AsyncRateLimiter):
    """
    Reference: :ref:`moving-window`
    """

    def __init__(self, storage: AsyncStorage) -> None:
        if not (
            hasattr(storage, "acquire_entry")
            or hasattr(storage, "get_moving_window")
        ):
            raise NotImplementedError(
                "MovingWindowRateLimiting is not implemented for storage "
                "of type %s" % storage.__class__
            )
        super(AsyncMovingWindowRateLimiter, self).__init__(storage)

    async def hit(self, item: RateLimitItem, *identifiers) -> bool:
        """
        creates a hit on the rate limit and returns True if successful.

        :param item: a :class:`RateLimitItem` instance
        :param identifiers: variable list of strings to uniquely identify the
         limit
        :return: True/False
        """
        return await self.storage().acquire_entry(
            item.key_for(*identifiers), item.amount, item.get_expiry()
        )

    async def test(self, item: RateLimitItem, *identifiers) -> bool:
        """
        checks  the rate limit and returns True if it is not
        currently exceeded.

        :param item: a :class:`RateLimitItem` instance
        :param identifiers: variable list of strings to uniquely identify the
         limit
        :return: True/False
        """
        return (
            await self.storage().get_moving_window(
                item.key_for(*identifiers), item.amount, item.get_expiry(),
            )[1]
            < item.amount
        )

    async def get_window_stats(
        self, item: RateLimitItem, *identifiers
    ) -> Tuple[int, int]:
        """
        returns the number of requests remaining within this limit.

        :param item: a :class:`RateLimitItem` instance
        :param identifiers: variable list of strings to uniquely identify the
         limit
        :return: tuple (reset time (int), remaining (int))
        """
        window_start, window_items = await self.storage().get_moving_window(
            item.key_for(*identifiers), item.amount, item.get_expiry()
        )
        reset = window_start + item.get_expiry()
        return (reset, item.amount - window_items)


class AsyncFixedWindowRateLimiter(AsyncRateLimiter):
    """
    Reference: :ref:`fixed-window`
    """

    async def hit(self, item: RateLimitItem, *identifiers) -> bool:
        """
        creates a hit on the rate limit and returns True if successful.

        :param item: a :class:`RateLimitItem` instance
        :param identifiers: variable list of strings to uniquely identify the
         limit
        :return: True/False
        """
        return await self.storage().incr(
            item.key_for(*identifiers), item.get_expiry()
        ) <= item.amount

    async def test(self, item, *identifiers):
        """
        checks  the rate limit and returns True if it is not
        currently exceeded.

        :param item: a :class:`RateLimitItem` instance
        :param identifiers: variable list of strings to uniquely identify the
         limit
        :return: True/False
        """
        return (
            await self.storage().get(item.key_for(*identifiers)) < item.amount
        )

    async def get_window_stats(self, item, *identifiers) -> Tuple[int, int]:
        """
        returns the number of requests remaining and reset of this limit.

        :param item: a :class:`RateLimitItem` instance
        :param identifiers: variable list of strings to uniquely identify the
         limit
        :return: tuple (reset time (int), remaining (int))
        """
        remaining = max(
            0,
            item.amount - await self.storage().get(item.key_for(*identifiers)),
        )
        reset = await self.storage().get_expiry(item.key_for(*identifiers))
        return (reset, remaining)


class AsyncFixedWindowElasticExpiryRateLimiter(AsyncFixedWindowRateLimiter):
    """
    Reference: :ref:`fixed-window-elastic`
    """

    async def hit(self, item: RateLimitItem, *identifiers) -> bool:
        """
        creates a hit on the rate limit and returns True if successful.

        :param item: a :class:`RateLimitItem` instance
        :param identifiers: variable list of strings to uniquely identify the
         limit
        :return: True/False
        """
        return await self.storage().incr(
            item.key_for(*identifiers), item.get_expiry(), True
        ) <= item.amount


STRATEGIES = {
    "fixed-window": AsyncFixedWindowRateLimiter,
    "fixed-window-elastic-expiry": AsyncFixedWindowElasticExpiryRateLimiter,
    "moving-window": AsyncMovingWindowRateLimiter,
}
