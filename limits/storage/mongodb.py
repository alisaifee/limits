import datetime
import time
from typing import Any
from typing import Dict

from .base import Storage
from ..errors import ConfigurationError
from ..util import get_dependency


class MongoDBStorage(Storage):
    """
    Rate limit storage with MongoDB as backend.

    Depends on the :mod:`pymongo` library.
    """

    STORAGE_SCHEME = ["mongodb"]
    DEFAULT_OPTIONS = {
        "serverSelectionTimeoutMS": 100,
        "socketTimeoutMS": 100,
        "connectTimeoutMS": 100,
    }

    def __init__(self, uri: str, database_name: str = "limits", **options):
        """
        :param uri: uri of the form `mongodb://[user:password]@host:port?...`,
         This uri is passed directly to :class:`~pymongo.mongo_client.MongoClient`
        :param database_name: The database to use for storing the rate limit
         collections (Default: limits).
        :param options: all remaining keyword arguments are passed
         directly to the constructor of :class:`~pymongo.mongo_client.MongoClient`
        :raise ConfigurationError: when the pymongo library is not available
        """
        self.lib = get_dependency("pymongo")

        if not self.lib:
            raise ConfigurationError("pymongo prerequisite not available")

        mongo_opts = options.copy()
        [mongo_opts.setdefault(k, v) for k, v in self.DEFAULT_OPTIONS.items()]
        self.storage = self.lib.MongoClient(uri, **mongo_opts)
        self.counters = self.storage.get_database(database_name).counters
        self.windows = self.storage.get_database(database_name).windows
        self.__initialize_database()
        super(MongoDBStorage, self).__init__(uri, **options)

    def __initialize_database(self):
        self.counters.create_index("expireAt", expireAfterSeconds=0)
        self.windows.create_index("expireAt", expireAfterSeconds=0)

    def reset(self) -> int:
        """
        Delete all rate limit keys in the rate limit collections (counters, windows)
        """
        num_keys = self.counters.count_documents({}) + self.windows.count_documents({})
        self.counters.drop()
        self.windows.drop()

        return num_keys

    def clear(self, key: str):
        """
        :param key: the key to clear rate limits for
        """
        self.counters.find_one_and_delete({"_id": key})
        self.windows.find_one_and_delete({"_id": key})

    def get_expiry(self, key: str) -> int:
        """
        :param key: the key to get the expiry for
        """
        counter = self.counters.find_one({"_id": key})
        expiry = counter["expireAt"] if counter else datetime.datetime.utcnow()

        return int(time.mktime(expiry.timetuple()))

    def get(self, key: str):
        """
        :param key: the key to get the counter value for
        """
        counter = self.counters.find_one(
            {"_id": key, "expireAt": {"$gte": datetime.datetime.utcnow()}},
            projection=["count"],
        )

        return counter and counter["count"] or 0

    def incr(self, key: str, expiry: int, elastic_expiry=False) -> int:
        """
        increments the counter for a given rate limit key

        :param key: the key to increment
        :param expiry: amount in seconds for the key to expire in
        """
        expiration = datetime.datetime.utcnow() + datetime.timedelta(seconds=expiry)

        return self.counters.find_one_and_update(
            {"_id": key},
            [
                {
                    "$set": {
                        "count": {
                            "$cond": {
                                "if": {"$lt": ["$expireAt", "$$NOW"]},
                                "then": 1,
                                "else": {"$add": ["$count", 1]},
                            }
                        },
                        "expireAt": {
                            "$cond": {
                                "if": {"$lt": ["$expireAt", "$$NOW"]},
                                "then": expiration,
                                "else": (expiration if elastic_expiry else "$expireAt"),
                            }
                        },
                    }
                },
            ],
            upsert=True,
            projection=["count"],
            return_document=self.lib.ReturnDocument.AFTER,
        )["count"]

    def check(self) -> bool:
        """
        check if storage is healthy
        """
        try:
            self.storage.server_info()

            return True
        except:  # noqa: E722
            return False

    def get_moving_window(self, key, limit, expiry):
        """
        returns the starting point and the number of entries in the moving
        window

        :param str key: rate limit key
        :param int expiry: expiry of entry
        :return: (start of window, number of acquired entries)
        """
        timestamp = time.time()
        result = list(
            self.windows.aggregate(
                [
                    {"$match": {"_id": key}},
                    {
                        "$project": {
                            "entries": {
                                "$filter": {
                                    "input": "$entries",
                                    "as": "entry",
                                    "cond": {
                                        "$gte": [
                                            "$$entry",
                                            timestamp - expiry,
                                        ]
                                    },
                                }
                            }
                        }
                    },
                    {"$unwind": "$entries"},
                    {
                        "$group": {
                            "_id": "$_id",
                            "max": {"$max": "$entries"},
                            "count": {"$sum": 1},
                        }
                    },
                ]
            )
        )

        if result:
            return (int(result[0]["max"]), result[0]["count"])

        return (int(timestamp), 0)

    def acquire_entry(self, key: str, limit: int, expiry: int, no_add=False) -> bool:
        """
        :param key: rate limit key to acquire an entry in
        :param limit: amount of entries allowed
        :param expiry: expiry of the entry
        :param no_add: if False an entry is not actually acquired but
         instead serves as a 'check'
        """
        timestamp = time.time()
        try:
            updates: Dict[str, Any] = {
                "$push": {"entries": {"$each": [], "$position": 0, "$slice": limit}}
            }

            if not no_add:
                updates["$set"] = {
                    "expireAt": (
                        datetime.datetime.utcnow() + datetime.timedelta(seconds=expiry)
                    )
                }
                updates["$push"]["entries"]["$each"] = [timestamp]
            self.windows.update_one(
                {
                    "_id": key,
                    "entries.%d" % (limit - 1): {"$not": {"$gte": timestamp - expiry}},
                },
                updates,
                upsert=True,
            )

            return True
        except self.lib.errors.DuplicateKeyError:
            return False
