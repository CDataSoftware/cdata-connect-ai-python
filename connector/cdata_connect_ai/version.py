# Version is derived from git tags by setuptools-scm at build time.
# At runtime we read from installed package metadata (works for both
# regular installs and editable installs).  If the package is not
# installed at all (bare source checkout with no git tags) we fall
# back to the _version.py that setuptools-scm writes during `python -m build`.
try:
    from importlib.metadata import version, PackageNotFoundError
    __version__ = version("cdata-connect-ai")
except PackageNotFoundError:
    try:
        from cdata_connect_ai._version import __version__  # generated at build time
    except ImportError:
        __version__ = "0.0.0+unknown"
