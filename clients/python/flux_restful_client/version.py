__version__ = "0.2.1"
AUTHOR = "Vanessa Sochat"
EMAIL = "vsoch@users.noreply.github.com"
NAME = "flux-restful-client"
PACKAGE_URL = (
    "https://github.com/flux-framework/flux-restful-api/tree/main/clients/python"
)
KEYWORDS = "flux, flux framework, client, RESTFul API"
DESCRIPTION = "Python functions and command line equivalent for interacting with Flux RESTful API."
LICENSE = "LICENSE"

################################################################################
# Global requirements

INSTALL_REQUIRES = (
    # Required to maintain comments in files
    ("ruamel.yaml", {"min_version": None}),
    ("httpx", {"min_version": None}),
    ("jsonschema", {"min_version": None}),
    ("python-jose[cryptography]", {"min_version": None}),
)

TESTS_REQUIRES = (("pytest", {"min_version": "4.6.2"}),)
INSTALL_REQUIRES_ALL = INSTALL_REQUIRES + TESTS_REQUIRES
