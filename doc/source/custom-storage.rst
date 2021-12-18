.. currentmodule:: limits

=======================
Custom storage backends
=======================

The **limits** package ships with a few storage implementations which allow you
to get started with some common data stores (redis & memcached) used for rate limiting.

To accommodate customizations to either the default storage backends or
different storage backends altogether, **limits** uses a registry pattern that
makes it painless to add your own custom storage (without having to submit patches
to the package itself).

Creating a custom backend requires:

    #. Subclassing :class:`limits.storage.Storage` or :class:`limits.aio.storage.Storage`
    #. Providing implementations for the abstractmethods of :class:`~limits.storage.Storage`
    #. If the storage can support the :ref:`strategies:moving window` strategy - additionally implementing
       the methods from :class:`~limits.storage.MovingWindowSupport`
    #. Providing naming *schemes* that can be used to lookup the custom storage in the storage registry.
       (Refer to :ref:`storage:storage scheme` for more details)

Example
=======

The following example shows two backend stores: one which doesn't implement the
:ref:`strategies:moving window` strategy and one that does. Do note the :code:`STORAGE_SCHEME` class
variables which result in the classes getting registered with the **limits** storage registry::


    import urlparse
    from limits.storage import MovingWindowSupport
    from limits.storage import Storage
    import time

    class AwesomeStorage(Storage):
        STORAGE_SCHEME = ["awesomedb"]
        def __init__(self, uri, **options):
            self.awesomesness = options.get("awesomeness", None)
            self.host = urlparse.urlparse(uri).netloc
            self.port = urlparse.urlparse(uri).port

        def check(self) -> bool:
            return True

        def get_expiry(self, key:str) -> int:
            return int(time.time())

        def incr(self, key: str, expiry: int, elastic_expiry=False) -> int:
            return

        def get(self, key):
            return 0


    class AwesomerStorage(Storage, MovingWindowSupport):
        STORAGE_SCHEME = ["awesomerdb"]
        def __init__(self, uri, **options):
            self.awesomesness = options.get("awesomeness", None)
            self.host = urlparse.urlparse(uri).netloc
            self.port = urlparse.urlparse(uri).port

        def check(self):
            return True

        def get_expiry(self, key):
            return int(time.time())

        def incr(self, key, expiry, elastic_expiry=False):
            return

        def get(self, key):
            return 0

        def acquire_entry(self, key, limit, expiry):
            return True

        def get_moving_window(
            self, key, limit, expiry
        ):
            return [0, 10]


Once the above implementations are declared you can look them up
using the :ref:`api:storage factory function` in the following manner::

    from limits.storage import storage_from_string

    awesome = storage_from_string("awesomedb://localhoax:42", awesomeness=0)
    awesomer = storage_from_string("awesomerdb://localhoax:42", awesomeness=1)
