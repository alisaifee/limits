from abc import ABCMeta
from typing import Dict, Type, cast

SCHEMES: Dict[str, Type] = {}


class StorageRegistry(ABCMeta):
    def __new__(mcs, name, bases, dct):
        storage_scheme = dct.get("STORAGE_SCHEME", None)
        cls = cast(Type, super(StorageRegistry, mcs).__new__(mcs, name, bases, dct))

        if storage_scheme:
            if isinstance(storage_scheme, str):  # noqa
                schemes = [storage_scheme]
            else:
                schemes = storage_scheme

            for scheme in schemes:
                SCHEMES[scheme] = cls

        return cls
