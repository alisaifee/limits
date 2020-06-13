import urllib

from limits.errors import ConfigurationError
from limits.storage.registry import SCHEMES

from .base import AsyncStorage
from .memory import AsyncMemoryStorage
from .redis import AsyncRedisStorage

def async_storage_from_string(storage_string: str, **options) -> AsyncStorage:
    """
    factory function to get an instance of the async storage class based
    on the uri of the storage

    :param storage_string: a string of the form method://host:port
    :return: an instance of :class:`limits._async.storage.AsyncStorage`
    """
    scheme = urllib.parse.urlparse(storage_string).scheme
    if scheme not in SCHEMES:
        raise ConfigurationError(
            "unknown storage scheme : %s" % storage_string
        )
    return SCHEMES[scheme](storage_string, **options)


__all__ = [
    "storage_from_string",
    "AsyncStorage",
    "AsyncMemoryStorage",
    "AsyncRedisStorage",
    "AsyncRedisClusterStorage",
    "AsyncRedisSentinelStorage",
]
