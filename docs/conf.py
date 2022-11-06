# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# http://www.sphinx-doc.org/en/master/config

from __future__ import annotations

import datetime
import pathlib
import sys

# -- Path setup --------------------------------------------------------------
# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
# import os
# import sys
# sys.path.insert(0, os.path.abspath('.'))


# -- Project information -----------------------------------------------------
project = "PyPIToken"
copyright = f"2021-{datetime.datetime.now().year}, Joachim Jablon"
author = "Joachim Jablon"

# -- General configuration ---------------------------------------------------
sys.path.append(str(pathlib.Path("sphinxext").absolute()))

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    "sphinx.ext.napoleon",
    "sphinx.ext.autodoc",
    "sphinx_github_changelog",
]

# Add any paths that contain templates here, relative to this directory.
templates_path = ["_templates"]

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

# When a word is enclosed between `backticks`, the role will automatically be
# inferred. It can be set explicitely if ambiguous.
default_role = "any"

# If we don't do that, glossary checks are case sensitive.
# https://github.com/sphinx-doc/sphinx/issues/7418
suppress_warnings = ["ref.term"]

# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = "sphinx_material"

html_sidebars = {
    "**": ["logo-text.html", "globaltoc.html", "localtoc.html", "searchbox.html"]
}

html_logo = "macaroon.png"
html_logo_text = "macaroon by Izwar Muis from the Noun Project"
html_favicon = "favicon.ico"

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
# html_static_path = ["_static"]

html_theme_options = {
    # Set the name of the project to appear in the navigation.
    "nav_title": "PyPIToken",
    # Specify a base_url used to generate sitemap.xml. If not
    # specified, then no sitemap will be built.
    "base_url": "https://pypitoken.readthedocs.io/",
    # Set the color and the accent color
    "color_primary": "indigo",
    "color_accent": "light-blue",
    # Set the repo location to get a badge with stats
    "repo_url": "https://github.com/ewjoachim/pypitoken",
    "repo_name": "PyPIToken",
    # Visible levels of the global TOC; -1 means unlimited
    "globaltoc_depth": 2,
    # If False, expand all TOC entries
    "globaltoc_collapse": False,
    # If True, show hidden TOC entries
    "globaltoc_includehidden": False,
}
