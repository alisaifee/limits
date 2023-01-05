import time
import urllib.parse
from typing import TYPE_CHECKING, Optional

from limits.errors import ConcurrentUpdateError
from limits.storage.base import Storage

if TYPE_CHECKING:
    import etcd3


class EtcdStorage(Storage):
    """
    Rate limit storage with etcd as backend.

    Depends on :pypi:`etcd3`.
    """

    STORAGE_SCHEME = ["etcd"]
    """The storage scheme for etcd"""
    DEPENDENCIES = ["etcd3"]
    PREFIX = "limits"
    MAX_RETRIES = 5

    def __init__(
        self,
        uri: str,
        **options: str,
    ) -> None:
        """
        :param uri: etcd location of the form
         ``etcd://host:port``,
        :param options: all remaining keyword arguments are passed
         directly to the constructor of :class:`etcd3.Etcd3Client`
        :raise ConfigurationError: when :pypi:`etcd3` is not available
        """
        parsed = urllib.parse.urlparse(uri)
        self.lib = self.dependencies["etcd3"].module
        self.storage: "etcd3.Etcd3Client" = self.lib.client(
            parsed.hostname, parsed.port, **options
        )

    def incr(
        self, key: str, expiry: int, elastic_expiry: bool = False, amount: int = 1
    ) -> int:
        retries = 0
        while retries < self.MAX_RETRIES:
            now = time.time()
            lease = self.storage.lease(expiry)
            window_end = now + expiry
            if self.storage.put_if_not_exists(
                f"{self.PREFIX}/{key}",
                f"{amount}:{window_end}".encode(),
                lease=lease.id,
            ):
                return amount
            else:
                cur, meta = self.storage.get(f"{self.PREFIX}/{key}")
                if cur:
                    cur_value, window_end = cur.split(b":")
                    window_end = float(window_end)
                    if window_end <= now:
                        self.storage.revoke_lease(meta.lease_id)
                        self.storage.delete(f"{self.PREFIX}/{key}")
                    else:
                        if elastic_expiry:
                            self.storage.refresh_lease(meta.lease_id)
                            window_end = now + expiry
                        new = int(cur_value) + amount
                        if self.storage.transaction(
                            compare=[
                                self.storage.transactions.value(f"{self.PREFIX}/{key}")
                                == cur
                            ],
                            success=[
                                self.storage.transactions.put(
                                    f"{self.PREFIX}/{key}",
                                    f"{new}:{window_end}".encode(),
                                    lease=meta.lease_id,
                                )
                            ],
                            failure=[],
                        )[0]:
                            return new
                retries += 1
        raise ConcurrentUpdateError()

    def get(self, key: str) -> int:
        value, meta = self.storage.get(f"{self.PREFIX}/{key}")
        if value:
            return int(value.split(b":")[0])
        return 0

    def get_expiry(self, key: str) -> int:
        value, _ = self.storage.get(f"{self.PREFIX}/{key}")
        if value:
            window_end = float(value.split(b":")[1])
            return int(window_end)
        return int(time.time())

    def check(self) -> bool:
        try:
            self.storage.status()
            return True
        except:  # noqa
            return False

    def reset(self) -> Optional[int]:
        return self.storage.delete_prefix(f"{self.PREFIX}/").deleted

    def clear(self, key: str) -> None:
        self.storage.delete(f"{self.PREFIX}/{key}")
