from __future__ import annotations

import pickle

from limits.storage import MemoryStorage


class TestSerialization:
    def test_pickle(self):
        storage = MemoryStorage()
        assert 1 == storage.incr("test", 60)
        assert storage.acquire_entry("moving_test", 2, 60)
        dump = pickle.dumps(storage)
        restored = pickle.loads(dump)
        assert 2 == restored.incr("test", 60)
        assert restored.acquire_entry("moving_test", 2, 60)
        assert not restored.acquire_entry("moving_test", 2, 60)
