import os
import sys

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

sys.path.insert(0, ROOT_DIR)
sys.path.insert(1, os.path.abspath('.'))
os.environ['DJANGO_SETTINGS_MODULE'] = 'django_settings'
extensions = [
    'sphinx.ext.autodoc',
    'sphinx_autodoc_typehints',
    'sphinx.ext.autosummary',
    'sphinx.ext.coverage',
    'sphinx.ext.doctest',
    'sphinx.ext.extlinks',
    'sphinx.ext.ifconfig',
    'sphinx.ext.napoleon',
    'sphinx.ext.todo',
    'sphinx.ext.viewcode',
]
if os.getenv('SPELLCHECK'):
    extensions += 'sphinxcontrib.spelling',
    spelling_show_suggestions = True
    spelling_lang = 'en_US'

source_parsers = {
    '.md': 'recommonmark.parser.CommonMarkParser',
}

source_suffix = ['.rst', '.md']
master_doc = 'index'
project = 'django-docker-helpers'
year = '2018'
author = 'Igor Kalishevsky'
copyright = '{0}, {1}'.format(year, author)
version = release = '0.1.12'

pygments_style = 'trac'
templates_path = ['.']
extlinks = {
    'issue': ('https://github.com/night-crawler/django-docker-helpers/issues/%s', '#'),
    'pr': ('https://github.com/night-crawler/django-docker-helpers/pull/%s', 'PR #'),
}

html_theme = "sphinx_rtd_theme"
html_theme_path = ["_themes", ]
# html_theme_options = {
#     'githuburl': 'https://github.com/night-crawler/django-docker-helpers/'
# }

html_use_smartypants = True
html_last_updated_fmt = '%b %d, %Y'
html_split_index = False
html_sidebars = {
    '**': ['searchbox.html', 'globaltoc.html', 'sourcelink.html'],
}
html_short_title = '%s-%s' % (project, version)

napoleon_use_ivar = True
napoleon_use_rtype = False
napoleon_use_param = False

autoclass_content = 'both'

autodoc_default_flags = [
    'members',
    'private-members',
    'special-members',
    # 'undoc-members',
    'show-inheritance',
    # 'inherited-members'
]


def autodoc_skip_member(app, what, name, obj, skip, options):
    exclusions = (
        '__weakref__',  # special-members
        '__doc__', '__module__', '__dict__', '__init__',
    )
    exclude = name in exclusions
    return skip or exclude


def setup(app):
    app.connect('autodoc-skip-member', autodoc_skip_member)
