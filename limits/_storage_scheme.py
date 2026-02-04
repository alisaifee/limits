from __future__ import annotations

import dataclasses
import urllib.parse
from abc import ABCMeta

SCHEMES: dict[str, StorageRegistry] = {}


class StorageRegistry(ABCMeta):
    def __new__(
        mcs, name: str, bases: tuple[type, ...], dct: dict[str, str | list[str]]
    ) -> StorageRegistry:
        storage_scheme = dct.get("STORAGE_SCHEME", None)
        cls = super().__new__(mcs, name, bases, dct)

        if storage_scheme:
            if isinstance(storage_scheme, str):  # noqa
                schemes = [storage_scheme]
            else:
                schemes = storage_scheme

            for scheme in schemes:
                SCHEMES[scheme] = cls

        return cls


@dataclasses.dataclass
class StorageURIOptions:
    scheme: str
    username: str | None
    password: str | None
    locations: list[tuple[str, int]]
    path: str | None
    query: dict[str, list[str]]

    @property
    def empty(self) -> bool:
        """
        whether this is just a scheme:// uri without any information
        that might be useful when constructing the actual storage
        instance
        """
        return bool(
            self.username is None
            and self.password is None
            and not (self.locations or self.path or self.query)
        )


def parse_storage_uri(uri: str) -> StorageURIOptions:
    parsed = urllib.parse.urlparse(uri)
    sep = parsed.netloc.find("@") + 1
    locations = []
    if parsed.netloc[sep:]:
        for loc in parsed.netloc[sep:].split(","):
            host, port = loc.split(":")
            locations.append((host, int(port)))
    return StorageURIOptions(
        parsed.scheme,
        parsed.username,
        parsed.password,
        locations,
        parsed.path,
        urllib.parse.parse_qs(parsed.query),
    )
