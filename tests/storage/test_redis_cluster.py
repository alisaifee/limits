from __future__ import annotations

import pytest

from limits.storage.redis_cluster import RedisClusterStorage


class TestRedisClusterStorageEncodePassword:
    """Test encode_password_in_url static method"""

    @pytest.mark.parametrize(
        "input_url, expected_output",
        [
            # Test cases from the image
            (
                "redis+cluster://user:pass#word@localhost:7001",
                "redis+cluster://user:pass%23word@localhost:7001",
            ),
            (
                "redis+cluster://:pass#word@localhost:7001",
                "redis+cluster://:pass%23word@localhost:7001",
            ),
            (
                "redis+cluster://user:p@ss#w:rd@localhost:7001",
                "redis+cluster://user:p%40ss%23w%3Ard@localhost:7001",
            ),
            # No authentication case - should remain unchanged
            (
                "redis+cluster://localhost:7001",
                "redis+cluster://localhost:7001",
            ),
        ],
    )
    def test_encode_password_in_url(self, input_url, expected_output):
        """Test encode_password_in_url encodes special characters correctly"""
        result = RedisClusterStorage.encode_password_in_url(input_url)
        assert result == expected_output

    def test_encode_password_in_url_no_scheme(self):
        """Test encode_password_in_url with URL without scheme"""
        url = "localhost:7001"
        result = RedisClusterStorage.encode_password_in_url(url)
        assert result == url

    def test_encode_password_in_url_no_auth(self):
        """Test encode_password_in_url with URL without auth part"""
        url = "redis+cluster://localhost:7001,localhost:7002"
        result = RedisClusterStorage.encode_password_in_url(url)
        assert result == url
