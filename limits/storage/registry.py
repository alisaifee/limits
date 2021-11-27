from limits.errors import ConfigurationError
from abc import ABCMeta

SCHEMES = {}


class StorageRegistry(ABCMeta):
    def __new__(mcs, name, bases, dct):
        storage_scheme = dct.get("STORAGE_SCHEME", None)

        if not len(bases) == 0 and not storage_scheme:
            raise ConfigurationError(
                "%s is not configured correctly, "
                "it must specify a STORAGE_SCHEME class attribute" % name
            )
        print(bases)
        cls = super(StorageRegistry, mcs).__new__(mcs, name, bases, dct)

        if storage_scheme:
            if isinstance(storage_scheme, str):
                schemes = [storage_scheme]
            else:
                schemes = storage_scheme

            for scheme in schemes:
                SCHEMES[scheme] = cls

        return cls
