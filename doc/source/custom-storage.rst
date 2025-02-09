.. currentmodule:: limits

=======================
Custom storage backends
=======================

The **limits** package ships with a few storage implementations which allow you
to get started with some common data stores (Redis & Memcached) used for rate limiting.

To accommodate customizations to either the default storage backends or
different storage backends altogether, **limits** uses a registry pattern that
makes it painless to add your own custom storage (without having to submit patches
to the package itself).

Creating a custom backend requires:

    #. Subclassing :class:`limits.storage.Storage` or :class:`limits.aio.storage.Storage`
       and implementing the abstract methods. This will allow the storage to be used with
       the :ref:`strategies:fixed window` strategies.
    #. If the storage can support the :ref:`strategies:moving window` strategy – additionally implementing
       the methods from :class:`~limits.storage.MovingWindowSupport`
    #. If the storage can support the :ref:`strategies:sliding window counter` strategy – additionally implementing
       the methods from :class:`~limits.storage.SlidingWindowCounterSupport`
    #. Providing naming *schemes* that can be used to look up the custom storage in the storage registry.
       (Refer to :ref:`storage:storage scheme` for more details)

Example
=======

The following example shows two backend stores: one which only supports the :ref:`strategies:fixed window`
strategy and one that implements all strategies. Note the :code:`STORAGE_SCHEME` class
variables which result in the classes getting registered with the **limits** storage registry::

    import time
    from urllib.parse import urlparse
    from typing import Tuple, Type, Union
    from limits.storage import Storage, MovingWindowSupport, SlidingWindowCounterSupport

    class BasicStorage(Storage):
        """A simple fixed-window storage backend."""
        STORAGE_SCHEME = ["basicdb"]

        def __init__(self, uri: str, **options) -> None:
            self.host = urlparse(uri).hostname or ""
            self.port = urlparse(uri).port or 0

        @property
        def base_exceptions(self) -> Union[Type[Exception], Tuple[Type[Exception], ...]]:
            return ()

        def check(self) -> bool:
            return True

        def get_expiry(self, key: str) -> int:
            return int(time.time())

        def incr(self, key: str, expiry: int, elastic_expiry: bool = False, amount: int = 1) -> int:
            return amount

        def get(self, key: str) -> int:
            return 0

        def reset(self) -> int:
            return 0

        def clear(self, key: str) -> None:
            pass

    class AdvancedStorage(Storage, MovingWindowSupport, SlidingWindowCounterSupport):
        """A more advanced storage backend supporting all rate-limiting strategies."""
        STORAGE_SCHEME = ["advanceddatabase"]

        def __init__(self, uri: str, **options) -> None:
            self.host = urlparse(uri).hostname or ""
            self.port = urlparse(uri).port or 0

        @property
        def base_exceptions(self) -> Union[Type[Exception], Tuple[Type[Exception], ...]]:
            return ()

        def check(self) -> bool:
            return True

        def get_expiry(self, key: str) -> int:
            return int(time.time())

        def incr(self, key: str, expiry: int, elastic_expiry: bool = False, amount: int = 1) -> int:
            return amount

        def get(self, key: str) -> int:
            return 0

        def reset(self) -> int:
            return 0

        def clear(self, key: str) -> None:
            pass

        # --- Moving Window Support ---
        def acquire_entry(self, key: str, limit: int, expiry: int, amount: int = 1) -> bool:
            return True

        def get_moving_window(self, key: str, limit: int, expiry: int) -> Tuple[float, int]:
            return (time.time(), 0)

        # --- Sliding Window Counter Support ---
        def acquire_sliding_window_entry(self, key: str, limit: int, expiry: int, amount: int = 1) -> bool:
            return True

        def get_sliding_window(self, key: str, expiry: int) -> Tuple[int, float, int, float]:
            return (0, expiry / 2, 0, expiry)

Once the above implementations are declared, you can look them up
using the :ref:`api:storage factory function` in the following manner::

    from limits.storage import storage_from_string

    basic_store = storage_from_string("basicdb://localhost:42")
    advanced_store = storage_from_string("advanceddatabase://localhost:42")
