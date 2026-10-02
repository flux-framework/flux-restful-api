"""
The package version, from the installed distribution or the VERSION file
in a source checkout.
"""

import os
from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("flux-restful")
except PackageNotFoundError:
    _version_file = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "VERSION"
    )
    try:
        with open(_version_file) as fd:
            __version__ = fd.read().strip()
    except OSError:
        __version__ = "0.0.0"
