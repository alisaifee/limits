import pytest
import redis.sentinel

from limits.storage import RedisSentinelStorage, storage_from_string
from tests.storage.test_redis import SharedRedisTests


class TestRedisSentinelStorage(SharedRedisTests):
    def setup_method(self):
        self.storage_url = "redis+sentinel://localhost:26379"
        self.service_name = "localhost-redis-sentinel"
        self.storage = RedisSentinelStorage(
            self.storage_url, service_name=self.service_name
        )
        redis.sentinel.Sentinel([("localhost", 26379)]).master_for(
            self.service_name
        ).flushall()

    def test_init_options(self, mocker):
        lib = mocker.Mock()
        mocker.patch("limits.storage.redis_sentinel.get_dependency", return_value=lib)
        assert storage_from_string(
            self.storage_url + "/" + self.service_name, connection_timeout=1
        )
        assert lib.Sentinel.call_args[1]["connection_timeout"] == 1

    @pytest.mark.parametrize(
        "username, password, opts",
        [
            ("", "", {}),
            ("username", "", {"username": "username"}),
            ("", "sekret", {"password": "sekret"}),
        ],
    )
    def test_auth(self, mocker, username, password, opts):
        lib = mocker.Mock()
        mocker.patch("limits.storage.redis_sentinel.get_dependency", return_value=lib)
        storage_url = (
            f"redis+sentinel://{username}:{password}@localhost:26379/service_name"
        )
        assert storage_from_string(storage_url).check()
        assert lib.Sentinel.call_args[1]["sentinel_kwargs"] == opts

    @pytest.mark.parametrize(
        "username, password, success",
        [
            ("", "", False),
            ("username", "", False),
            ("", "sekret", True),
        ],
    )
    def test_auth_connect(self, username, password, success):
        storage_url = (
            f"redis+sentinel://{username}:{password}@localhost:36379/"
            "localhost-redis-sentinel"
        )
        assert success == storage_from_string(storage_url).check()
