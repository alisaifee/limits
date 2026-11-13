from __future__ import annotations

import pickle
from unittest.mock import patch

from limits.storage import MemoryStorage


class TestMovingWindowExpiry:
    def test_expired_moving_window_keys_are_removed(self):
        with patch("limits.storage.memory.threading.Timer"):
            with patch("limits.storage.memory.time.time", return_value=1000):
                storage = MemoryStorage()
                for index in range(1000):
                    assert storage.acquire_entry(f"client:{index}", 1, 60)
            with patch("limits.storage.memory.time.time", return_value=1061):
                storage._MemoryStorage__expire_events()
            assert storage.events == {}
            assert storage.locks == {}

    def test_expired_moving_window_keys_mixed_with_live_ones(self):
        with patch("limits.storage.memory.threading.Timer"):
            with patch("limits.storage.memory.time.time", return_value=1000):
                storage = MemoryStorage()
                assert storage.acquire_entry("expired", 1, 60)
                assert storage.acquire_entry("live", 1, 120)
            with patch("limits.storage.memory.time.time", return_value=1061):
                storage._MemoryStorage__expire_events()
                # Repeated cleanup is a no-op for already removed keys.
                storage._MemoryStorage__expire_events()
            assert "expired" not in storage.events
            assert "expired" not in storage.locks
            assert len(storage.events["live"]) == 1
            # The expired key can be reused afterwards.
            with patch("limits.storage.memory.time.time", return_value=1061):
                assert storage.acquire_entry("expired", 1, 60)
            assert len(storage.events["expired"]) == 1


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
