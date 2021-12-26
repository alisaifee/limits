"""
setup.py for limits


"""
__author__ = "Ali-Akber Saifee"
__email__ = "ali@indydevs.org"
__copyright__ = "Copyright 2021, Ali-Akber Saifee"

import itertools
import os
from setuptools import setup, find_packages
import versioneer

THIS_DIR = os.path.abspath(os.path.dirname(__file__))


def get_requirements(req_file):
    requirements = []

    for r in open(os.path.join(THIS_DIR, "requirements", req_file)).read().splitlines():
        if r.strip():
            requirements.append(r.strip())

    return requirements


EXTRA_REQUIREMENTS = {
    "redis": get_requirements("storage/redis.txt"),
    "rediscluster": get_requirements("storage/rediscluster.txt"),
    "memcached": get_requirements("storage/memcached.txt"),
    "mongodb": get_requirements("storage/mongodb.txt"),
    "async-redis": get_requirements("storage/async-redis.txt"),
    "async-memcached": get_requirements("storage/async-memcached.txt"),
    "async-mongodb": get_requirements("storage/async-mongodb.txt"),
}
EXTRA_REQUIREMENTS["all"] = list(itertools.chain(*EXTRA_REQUIREMENTS.values()))

setup(
    name="limits",
    author=__author__,
    author_email=__email__,
    license="MIT",
    url="https://limits.readthedocs.org",
    zip_safe=False,
    version=versioneer.get_version(),
    cmdclass=versioneer.get_cmdclass(),
    install_requires=get_requirements("main.txt"),
    classifiers=[k for k in open("CLASSIFIERS").read().split("\n") if k],
    description="Rate limiting utilities",
    long_description=open("README.rst").read(),
    packages=find_packages(exclude=["google.*", "google", "tests*"]),
    python_requires=">=3.7",
    extras_require=EXTRA_REQUIREMENTS,
    include_package_data=True,
    package_data={
        "limits": ["py.typed"],
    },
)
