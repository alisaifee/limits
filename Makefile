SHELL = bash
HOST_OS = $(shell uname -s)
ifeq ("$(HOST_OS)", "Darwin")
HOST_IP = $(shell ipconfig getifaddr en0)
OS_HACKS = osx-hacks
else
HOST_IP = $(shell hostname -I | awk '{print $$1}')
endif

PY_VERSION =$(shell python -c "import sys;print('.'.join(str(k) for k in sys.version_info[0:2]))")

redis-uds-start:
	redis-server --port 0 --unixsocket /tmp/limits.redis.sock --daemonize yes --pidfile /tmp/redis_unix-domain-socket.pid

redis-uds-stop:
	[ -e /tmp/redis_unix-domain-socket.pid ] && kill -9 `cat /tmp/redis_unix-domain-socket.pid` || true


memcached-uds-start:
	memcached -d -s /tmp/limits.memcached.sock -P /tmp/limits.memcached.uds.pid

memcached-uds-stop:
	[ -e /tmp/limits.memcached.uds.pid ] && kill `cat /tmp/limits.memcached.uds.pid` || true
	rm -rf /tmp/limits.memcached.*.pid

docker-down:
	docker-compose down --remove-orphans

docker-up: docker-down
	HOST_OS=$(HOST_OS) HOST_IP=$(HOST_IP) docker-compose up -d
	docker exec -i limits_redis-cluster-5_1 bash -c "echo yes | redis-cli --cluster create --cluster-replicas 1 $(HOST_IP):{7000..7005}"

osx-hacks: redis-uds-stop memcached-uds-stop redis-uds-start memcached-uds-start

setup-test-backends: $(OS_HACKS) docker-up
teardown-test-backends: $(OS_HACKS) docker-down

tests: setup-test-backends
	pytest -m "not integration" --durations=10

integration-tests: setup-test-backends
	pytest -m integration

all-tests: setup-test-backends
	pytest -m --durations=10
