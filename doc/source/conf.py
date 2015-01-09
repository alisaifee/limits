# -*- coding: utf-8 -*-
#

import sys
import os

sys.path.insert(0, os.path.abspath('../../'))
import limits

on_rtd = os.environ.get('READTHEDOCS', None) == 'True'

if not on_rtd:  # only import and set the theme if we're building docs locally
    import sphinx_rtd_theme
    html_theme = 'sphinx_rtd_theme'
    html_theme_path = [sphinx_rtd_theme.get_html_theme_path()]


extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.intersphinx',
    'sphinx.ext.todo',
    'sphinx.ext.viewcode',
]

source_suffix = '.rst'
master_doc = 'index'
project = u'limits'
copyright = u'2015, Ali-Akber Saifee'

version = release = limits.__version__
exclude_patterns = []
pygments_style = 'sphinx'
htmlhelp_basename = 'limitsdoc'

latex_documents = [
    ('index', 'limits.tex', u'limits Documentation',
     u'Ali-Akber Saifee', 'manual'),
]
man_pages = [
    ('index', 'flask-limiter', u'limits Documentation',
     [u'Ali-Akber Saifee'], 1)
]

texinfo_documents = [
    ('index', 'limits', u'limits Documentation',
     u'Ali-Akber Saifee', 'limits', 'One line description of project.',
     'Miscellaneous'),
]

intersphinx_mapping = {'python': ('http://docs.python.org/', None)
}

autodoc_default_flags = [
    "members"
    , "show-inheritance"
]
