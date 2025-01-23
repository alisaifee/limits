import time
import urllib.parse
from typing import TYPE_CHECKING, Optional, Tuple, Type, Union

from limits.errors import ConcurrentUpdateError
from limits.storage.base import SlidingWindowCounterSupport, Storage

if TYPE_CHECKING:
    import etcd3


class EtcdStorage(Storage, SlidingWindowCounterSupport):
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
        max_retries: int = MAX_RETRIES,
        **options: str,
    ) -> None:
        """
        :param uri: etcd location of the form
         ``etcd://host:port``,
        :param max_retries: Maximum number of attempts to retry
         in the case of concurrent updates to a rate limit key
        :param options: all remaining keyword arguments are passed
         directly to the constructor of :class:`etcd3.Etcd3Client`
        :raise ConfigurationError: when :pypi:`etcd3` is not available
        """
        parsed = urllib.parse.urlparse(uri)
        self.lib = self.dependencies["etcd3"].module
        self.storage: "etcd3.Etcd3Client" = self.lib.client(
            parsed.hostname, parsed.port, **options
        )
        self.max_retries = max_retries

    @property
    def base_exceptions(
        self,
    ) -> Union[Type[Exception], Tuple[Type[Exception], ...]]:  # pragma: no cover
        return self.lib.Etcd3Exception  # type: ignore[no-any-return]

    def prefixed_key(self, key: str) -> bytes:
        return f"{self.PREFIX}/{key}".encode()

    @staticmethod
    def window_stat(value: bytes) -> Tuple[int, float]:
        if b":" in value:
            count, timestamp = value.split(b":")
            return int(count), float(timestamp)
        return 0, 0

    def incr(
        self, key: str, expiry: int, elastic_expiry: bool = False, amount: int = 1
    ) -> int:
        retries = 0
        etcd_key = self.prefixed_key(key)
        while retries < self.max_retries:
            now = time.time()
            lease = self.storage.lease(expiry)
            window_end = now + expiry
            create_attempt = self.storage.transaction(
                compare=[self.storage.transactions.create(etcd_key) == "0"],
                success=[
                    self.storage.transactions.put(
                        etcd_key,
                        f"{amount}:{window_end}".encode(),
                        lease=lease.id,
                    )
                ],
                failure=[self.storage.transactions.get(etcd_key)],
            )
            if create_attempt[0]:
                return amount
            else:
                cur, meta = create_attempt[1][0][0]
                cur_value, window_end = EtcdStorage.window_stat(cur)
                window_end = float(window_end)
                if window_end <= now:
                    self.storage.revoke_lease(meta.lease_id)
                    self.storage.delete(etcd_key)
                else:
                    if elastic_expiry:
                        self.storage.refresh_lease(meta.lease_id)
                        window_end = now + expiry
                    new = int(cur_value) + amount
                    if self.storage.transaction(
                        compare=[self.storage.transactions.value(etcd_key) == cur],
                        success=[
                            self.storage.transactions.put(
                                etcd_key,
                                f"{new}:{window_end}".encode(),
                                lease=meta.lease_id,
                            )
                        ],
                        failure=[],
                    )[0]:
                        return new
                retries += 1
        raise ConcurrentUpdateError(key, retries)

    def get(self, key: str) -> int:
        value, meta = self.storage.get(self.prefixed_key(key))
        if value:
            amount, expiry = EtcdStorage.window_stat(value)
            if expiry > time.time():
                return amount
        return 0

    def get_expiry(self, key: str) -> float:
        value, _ = self.storage.get(self.prefixed_key(key))
        if value:
            return EtcdStorage.window_stat(value)[1]
        return time.time()

    def check(self) -> bool:
        try:
            self.storage.status()
            return True
        except:  # noqa
            return False

    def reset(self) -> Optional[int]:
        return self.storage.delete_prefix(f"{self.PREFIX}/").deleted

    def clear(self, key: str) -> None:
        self.storage.delete(self.prefixed_key(key))

    def _current_window_key(
        self, key: str, expiry: int, now: Optional[float] = None
    ) -> str:
        if now is None:
            now = time.time()
        return f"{key}/{int(now / expiry)}"

    def _previous_window_key(
        self, key: str, expiry: int, now: Optional[float] = None
    ) -> str:
        if now is None:
            now = time.time()
        return f"{key}/{int((now - expiry) / expiry)}"

    def acquire_sliding_window_entry(
        self, key: str, limit: int, expiry: int, amount: int = 1
    ) -> bool:
        now = time.time()
        previous, previous_ttl, current, current_ttl = self._fetch_sliding_window(
            key, now, expiry
        )
        weighted_count = current + previous * (previous_ttl / expiry)
        if weighted_count + amount > limit or (
            self.incr(
                self._current_window_key(key, expiry, now), expiry * 2, amount=amount
            )
            > limit
        ):
            return False
        return True

    def get_sliding_window(
        self, key: str, expiry: Optional[int] = None
    ) -> tuple[int, float, int, float]:
        return self._fetch_sliding_window(key, time.time(), expiry)

    def _fetch_sliding_window(
        self, key: str, now: float, expiry: Optional[int] = None
    ) -> tuple[int, float, int, float]:
        result = self.storage.transaction(
            compare=[],
            success=[
                self.storage.transactions.get(
                    self.prefixed_key(self._previous_window_key(key, expiry, now))
                ),
                self.storage.transactions.get(
                    self.prefixed_key(self._current_window_key(key, expiry, now))
                ),
            ],
            failure=[],
        )
        current, previous, current_ttl, previous_ttl = 0, 0, 0, 0
        if result[0]:
            previous_window = result[1][0]
            current_window = result[1][1]
            if previous_window:
                previous, previous_expiry = EtcdStorage.window_stat(
                    previous_window[0][0]
                )
                previous_ttl = previous_expiry - now
            if current_window:
                current, current_expiry = EtcdStorage.window_stat(current_window[0][0])
                current_ttl = current_expiry - now
        return previous, previous_ttl, current, current_ttl
