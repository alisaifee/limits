SHELL = bash
ifneq ("$(wildcard ./google_appengine/VERSION)","")
GAE_INSTALLED = 1
else
GAE_INSTALLED = 0
endif

HOST_OS = $(shell uname -s)
ifeq ("$(HOST_OS)", "Darwin")
HOST_IP = $(shell ipconfig getifaddr en0)
OS_HACKS = osx-hacks
else
HOST_IP = $(shell hostname -I | awk '{print $$1}')
endif

PY_VERSION =$(shell python -c "import sys;print('.'.join(str(k) for k in sys.version_info[0:2]))")

clean:
	-rm -f MANIFEST
	-rm -rf dist/
	-rm -rf build/

cleancov:
	-rm -rf htmlcov/
	-coverage combine
	-coverage erase

cleanmeta:
	-rm -rf limits.egg-info/

cleanall: clean cleancov cleanmeta
	-find . -type f -name "*~" -exec rm -f "{}" \;
	-find . -type f -name "*.orig" -exec rm -f "{}" \;
	-find . -type f -name "*.rej" -exec rm -f "{}" \;
	-find . -type f -name "*.pyc" -exec rm -f "{}" \;
	-find . -type f -name "*.parse-index" -exec rm -f "{}" \;

sdist: cleanmeta
	python setup.py sdist

bdist: cleanmeta
	python setup.py bdist_egg

install:
	python setup.py install

redis-uds-start:
	redis-server --port 0 --unixsocket /tmp/limits.redis.sock --daemonize yes --pidfile /tmp/redis_unix-domain-socket.pid

redis-uds-stop:
	[ -e /tmp/redis_unix-domain-socket.pid ] && kill -9 `cat /tmp/redis_unix-domain-socket.pid` || true


memcached-uds-start:
	memcached -d -s /tmp/limits.memcached.sock -P /tmp/limits.memcached.uds.pid

memcached-uds-stop:
	[ -e /tmp/limits.memcached.uds.pid ] && kill `cat /tmp/limits.memcached.uds.pid` || true
	rm -rf /tmp/limits.memcached.*.pid

memcached-gae-install:
ifeq ($(PY_VERSION),2.7)
ifeq ($(GAE_INSTALLED),0)
	wget https://storage.googleapis.com/appengine-sdks/featured/google_appengine_1.9.91.zip -P /var/tmp/
	rm -rf google_appengine
	unzip -qu /var/tmp/google_appengine_1.9.91.zip -d .
else
	echo "GAE SDK already setup"
endif
	ln -sf google_appengine/google google
endif

memcached-gae-clean:
	rm google-cloud-sdk-167.0.0-linux-x86_64.tar.gz
	rm -r google-cloud-sdk

docker-down:
	docker-compose down --remove-orphans

docker-up: docker-down
	HOST_OS=$(HOST_OS) HOST_IP=$(HOST_IP) docker-compose up -d
	docker exec -i redis-cluster-5 bash -c "echo yes | redis-cli --cluster create --cluster-replicas 1 $(HOST_IP):{7000..7005}"

osx-hacks: redis-uds-stop memcached-uds-stop redis-uds-start memcached-uds-start

setup-backends: $(OS_HACKS) memcached-gae-install docker-up
tests: setup-backends
	nosetests tests --with-cov -v --with-timer --timer-top-n 10
.PHONY: test
