"""
Cython compilation runner for scaldys-builder.

Invoked as a module by the build system::

    python -P -m scaldys_builder.common.compile_runner build_ext --build-lib <path>

Reads the list of modules to compile from ``builder.toml`` in the current
working directory (the consuming project's root).  If no modules are configured
or ``builder.toml`` is absent, exits immediately without error — fully
supporting pure-Python projects that have no Cython compilation step.

The ``--compiler=msvc`` flag is passed by the build system on Windows because
the MSVC compiler is required for CPython extension modules.  MinGW is not
supported for this purpose on Windows builds.
"""

import os
import sys
import tomllib
from pathlib import Path
from setuptools import setup, Extension, find_packages
from setuptools.dist import Distribution
from Cython.Build import cythonize
from Cython.Distutils.build_ext import build_ext


class BinaryDistribution(Distribution):
    """Distribution that always forces a binary package with a platform name."""

    def has_ext_modules(self) -> bool:
        return True


def _load_cython_config() -> tuple[list[str], str]:
    """
    Read ``compiled_modules`` and ``source_root`` from ``builder.toml`` in cwd.

    Returns
    -------
    compiled_modules : list of str
        Dotted module paths to compile.  Empty list if unconfigured.
    source_root : str
        Source directory relative to project root.  Defaults to ``"src"``.
    """
    config_file = Path.cwd() / "builder.toml"
    if not config_file.exists():
        return [], "src"
    with open(config_file, "rb") as f:
        data = tomllib.load(f)
    cython_cfg = data.get("cython", {})
    return (
        cython_cfg.get("compiled_modules", []),
        cython_cfg.get("source_root", "src"),
    )


def _get_extensions(compiled_modules: list[str], source_root: str) -> list[Extension]:
    extensions = []
    for module in compiled_modules:
        source_file = os.path.join(source_root, *module.split(".")) + ".py"
        extensions.append(Extension(module, sources=[source_file]))
    return extensions


if __name__ == "__main__":
    compiled_modules, source_root = _load_cython_config()

    if not compiled_modules:
        # Nothing to compile; pure-Python project or no modules declared.
        sys.exit(0)

    setup(
        name="__compile_runner__",
        cmdclass={"build_ext": build_ext},
        ext_modules=cythonize(
            _get_extensions(compiled_modules, source_root),
            annotate=False,
            language_level="3",
        ),
        package_dir={"": source_root},
        packages=find_packages(source_root),
        distclass=BinaryDistribution,
    )
