#
from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.abspath("../../"))
sys.path.insert(0, os.path.abspath("./"))

from theme_config import *  # noqa

import limits

project = "limits"
description = "limits is a python library to perform rate limiting with commonly used storage backends"
copyright = "2023, Ali-Akber Saifee"


if ".post0.dev" in limits.__version__:
    version, ahead = limits.__version__.split(".post0.dev")
else:
    version = limits.__version__
    ahead = 0

release = version


if branch_from_env := os.environ.get("READTHEDOCS_VERSION", None):
    branch_from_env = "master" if branch_from_env == "latest" else branch_from_env
    benchmark_git_context = {
        "branch": branch_from_env,
        "sha": os.environ.get("READTHEDOCS_GIT_COMMIT_HASH", ""),
    }
else:
    import limits._version

    git_info = limits._version.git_pieces_from_vcs("", os.path.abspath("../../"), False)
    benchmark_git_context = {
        "branch": git_info.get("branch", ""),
        "sha": git_info.get("long", None),
    }

html_static_path = ["_static"]

html_css_files = [
    "custom.css",
    "https://fonts.googleapis.com/css2?family=Fira+Code:wght@300;400;700&family=Fira+Sans:ital,wght@0,100;0,200;0,300;0,400;0,500;0,600;0,700;0,800;0,900;1,100;1,200;1,300;1,400;1,500;1,600;1,700;1,800;1,900&display=swap",
]

html_title = f"{project} <small><b style='color: var(--color-brand-primary)'>{{{release}}}</b></small>"

try:
    ahead = int(ahead)
    if ahead > 0:
        html_theme_options[  # noqa
            "announcement"
        ] = f"""
        This is a development version. The documentation for the latest version: <b>{release}</b> can be found <a href="/en/stable">here</a>
        """
        html_title = f"{project} <small><b style='color: var(--color-brand-primary)'>{{dev}}</b></small>"
except ValueError:
    pass
sys.path.append(str(Path("ext").resolve()))

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.autosectionlabel",
    "sphinx.ext.autosummary",
    "sphinx.ext.extlinks",
    "sphinx.ext.intersphinx",
    "sphinx.ext.todo",
    "sphinx.ext.viewcode",
    "sphinx.ext.mathjax",
    "sphinxext.opengraph",
    "sphinxcontrib.programoutput",
    "sphinx_copybutton",
    "sphinx_inline_tabs",
    "sphinx_paramlinks",
    "bench_chart",
]

autodoc_default_options = {
    "members": True,
    "inherited-members": True,
    "inherit-docstrings": True,
    "member-order": "bysource",
}

add_module_names = False
autoclass_content = "both"
autodoc_typehints_format = "short"
autosectionlabel_maxdepth = 3
autosectionlabel_prefix_document = True

extlinks = {"pypi": ("https://pypi.org/project/%s", "%s")}

copybutton_exclude = ".gp, .go"

intersphinx_mapping = {
    "python": ("http://docs.python.org/", None),
    "coredis": ("https://coredis.readthedocs.io/en/latest/", None),
    "memcachio": ("https://memcachio.readthedocs.io/en/latest/", None),
    "motor": ("https://motor.readthedocs.io/en/stable/", None),
    "redis-py-cluster": ("https://redis-py-cluster.readthedocs.io/en/latest/", None),
    "redis-py": ("https://redis-py.readthedocs.io/en/latest/", None),
    "pymemcache": ("https://pymemcache.readthedocs.io/en/latest/", None),
    "pymongo": ("https://pymongo.readthedocs.io/en/stable/", None),
    "valkey-py": ("https://valkey-py.readthedocs.io/en/latest/", None),
}
