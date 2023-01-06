import time
import urllib.parse
from typing import TYPE_CHECKING, Optional

from limits.aio.storage.base import Storage
from limits.errors import ConcurrentUpdateError

if TYPE_CHECKING:
    import aetcd


class EtcdStorage(Storage):
    """
    Rate limit storage with etcd as backend.

    Depends on :pypi:`etcd3`.
    """

    STORAGE_SCHEME = ["async+etcd"]
    """The async storage scheme for etcd"""
    DEPENDENCIES = ["aetcd"]

    PREFIX = "limits"
    MAX_RETRIES = 5

    def __init__(
        self,
        uri: str,
        max_retries: int = MAX_RETRIES,
        **options: str,
    ) -> None:
        """
        :param uri: etcd location of the form
         ``etcd://host:port``,
        :param max_retries: Maximum number of attempts to retry
         in the case of concurrent updates to a rate limit key
        :param options: all remaining keyword arguments are passed
         directly to the constructor of :class:`aetcd.client.Client`
        :raise ConfigurationError: when :pypi:`aetcd` is not available
        """
        parsed = urllib.parse.urlparse(uri)
        self.lib = self.dependencies["aetcd"].module
        self.storage: "aetcd.Client" = self.lib.Client(
            host=parsed.hostname, port=parsed.port, **options
        )
        self.max_retries = max_retries

    async def incr(
        self, key: str, expiry: int, elastic_expiry: bool = False, amount: int = 1
    ) -> int:
        retries = 0
        etcd_key = f"{self.PREFIX}/{key}".encode()
        while retries < self.max_retries:
            now = time.time()
            lease = await self.storage.lease(expiry)
            window_end = now + expiry
            if (
                await self.storage.transaction(
                    compare=[self.storage.transactions.create(etcd_key) == b"0"],
                    success=[
                        self.storage.transactions.put(
                            etcd_key, f"{amount}:{window_end}".encode(), lease=lease.id
                        )
                    ],
                    failure=[],
                )
            )[0]:
                return amount
            else:
                cur = await self.storage.get(etcd_key)
                if cur:
                    cur_value, window_end = cur.value.split(b":")
                    window_end = float(window_end)
                    if window_end <= now:
                        await self.storage.revoke_lease(cur.lease)
                        await self.storage.delete(etcd_key)
                    else:
                        if elastic_expiry:
                            await self.storage.refresh_lease(cur.lease)
                            window_end = now + expiry
                        new = int(cur_value) + amount
                        if (
                            await self.storage.transaction(
                                compare=[
                                    self.storage.transactions.value(etcd_key)
                                    == cur.value
                                ],
                                success=[
                                    self.storage.transactions.put(
                                        etcd_key,
                                        f"{new}:{window_end}".encode(),
                                        lease=cur.lease,
                                    )
                                ],
                                failure=[],
                            )
                        )[0]:
                            return new
                retries += 1
        raise ConcurrentUpdateError(key, retries)

    async def get(self, key: str) -> int:
        cur = await self.storage.get(f"{self.PREFIX}/{key}".encode())
        if cur:
            amount, expiry = cur.value.split(b":")
            if float(expiry) > time.time():
                return int(amount)
        return 0

    async def get_expiry(self, key: str) -> int:
        cur = await self.storage.get(f"{self.PREFIX}/{key}".encode())
        if cur:
            window_end = float(cur.value.split(b":")[1])
            return int(window_end)
        return int(time.time())

    async def check(self) -> bool:
        try:
            await self.storage.status()
            return True
        except:  # noqa
            return False

    async def reset(self) -> Optional[int]:
        return (await self.storage.delete_prefix(f"{self.PREFIX}/".encode())).deleted

    async def clear(self, key: str) -> None:
        await self.storage.delete(f"{self.PREFIX}/{key}".encode())
