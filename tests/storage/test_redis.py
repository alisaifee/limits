from __future__ import annotations

import pytest

from limits.storage import storage_from_string
from tests.utils import ALL_STORAGES


@pytest.fixture
def fubar():
    yield [1, 2, 3]


class TestRedisStorage:
    @pytest.mark.parametrize(
        "uri, args, fixture",
        [
            storage
            for name, storage in ALL_STORAGES.items()
            if name in {"redis", "redis-cluster", "redis-sentinel"}
        ],
    )
    def test_custom_prefix(self, uri, args, fixture):
        storage = storage_from_string(uri, **args, key_prefix="my-custom-prefix")
        assert 1 == storage.incr("test", 10)
        assert fixture.get("my-custom-prefix:test") == b"1"
