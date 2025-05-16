from __future__ import annotations

import asyncio
import datetime
import time

from deprecated.sphinx import versionadded, versionchanged

from limits.aio.storage.base import (
    MovingWindowSupport,
    SlidingWindowCounterSupport,
    Storage,
)
from limits.typing import (
    ParamSpec,
    TypeVar,
    cast,
)
from limits.util import get_dependency

P = ParamSpec("P")
R = TypeVar("R")


@versionadded(version="2.1")
@versionchanged(
    version="3.14.0",
    reason="Added option to select custom collection names for windows & counters",
)
class MongoDBStorage(Storage, MovingWindowSupport, SlidingWindowCounterSupport):
    """
    Rate limit storage with MongoDB as backend.

    Depends on :pypi:`motor`
    """

    STORAGE_SCHEME = ["async+mongodb", "async+mongodb+srv"]
    """
    The storage scheme for MongoDB for use in an async context
    """

    DEPENDENCIES = ["motor.motor_asyncio", "pymongo"]

    def __init__(
        self,
        uri: str,
        database_name: str = "limits",
        counter_collection_name: str = "counters",
        window_collection_name: str = "windows",
        wrap_exceptions: bool = False,
        **options: float | str | bool,
    ) -> None:
        """
        :param uri: uri of the form ``async+mongodb://[user:password]@host:port?...``,
         This uri is passed directly to :class:`~motor.motor_asyncio.AsyncIOMotorClient`
        :param database_name: The database to use for storing the rate limit
         collections.
        :param counter_collection_name: The collection name to use for individual counters
         used in fixed window strategies
        :param window_collection_name: The collection name to use for sliding & moving window
         storage
        :param wrap_exceptions: Whether to wrap storage exceptions in
         :exc:`limits.errors.StorageError` before raising it.
        :param options: all remaining keyword arguments are passed
         to the constructor of :class:`~motor.motor_asyncio.AsyncIOMotorClient`
        :raise ConfigurationError: when the :pypi:`motor` or :pypi:`pymongo` are
         not available
        """

        uri = uri.replace("async+mongodb", "mongodb", 1)

        super().__init__(uri, wrap_exceptions=wrap_exceptions, **options)

        self.dependency = self.dependencies["motor.motor_asyncio"]
        self.proxy_dependency = self.dependencies["pymongo"]
        self.lib_errors, _ = get_dependency("pymongo.errors")

        self.storage = self.dependency.module.AsyncIOMotorClient(uri, **options)
        # TODO: Fix this hack. It was noticed when running a benchmark
        # with FastAPI - however - doesn't appear in unit tests or in an isolated
        # use. Reference: https://jira.mongodb.org/browse/MOTOR-822
        self.storage.get_io_loop = asyncio.get_running_loop

        self.__database_name = database_name
        self.__collection_mapping = {
            "counters": counter_collection_name,
            "windows": window_collection_name,
        }
        self.__indices_created = False

    @property
    def base_exceptions(
        self,
    ) -> type[Exception] | tuple[type[Exception], ...]:  # pragma: no cover
        return self.lib_errors.PyMongoError  # type: ignore

    @property
    def database(self):  # type: ignore
        return self.storage.get_database(self.__database_name)

    async def create_indices(self) -> None:
        if not self.__indices_created:
            await asyncio.gather(
                self.database[self.__collection_mapping["counters"]].create_index(
                    "expireAt", expireAfterSeconds=0
                ),
                self.database[self.__collection_mapping["windows"]].create_index(
                    "expireAt", expireAfterSeconds=0
                ),
            )
        self.__indices_created = True

    async def reset(self) -> int | None:
        """
        Delete all rate limit keys in the rate limit collections (counters, windows)
        """
        num_keys = sum(
            await asyncio.gather(
                self.database[self.__collection_mapping["counters"]].count_documents(
                    {}
                ),
                self.database[self.__collection_mapping["windows"]].count_documents({}),
            )
        )
        await asyncio.gather(
            self.database[self.__collection_mapping["counters"]].drop(),
            self.database[self.__collection_mapping["windows"]].drop(),
        )

        return cast(int, num_keys)

    async def clear(self, key: str) -> None:
        """
        :param key: the key to clear rate limits for
        """
        await asyncio.gather(
            self.database[self.__collection_mapping["counters"]].find_one_and_delete(
                {"_id": key}
            ),
            self.database[self.__collection_mapping["windows"]].find_one_and_delete(
                {"_id": key}
            ),
        )

    async def get_expiry(self, key: str) -> float:
        """
        :param key: the key to get the expiry for
        """
        counter = await self.database[self.__collection_mapping["counters"]].find_one(
            {"_id": key}
        )
        return (
            (counter["expireAt"] if counter else datetime.datetime.now())
            .replace(tzinfo=datetime.timezone.utc)
            .timestamp()
        )

    async def get(self, key: str) -> int:
        """
        :param key: the key to get the counter value for
        """
        counter = await self.database[self.__collection_mapping["counters"]].find_one(
            {
                "_id": key,
                "expireAt": {"$gte": datetime.datetime.now(datetime.timezone.utc)},
            },
            projection=["count"],
        )

        return counter and counter["count"] or 0

    async def incr(self, key: str, expiry: int, amount: int = 1) -> int:
        """
        increments the counter for a given rate limit key

        :param key: the key to increment
        :param expiry: amount in seconds for the key to expire in
        :param amount: the number to increment by
        """
        await self.create_indices()

        expiration = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(
            seconds=expiry
        )

        response = await self.database[
            self.__collection_mapping["counters"]
        ].find_one_and_update(
            {"_id": key},
            [
                {
                    "$set": {
                        "count": {
                            "$cond": {
                                "if": {"$lt": ["$expireAt", "$$NOW"]},
                                "then": amount,
                                "else": {"$add": ["$count", amount]},
                            }
                        },
                        "expireAt": {
                            "$cond": {
                                "if": {"$lt": ["$expireAt", "$$NOW"]},
                                "then": expiration,
                                "else": "$expireAt",
                            }
                        },
                    }
                },
            ],
            upsert=True,
            projection=["count"],
            return_document=self.proxy_dependency.module.ReturnDocument.AFTER,
        )

        return int(response["count"])

    async def check(self) -> bool:
        """
        Check if storage is healthy by calling
        :meth:`motor.motor_asyncio.AsyncIOMotorClient.server_info`
        """
        try:
            await self.storage.server_info()

            return True
        except:  # noqa: E722
            return False

    async def get_moving_window(
        self, key: str, limit: int, expiry: int
    ) -> tuple[float, int]:
        """
        returns the starting point and the number of entries in the moving
        window

        :param str key: rate limit key
        :param int expiry: expiry of entry
        :return: (start of window, number of acquired entries)
        """

        timestamp = time.time()
        if (
            result := await self.database[self.__collection_mapping["windows"]]
            .aggregate(
                [
                    {"$match": {"_id": key}},
                    {
                        "$project": {
                            "filteredEntries": {
                                "$filter": {
                                    "input": "$entries",
                                    "as": "entry",
                                    "cond": {"$gte": ["$$entry", timestamp - expiry]},
                                }
                            }
                        }
                    },
                    {
                        "$project": {
                            "min": {"$min": "$filteredEntries"},
                            "count": {"$size": "$filteredEntries"},
                        }
                    },
                ]
            )
            .to_list(length=1)
        ):
            return result[0]["min"], result[0]["count"]
        return timestamp, 0

    async def acquire_entry(
        self, key: str, limit: int, expiry: int, amount: int = 1
    ) -> bool:
        """
        :param key: rate limit key to acquire an entry in
        :param limit: amount of entries allowed
        :param expiry: expiry of the entry
        :param amount: the number of entries to acquire
        """
        await self.create_indices()

        if amount > limit:
            return False

        timestamp = time.time()
        try:
            updates: dict[
                str,
                dict[str, datetime.datetime | dict[str, list[float] | int]],
            ] = {
                "$push": {
                    "entries": {
                        "$each": [timestamp] * amount,
                        "$position": 0,
                        "$slice": limit,
                    }
                },
                "$set": {
                    "expireAt": (
                        datetime.datetime.now(datetime.timezone.utc)
                        + datetime.timedelta(seconds=expiry)
                    )
                },
            }

            await self.database[self.__collection_mapping["windows"]].update_one(
                {
                    "_id": key,
                    f"entries.{limit - amount}": {"$not": {"$gte": timestamp - expiry}},
                },
                updates,
                upsert=True,
            )

            return True
        except self.proxy_dependency.module.errors.DuplicateKeyError:
            return False

    async def acquire_sliding_window_entry(
        self, key: str, limit: int, expiry: int, amount: int = 1
    ) -> bool:
        await self.create_indices()
        expiry_ms = expiry * 1000
        result = await self.database[
            self.__collection_mapping["windows"]
        ].find_one_and_update(
            {"_id": key},
            [
                {
                    "$set": {
                        "previousCount": {
                            "$cond": {
                                "if": {
                                    "$lte": [
                                        {"$subtract": ["$expireAt", "$$NOW"]},
                                        expiry_ms,
                                    ]
                                },
                                "then": {"$ifNull": ["$currentCount", 0]},
                                "else": {"$ifNull": ["$previousCount", 0]},
                            }
                        },
                    }
                },
                {
                    "$set": {
                        "currentCount": {
                            "$cond": {
                                "if": {
                                    "$lte": [
                                        {"$subtract": ["$expireAt", "$$NOW"]},
                                        expiry_ms,
                                    ]
                                },
                                "then": 0,
                                "else": {"$ifNull": ["$currentCount", 0]},
                            }
                        },
                        "expireAt": {
                            "$cond": {
                                "if": {
                                    "$lte": [
                                        {"$subtract": ["$expireAt", "$$NOW"]},
                                        expiry_ms,
                                    ]
                                },
                                "then": {
                                    "$cond": {
                                        "if": {"$gt": ["$expireAt", 0]},
                                        "then": {"$add": ["$expireAt", expiry_ms]},
                                        "else": {"$add": ["$$NOW", 2 * expiry_ms]},
                                    }
                                },
                                "else": "$expireAt",
                            }
                        },
                    }
                },
                {
                    "$set": {
                        "curWeightedCount": {
                            "$floor": {
                                "$add": [
                                    {
                                        "$multiply": [
                                            "$previousCount",
                                            {
                                                "$divide": [
                                                    {
                                                        "$max": [
                                                            0,
                                                            {
                                                                "$subtract": [
                                                                    "$expireAt",
                                                                    {
                                                                        "$add": [
                                                                            "$$NOW",
                                                                            expiry_ms,
                                                                        ]
                                                                    },
                                                                ]
                                                            },
                                                        ]
                                                    },
                                                    expiry_ms,
                                                ]
                                            },
                                        ]
                                    },
                                    "$currentCount",
                                ]
                            }
                        }
                    }
                },
                {
                    "$set": {
                        "currentCount": {
                            "$cond": {
                                "if": {
                                    "$lte": [
                                        {"$add": ["$curWeightedCount", amount]},
                                        limit,
                                    ]
                                },
                                "then": {"$add": ["$currentCount", amount]},
                                "else": "$currentCount",
                            }
                        }
                    }
                },
                {
                    "$set": {
                        "_acquired": {
                            "$lte": [{"$add": ["$curWeightedCount", amount]}, limit]
                        }
                    }
                },
                {"$unset": ["curWeightedCount"]},
            ],
            return_document=self.proxy_dependency.module.ReturnDocument.AFTER,
            upsert=True,
        )

        return cast(bool, result["_acquired"])

    async def get_sliding_window(
        self, key: str, expiry: int
    ) -> tuple[int, float, int, float]:
        expiry_ms = expiry * 1000
        if result := await self.database[
            self.__collection_mapping["windows"]
        ].find_one_and_update(
            {"_id": key},
            [
                {
                    "$set": {
                        "previousCount": {
                            "$cond": {
                                "if": {
                                    "$lte": [
                                        {"$subtract": ["$expireAt", "$$NOW"]},
                                        expiry_ms,
                                    ]
                                },
                                "then": {"$ifNull": ["$currentCount", 0]},
                                "else": {"$ifNull": ["$previousCount", 0]},
                            }
                        },
                        "currentCount": {
                            "$cond": {
                                "if": {
                                    "$lte": [
                                        {"$subtract": ["$expireAt", "$$NOW"]},
                                        expiry_ms,
                                    ]
                                },
                                "then": 0,
                                "else": {"$ifNull": ["$currentCount", 0]},
                            }
                        },
                        "expireAt": {
                            "$cond": {
                                "if": {
                                    "$lte": [
                                        {"$subtract": ["$expireAt", "$$NOW"]},
                                        expiry_ms,
                                    ]
                                },
                                "then": {"$add": ["$expireAt", expiry_ms]},
                                "else": "$expireAt",
                            }
                        },
                    }
                }
            ],
            return_document=self.proxy_dependency.module.ReturnDocument.AFTER,
            projection=["currentCount", "previousCount", "expireAt"],
        ):
            expires_at = (
                (result["expireAt"].replace(tzinfo=datetime.timezone.utc).timestamp())
                if result.get("expireAt")
                else time.time()
            )
            current_ttl = max(0, expires_at - time.time())
            prev_ttl = max(0, current_ttl - expiry if result["previousCount"] else 0)

            return (
                result["previousCount"],
                prev_ttl,
                result["currentCount"],
                current_ttl,
            )
        return 0, 0.0, 0, 0.0

    async def clear_sliding_window(self, key: str, expiry: int) -> None:
        return await self.clear(key)

    def __del__(self) -> None:
        self.storage and self.storage.close()
