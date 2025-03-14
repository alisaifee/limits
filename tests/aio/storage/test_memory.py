from __future__ import annotations

import pickle

from limits.aio.storage import MemoryStorage


class TestSerialization:
    async def test_pickle(self):
        storage = MemoryStorage()
        assert 1 == await storage.incr("test", 60)
        assert await storage.acquire_entry("moving_test", 2, 60)
        dump = pickle.dumps(storage)
        restored = pickle.loads(dump)
        assert 2 == await restored.incr("test", 60)
        assert await restored.acquire_entry("moving_test", 2, 60)
        assert not await restored.acquire_entry("moving_test", 2, 60)
