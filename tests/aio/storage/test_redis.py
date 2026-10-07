from __future__ import annotations

import pytest

from limits.storage import storage_from_string
from tests.utils import ALL_STORAGES_ASYNC


class TestRedisStorage:
    @pytest.mark.parametrize(
        "uri, args, fixture",
        [
            storage
            for name, storage in ALL_STORAGES_ASYNC.items()
            if name in {"redis", "redis-cluster", "redis-sentinel"}
        ],
    )
    async def test_custom_prefix(self, uri, args, fixture):
        storage = storage_from_string(uri, **args, key_prefix="my-custom-prefix")
        assert 1 == await storage.incr("test", 10)
        assert fixture.get("my-custom-prefix:test") == b"1"

    @pytest.mark.parametrize("uri, args, fixture", [ALL_STORAGES_ASYNC["redis"]])
    async def test_incr_sets_expiry_in_same_command(
        self, uri, args, fixture, monkeypatch
    ):
        storage = storage_from_string(uri, **args)

        async def expire(*_args, **_kwargs):
            raise ConnectionError("expire sent as a separate command")

        monkeypatch.setattr(storage.bridge.get_connection(), "expire", expire)

        assert 1 == await storage.incr("test", 10)
        assert 0 < fixture.ttl("LIMITS:test") <= 10
