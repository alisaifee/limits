import os
import platform
import socket
import time

import etcd3
import pymemcache
import pymemcache.client
import pymongo
import pytest
import redis
import redis.sentinel


def check_redis_cluster_ready(host, port):
    try:
        return redis.Redis(host, port).cluster("info")["cluster_state"] == "ok"
    except Exception:
        return False


def check_redis_ssl_cluster_ready(host, port):

    storage_url = (
        "rediss://localhost:8301/?ssl_cert_reqs=required"
        "&ssl_keyfile=./tests/tls/client.key"
        "&ssl_certfile=./tests/tls/client.crt"
        "&ssl_ca_certs=./tests/tls/ca.crt"
    )
    try:
        return (
            redis.Redis.from_url(storage_url).cluster("info")["cluster_state"] == "ok"
        )
    except Exception:
        return False


def check_sentinel_ready(host, port):
    try:
        return redis.sentinel.Sentinel([(host, port)]).master_for("mymaster").ping()
    except:  # noqa
        return False


def check_sentinel_auth_ready(host, port):
    try:
        return (
            redis.sentinel.Sentinel(
                [(host, port)],
                sentinel_kwargs={"password": "sekret"},
                password="sekret",
            )
            .master_for("mymaster")
            .ping()
        )
    except:  # noqa
        return False


def check_mongo_ready(host, port):
    try:
        pymongo.MongoClient("mongodb://localhost:37017").server_info()

        return True
    except:  # noqa
        return False


@pytest.fixture(scope="session")
def host_ip_env():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("10.255.255.255", 1))
        ip = s.getsockname()[0]
    except Exception:
        ip = "127.0.0.1"
    finally:
        s.close()
    os.environ["HOST_IP"] = str(ip)


@pytest.fixture(scope="session")
def docker_services(host_ip_env, docker_services):
    return docker_services


@pytest.fixture(scope="session")
def etcd_client(docker_services):
    docker_services.start("etcd")
    docker_services.wait_for_service("etcd", 2379)

    return etcd3.client()


@pytest.fixture(scope="session")
def redis_basic_client(docker_services):
    docker_services.start("redis-basic")

    return redis.StrictRedis("localhost", 7379)


@pytest.fixture(scope="session")
def redis_uds_client(docker_services):
    if platform.system().lower() == "darwin":
        pytest.skip("Fixture not supported on OSX")
    docker_services.start("redis-uds")

    return redis.from_url("unix:///tmp/limits.redis.sock")


@pytest.fixture(scope="session")
def redis_auth_client(docker_services):
    docker_services.start("redis-auth")

    return redis.from_url("redis://:sekret@localhost:7389")


@pytest.fixture(scope="session")
def redis_ssl_client(docker_services):
    docker_services.start("redis-ssl")
    storage_url = (
        "rediss://localhost:8379/0?ssl_cert_reqs=required"
        "&ssl_keyfile=./tests/tls/client.key"
        "&ssl_certfile=./tests/tls/client.crt"
        "&ssl_ca_certs=./tests/tls/ca.crt"
    )

    return redis.from_url(storage_url)


@pytest.fixture(scope="session")
def redis_cluster_client(docker_services):
    docker_services.start("redis-cluster-init")
    docker_services.wait_for_service("redis-cluster-6", 7006, check_redis_cluster_ready)
    if os.environ.get("CI") == "True":
        time.sleep(10)

    return redis.cluster.RedisCluster("localhost", 7001)


@pytest.fixture(scope="session")
def redis_ssl_cluster_client(docker_services):
    docker_services.start("redis-ssl-cluster-init")
    docker_services.wait_for_service(
        "redis-ssl-cluster-6", 8306, check_redis_ssl_cluster_ready
    )
    if os.environ.get("CI") == "True":
        time.sleep(10)

    storage_url = (
        "rediss://localhost:8301/?ssl_cert_reqs=required"
        "&ssl_keyfile=./tests/tls/client.key"
        "&ssl_certfile=./tests/tls/client.crt"
        "&ssl_ca_certs=./tests/tls/ca.crt"
    )
    return redis.cluster.RedisCluster.from_url(storage_url)


@pytest.fixture(scope="session")
def redis_sentinel_client(docker_services):
    docker_services.start("redis-sentinel")
    docker_services.wait_for_service("redis-sentinel", 26379, check_sentinel_ready)

    return redis.sentinel.Sentinel([("localhost", 26379)])


@pytest.fixture(scope="session")
def redis_sentinel_auth_client(docker_services):
    docker_services.start("redis-sentinel-auth")
    docker_services.wait_for_service(
        "redis-sentinel-auth", 26379, check_sentinel_auth_ready
    )

    return redis.sentinel.Sentinel(
        [("localhost", 36379)],
        sentinel_kwargs={"password": "sekret"},
        password="sekret",
    )


@pytest.fixture(scope="session")
def memcached_client(docker_services):
    docker_services.start("memcached-1")

    return pymemcache.Client(("localhost", 22122))


@pytest.fixture(scope="session")
def memcached_cluster_client(docker_services):
    docker_services.start("memcached-1")
    docker_services.start("memcached-2")

    return pymemcache.client.HashClient([("localhost", 22122), ("localhost", 22123)])


@pytest.fixture(scope="session")
def memcached_uds_client(docker_services):
    if platform.system().lower() == "darwin":
        pytest.skip("Fixture not supported on OSX")
    docker_services.start("memcached-uds")

    return pymemcache.Client("/tmp/limits.memcached.sock")


@pytest.fixture(scope="session")
def mongodb_client(docker_services):
    docker_services.start("mongodb")
    docker_services.wait_for_service("mongodb", 27017, check_mongo_ready)

    return pymongo.MongoClient("mongodb://localhost:37017")


@pytest.fixture
def memcached(memcached_client):
    memcached_client.flush_all()

    return memcached_client


@pytest.fixture
def memcached_uds(memcached_uds_client):
    memcached_uds_client.flush_all()

    return memcached_uds_client


@pytest.fixture
def memcached_cluster(memcached_cluster_client):
    memcached_cluster_client.flush_all()

    return memcached_cluster_client


@pytest.fixture
def redis_basic(redis_basic_client):
    redis_basic_client.flushall()

    return redis_basic


@pytest.fixture
def redis_ssl(redis_ssl_client):
    redis_ssl_client.flushall()

    return redis_ssl_client


@pytest.fixture
def redis_auth(redis_auth_client):
    redis_auth_client.flushall()

    return redis_auth_client


@pytest.fixture
def redis_uds(redis_uds_client):
    redis_uds_client.flushall()

    return redis_uds_client


@pytest.fixture
def redis_cluster(redis_cluster_client):
    redis_cluster_client.flushall()

    return redis_cluster_client


@pytest.fixture
def redis_ssl_cluster(redis_ssl_cluster_client):
    redis_ssl_cluster_client.flushall()

    return redis_ssl_cluster_client


@pytest.fixture
def redis_sentinel(redis_sentinel_client):
    redis_sentinel_client.master_for("mymaster").flushall()

    return redis_sentinel


@pytest.fixture
def redis_sentinel_auth(redis_sentinel_auth_client):
    redis_sentinel_auth_client.master_for("mymaster").flushall()

    return redis_sentinel_auth_client


@pytest.fixture
def mongodb(mongodb_client):
    mongodb_client.limits.windows.drop()
    mongodb_client.limits.counters.drop()

    return mongodb_client


@pytest.fixture
def etcd(etcd_client):
    etcd_client.delete_prefix("limits/")
    return etcd_client


@pytest.fixture(scope="session")
def docker_services_project_name():
    return "limits"


@pytest.fixture(scope="session")
def docker_compose_files(pytestconfig):
    """Get the docker-compose.yml absolute path.
    Override this fixture in your tests if you need a custom location.
    """

    return ["docker-compose.yml"]
