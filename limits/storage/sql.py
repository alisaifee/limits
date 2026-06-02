from __future__ import annotations

from datetime import datetime, timedelta, timezone
from math import floor
from typing import Tuple

from sqlalchemy import (
    TIMESTAMP,
    Column,
    Integer,
    MetaData,
    String,
    Table,
    and_,
    create_engine,
    func,
    select,
    text,
)
from sqlalchemy.exc import SQLAlchemyError

from limits.storage.base import (
    MovingWindowSupport,
    SlidingWindowCounterSupport,
    Storage,
)


def _as_utc(dt: datetime) -> datetime:
    """Return dt as a UTC-aware datetime, attaching UTC if it is naive."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


class SqlStorage(
    Storage, MovingWindowSupport, SlidingWindowCounterSupport
):
    """
    Rate limit storage with SQL as backend.

    Depends on :pypi:`SQLAlchemy`.
    """

    # TODO: SqlAlchemy supports a lot of database and dialects. Find a way to recognize all schemes.
    STORAGE_SCHEME = [
        "postgresql",
        "postgresql+psycopg2",
        "postgresql+pg8000",
        "mysql",
        "mysql+mysqldb",
        "mysql+pymysql",
        "sqlite",
    ]

    DEPENDENCIES = ["sqlalchemy"]

    def __init__(
        self,
        uri: str,
        moving_window_table_name: str = "limits_moving_window",
        fixed_sliding_window_table_name: str = "limits_fixed_and_sliding_window",
        wrap_exceptions: bool = False,
        **options: int | str | bool,
    ):
        super().__init__(uri, wrap_exceptions=wrap_exceptions, **options)
        self.moving_window_table_name = moving_window_table_name
        self.fixed_sliding_window_table_name = fixed_sliding_window_table_name
        self.metadata = MetaData()
        self.engine = create_engine(uri)
        # Table for moving window
        self.moving_window_table = Table(
            self.moving_window_table_name,
            self.metadata,
            Column("id", Integer, primary_key=True, autoincrement=True),
            Column("key", String(255), nullable=False, index=True),
            Column("timestamp", TIMESTAMP(timezone=True), nullable=False, index=True),
            Column("amount", Integer, nullable=False),
        )
        # Table for fixed and sliding window
        self.fixed_and_sliding_window_table = Table(
            self.fixed_sliding_window_table_name,
            self.metadata,
            Column("key", String(255), primary_key=True, index=True),
            Column("current_count", Integer, nullable=False),
            Column("previous_count", Integer, nullable=True),
            # previous count is only for sliding window
            Column(
                "expiry_timestamp", TIMESTAMP(timezone=True), nullable=False, index=True
            ),
        )
        with self.engine.begin() as conn:
            self.metadata.create_all(conn)

    @property
    def base_exceptions(self) -> type[SQLAlchemyError]:
        return SQLAlchemyError

    def check(self):
        with self.engine.connect() as conn:
            return bool(conn.execute(text("SELECT 1")).scalar_one() == 1)

    def get_expiry(self, key: str):
        """Get the expiry timestamp for a given key from the fixed/sliding window table."""
        with self.engine.begin() as conn:
            query = self.fixed_and_sliding_window_table.select().where(
                and_(self.fixed_and_sliding_window_table.c.key == key)
            )
            result = conn.execute(query).first()
            if result and result.expiry_timestamp:
                return float(
                    result.expiry_timestamp.replace(tzinfo=timezone.utc).timestamp()
                )
            else:
                return float(datetime.now(timezone.utc).timestamp())

    def incr(self, key: str, expiry: int, amount: int = 1) -> int:
        updated_count = None
        with self.engine.begin() as conn:
            row = conn.execute(
                self.fixed_and_sliding_window_table.select().where(
                    and_(self.fixed_and_sliding_window_table.c.key == key)
                )
            ).first()
            current_timestamp = datetime.now(timezone.utc)
            if not row:
                # first entry for this rate limit
                expiry_timestamp = current_timestamp + timedelta(seconds=expiry)
                conn.execute(
                    self.fixed_and_sliding_window_table.insert().values(
                        key=key,
                        current_count=amount,
                        previous_count=0,
                        expiry_timestamp=expiry_timestamp,
                    )
                )
                updated_count = amount
            elif row and _as_utc(row.expiry_timestamp) <= current_timestamp:
                # last window has expired, update expiry and reset count
                expiry_timestamp = current_timestamp + timedelta(seconds=expiry)
                conn.execute(
                    self.fixed_and_sliding_window_table.update()
                    .where(and_(self.fixed_and_sliding_window_table.c.key == key))
                    .values(
                        current_count=amount,
                        previous_count=0,
                        expiry_timestamp=expiry_timestamp,
                    )
                )
                updated_count = amount
            elif row and current_timestamp < _as_utc(row.expiry_timestamp):
                # within the same window, increment count
                new_count = row.current_count + amount
                conn.execute(
                    self.fixed_and_sliding_window_table.update()
                    .where(and_(self.fixed_and_sliding_window_table.c.key == key))
                    .values(current_count=new_count)
                )
                updated_count = new_count

        return updated_count

    def get(self, key: str) -> int:
        with self.engine.begin() as conn:
            current_timestamp = datetime.now(timezone.utc)
            query = self.fixed_and_sliding_window_table.select().where(
                and_(
                    self.fixed_and_sliding_window_table.c.key == key,
                    self.fixed_and_sliding_window_table.c.expiry_timestamp
                    > current_timestamp,
                )
            )
            result = conn.execute(query).first()
            if result:
                return result.current_count
            else:
                return 0

    def reset(self) -> None:
        """Delete all entries from the rate limit table."""
        with self.engine.begin() as conn:
            conn.execute(self.fixed_and_sliding_window_table.delete())
            conn.execute(self.moving_window_table.delete())

    def clear(self, key: str) -> None:
        """Delete all entries for the given key from the rate limit table."""
        with self.engine.begin() as conn:
            conn.execute(
                self.fixed_and_sliding_window_table.delete().where(
                    and_(self.fixed_and_sliding_window_table.c.key == key)
                )
            )
            conn.execute(
                self.moving_window_table.delete().where(
                    and_(self.moving_window_table.c.key == key)
                )
            )

    # --- Moving Window Support ---
    def acquire_entry(self, key: str, limit: int, expiry: int, amount: int = 1) -> bool:
        """
        Acquire an entry in the moving window if it does not exceed the limit.
        """
        with self.engine.begin() as conn:
            current_time = datetime.now(timezone.utc)
            cutoff_time = current_time - timedelta(seconds=expiry)
            # Delete expired entries for this key
            conn.execute(
                self.moving_window_table.delete().where(
                    (self.moving_window_table.c.key == key)
                    & (self.moving_window_table.c.timestamp < cutoff_time)
                )
            )
            # Count existing entries within the window
            existing_count = conn.scalar(
                select(func.sum(self.moving_window_table.c.amount)).where(
                    (self.moving_window_table.c.key == key)
                    & (self.moving_window_table.c.timestamp >= cutoff_time)
                )
            ) or 0
            # Check if adding the new entry would exceed the limit
            if existing_count + amount > limit:
                return False

            insert_query = self.moving_window_table.insert().values(
                key=key, timestamp=current_time, amount=amount
            )
            conn.execute(insert_query)

            return True

    def get_moving_window(self, key: str, limit: int, expiry: int) -> Tuple[float, int]:
        """
        Get timestamp of first entry within the current moving window and the total entries in the window.
        """
        with self.engine.begin() as conn:
            current_time = datetime.now(timezone.utc)
            cutoff_time = current_time - timedelta(seconds=expiry)
            result = conn.execute(
                select(func.min(self.moving_window_table.c.timestamp),
                       func.sum(self.moving_window_table.c.amount)
                ).where(
                    (self.moving_window_table.c.key == key)
                    & (self.moving_window_table.c.timestamp >= cutoff_time)
                )
            ).first()
            if result:
                earliest_timestamp, existing_count = result
                return _as_utc(earliest_timestamp).timestamp() if earliest_timestamp else current_time.timestamp(), existing_count or 0
            else:
                return current_time.timestamp(), 0

    # --- Sliding Window Counter Support ---
    def acquire_sliding_window_entry(
        self, key: str, limit: int, expiry: int, amount: int = 1
    ) -> bool:
        success = False
        with self.engine.begin() as conn:
            row = conn.execute(
                self.fixed_and_sliding_window_table.select().where(
                    and_(
                        self.fixed_and_sliding_window_table.c.key == key
                    )  # Only one row for each key should exist
                )
            ).first()
            current_timestamp = datetime.now(timezone.utc)
            if not row:
                # first entry for this rate limit
                expiry_timestamp = current_timestamp + timedelta(seconds=expiry)
                success = amount <= limit
                if success:
                    conn.execute(
                        self.fixed_and_sliding_window_table.insert().values(
                            key=key,
                            current_count=amount,
                            previous_count=0,
                            expiry_timestamp=expiry_timestamp,
                        )
                    )
            elif row and _as_utc(row.expiry_timestamp) <= current_timestamp:
                # last window has expired, calculate new expiry,
                # set current count to amount
                # set previous count to current count of the last window if last window expired less than expiry seconds ago, otherwise set previous count to 0
                row_expiry = _as_utc(row.expiry_timestamp)
                expiry_timestamp = row_expiry + timedelta(seconds=(1 + (current_timestamp - row_expiry).total_seconds()//expiry)*expiry)
                previous_count = (
                    min(limit, row.current_count) # use min to be safe
                    if current_timestamp - row_expiry < timedelta(seconds=expiry)
                    else 0
                )
                weight = (
                    expiry - (current_timestamp - row_expiry).total_seconds() % expiry) / expiry
                new_count = int(floor(amount + weight * previous_count))
                success = new_count <= limit
                if success:
                    conn.execute(
                        self.fixed_and_sliding_window_table.update()
                        .where(and_(self.fixed_and_sliding_window_table.c.key == key))
                        .values(
                            current_count=amount,
                            previous_count=previous_count,
                            expiry_timestamp=expiry_timestamp,
                        )
                    )
            elif row and _as_utc(row.expiry_timestamp) > current_timestamp:
                # within the current window
                # calculate weight of the previous count and add it to the current count to check if it exceeds the limit, if not increment current count by amount
                row_expiry = _as_utc(row.expiry_timestamp)
                weight = (
                    expiry - ((current_timestamp - (row_expiry - timedelta(seconds=expiry))).total_seconds())
                ) / expiry
                new_count = int(floor(row.current_count + amount + weight * row.previous_count))
                success = new_count <= limit
                if success:
                    conn.execute(
                        self.fixed_and_sliding_window_table.update()
                        .where(and_(self.fixed_and_sliding_window_table.c.key == key))
                        .values(current_count=row.current_count + amount)
                    )

        return success

    def get_sliding_window(
        self, key: str, expiry: int
    ) -> Tuple[int, float, int, float]:
        with self.engine.begin() as conn:
            row = conn.execute(
                self.fixed_and_sliding_window_table.select().where(
                    and_(self.fixed_and_sliding_window_table.c.key == key)
                )
            ).first()
            if row:
                current_timestamp = datetime.now(timezone.utc)
                row_expiry = _as_utc(row.expiry_timestamp)
                if row_expiry > current_timestamp:
                    # within the current window, calculate TTLs
                    current_ttl = (row_expiry - current_timestamp).total_seconds()
                    current_count = row.current_count
                    prev_ttl = expiry - (current_timestamp - (row_expiry - timedelta(seconds=expiry))).total_seconds()
                    prev_count = row.previous_count
                elif row_expiry <= current_timestamp:
                    # last window has expired, calculate new expiry, current_ttl is based on this new expiry.
                    # prev_ttl is expiry minus time elapsed since prev window expiry
                    # current count will be 0, set previous count to current count of the last window if last window expired less than expiry seconds ago, otherwise 0
                    expiry_timestamp = row_expiry + timedelta(seconds=(1 + (
                                current_timestamp - row_expiry).total_seconds() // expiry) * expiry)
                    current_ttl = (expiry_timestamp - current_timestamp).total_seconds()
                    current_count = 0
                    prev_ttl = expiry - ((current_timestamp - row_expiry).total_seconds() % expiry)
                    prev_count = (
                        row.current_count
                        if current_timestamp - row_expiry < timedelta(seconds=expiry)
                        else 0
                    )
                return (
                    prev_count,
                    prev_ttl,
                    current_count,
                    current_ttl,
                )
            else:
                return 0, 0.0, 0, 0.0

    def clear_sliding_window(self, key: str, expiry: int) -> None:
        with self.engine.begin() as conn:
            conn.execute(
                self.fixed_and_sliding_window_table.delete().where(
                    and_(self.fixed_and_sliding_window_table.c.key == key)
                )
            )

    def __del__(self) -> None:
        if self.engine:
            self.engine.dispose()