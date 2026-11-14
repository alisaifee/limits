from __future__ import annotations

import pytest

from limits.errors import ConfigurationError
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


class TestRedisStorageUri:
    @pytest.mark.parametrize(
        "uri, args",
        [
            ("async+redis://otherhost", {}),
            ("async+redis://otherhost", {"implementation": "redispy"}),
            ("async+valkey://otherhost", {}),
        ],
    )
    async def test_location_without_port(self, uri, args):
        storage = storage_from_string(uri, **args)
        connection_kwargs = storage.bridge.storage.connection_pool.connection_kwargs
        assert not storage.bridge.uri_is_empty
        assert connection_kwargs["host"] == "otherhost"

    @pytest.mark.parametrize(
        "uri",
        [
            "async+redis+cluster://localhost",
            "async+redis+sentinel://localhost/service",
            "async+valkey+cluster://localhost",
        ],
    )
    async def test_cluster_sentinel_location_without_port(self, uri):
        with pytest.raises(ConfigurationError, match="Missing host or port"):
            storage_from_string(uri)

    @pytest.mark.parametrize(
        "uri, args",
        [
            ("async+redis://user:pass@otherhost", {}),
            ("async+redis://otherhost", {"username": "user", "password": "pass"}),
            ("async+valkey://user:pass@otherhost", {}),
        ],
    )
    async def test_auth_without_port(self, uri, args):
        storage = storage_from_string(uri, **args)
        assert storage.bridge.parsed_auth == {"username": "user", "password": "pass"}
