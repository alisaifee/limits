import threading
from abc import ABCMeta, abstractmethod

import six

from limits.storage.registry import StorageRegistry


@six.add_metaclass(StorageRegistry)
@six.add_metaclass(ABCMeta)
class Storage(object):
    """
    Base class to extend when implementing a storage backend.
    """

    def __init__(self, uri=None, **options):
        self.lock = threading.RLock()

    @abstractmethod
    def incr(self, key, expiry, elastic_expiry=False):
        """
        increments the counter for a given rate limit key

        :param str key: the key to increment
        :param int expiry: amount in seconds for the key to expire in
        :param bool elastic_expiry: whether to keep extending the rate limit
         window every hit.
        """
        raise NotImplementedError

    @abstractmethod
    def get(self, key):
        """
        :param str key: the key to get the counter value for
        """
        raise NotImplementedError

    @abstractmethod
    def get_expiry(self, key):
        """
        :param str key: the key to get the expiry for
        """
        raise NotImplementedError

    @abstractmethod
    def check(self):
        """
        check if storage is healthy
        """
        raise NotImplementedError

    @abstractmethod
    def reset(self):
        """
        reset storage to clear limits
        """
        raise NotImplementedError

    @abstractmethod
    def clear(self, key):
        """
        resets the rate limit key
        :param str key: the key to clear rate limits for
        """
        raise NotImplementedError
