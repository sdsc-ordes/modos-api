# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = "modos-api"
copyright = "2024, sdsc-ordes"
author = "sdsc-ordes"
release = "0.3.5"

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    "sphinx.ext.napoleon",
    "sphinx.ext.doctest",
    "sphinx.ext.intersphinx",
    "sphinx.ext.autodoc",
    "sphinx.ext.coverage",
    "sphinx.ext.viewcode",
    "sphinx.ext.githubpages",
    "sphinx.ext.autosectionlabel",
    "autoapi.extension",
    "sphinx_click",
    "sphinx_design",
    "myst_parser",
]

templates_path = ["_templates"]

source_suffix = {
    ".rst": "restructuredtext",
    ".md": "markdown",
}


exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]


# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "pydata_sphinx_theme"
html_static_path = ["_static"]
html_logo = "img/modos.png"
html_favicon = "img/favicon.ico"


html_theme_options = {
    "github_url": "https://github.com/sdsc-ordes/modos-api",
    "collapse_navigation": True,
    "navigation_with_keys": False,
}


# -- Extension configuration -------------------------------------------------
# Options for myst
myst_enable_extensions = ["colon_fence"]


# Options for autoapi
autoapi_dirs = ["../src/modos"]
autoapi_ignore = ["*cli*"]
autodoc_typehints = "description"

# Options for intersphinx

intersphinx_mapping = {
    "python": ("https://docs.python.org/", None),
    "zarr": ("https://zarr.readthedocs.io/en/stable/", None),
}
