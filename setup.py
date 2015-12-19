"""
setup.py for limits


"""
__author__ = "Ali-Akber Saifee"
__email__ = "ali@indydevs.org"
__copyright__ = "Copyright 2015, Ali-Akber Saifee"

from setuptools import setup, find_packages
import os

this_dir = os.path.abspath(os.path.dirname(__file__))
REQUIREMENTS = [
    k for k in open(
        os.path.join(this_dir, 'requirements', 'main.txt')
    ).read().splitlines() if k.strip()
]
import versioneer

versioneer.versionfile_source = "limits/_version.py"
versioneer.versionfile_build = "limits/version.py"
versioneer.tag_prefix = ""
versioneer.parentdir_prefix = "limits-"

setup(
    name='limits',
    author=__author__,
    author_email=__email__,
    license="MIT",
    url="https://limits.readthedocs.org",
    zip_safe=False,
    version=versioneer.get_version(),
    cmdclass=versioneer.get_cmdclass(),
    install_requires=REQUIREMENTS,
    classifiers=[k for k in open('CLASSIFIERS').read().split('\n') if k],
    description='Rate limiting utilities',
    long_description=open('README.rst').read(),
    packages=find_packages(exclude=["tests*"]),
)

