import pytest
import redis.sentinel

from limits.storage import RedisSentinelStorage, storage_from_string
from tests.storage.test_redis import SharedRedisTests


@pytest.mark.redis_sentinel
class TestRedisSentinelStorage(SharedRedisTests):
    @pytest.fixture(autouse=True)
    def setup(self, redis_sentinel):
        self.storage_url = "redis+sentinel://localhost:26379"
        self.service_name = "localhost-redis-sentinel"
        self.storage = RedisSentinelStorage(
            self.storage_url, service_name=self.service_name
        )

    def test_init_options(self, mocker):
        constructor = mocker.spy(redis.sentinel, "Sentinel")
        assert storage_from_string(
            self.storage_url + "/" + self.service_name,
            sentinel_kwargs={"socket_timeout": 1},
            socket_timeout=42,
        )
        assert constructor.call_args[1]["sentinel_kwargs"]["socket_timeout"] == 1
        assert constructor.call_args[1]["socket_timeout"] == 42

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
        mocker.patch("limits.util.get_dependency", return_value=lib)
        storage_url = (
            f"redis+sentinel://{username}:{password}@localhost:26379/service_name"
        )
        assert storage_from_string(storage_url).check()
        assert lib.Sentinel.call_args[1]["sentinel_kwargs"] == opts

    @pytest.mark.parametrize(
        "username, sentinel_password, password, success",
        [
            ("", "", "", False),
            ("username", "", "", False),
            ("", "sekret", "", False),
            ("", "sekret", "sekret", True),
        ],
    )
    def test_auth_connect(
        self, username, sentinel_password, password, success, redis_sentinel_auth
    ):
        redis_sentinel_auth.master_for(self.service_name).flushall()
        storage_url = (
            f"redis+sentinel://{username}:{sentinel_password}@localhost:36379/"
            "localhost-redis-sentinel"
        )
        assert success == storage_from_string(storage_url, password=password).check()
