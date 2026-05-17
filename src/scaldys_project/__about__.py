# -*- coding: utf-8 -*-

__all__ = [
    "APP_NAME",
    "PACKAGE_NAME",
    "ORGANIZATION_NAME",
    "VERSION",
]

from importlib.metadata import version, PackageNotFoundError

APP_NAME = "Scaldys Builder"
PACKAGE_NAME = "scaldys-project"
ORGANIZATION_NAME = "Scaldys"

try:
    VERSION = version(PACKAGE_NAME)
except PackageNotFoundError:
    VERSION = "0.0.0"
