"""
Build configuration loader for scaldys-builder.

Reads project-specific build settings from ``builder.toml`` in the project root.
If the file is absent, or a section is missing, all settings fall back to defaults —
so pure-Python projects with no Cython compilation and standard packaging layouts
require no configuration file at all.

Example ``builder.toml``::

    [cython]
    compiled_modules = [
        "myapp.core.engine",   # performance-critical
        "myapp.core.crypto",   # obfuscation
    ]

    [windows]
    script_dir = "packaging/windows"

    [docs]
    dist_dirs = ["manual"]
    apidoc_dirs = ["developer_guide"]
"""

import tomllib
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class CythonConfig:
    """
    Cython compilation settings.

    Attributes
    ----------
    compiled_modules : list of str
        Dotted module paths to compile with Cython (e.g. ``"myapp.core.engine"``).
        An empty list disables Cython; source files are staged as-is for PyInstaller.
    source_root : str
        Directory (relative to project root) containing Python source packages.
        Defaults to ``"src"``.
    """

    compiled_modules: list[str] = field(default_factory=list)
    source_root: str = "src"


@dataclass
class WindowsConfig:
    """
    Windows packaging settings.

    Attributes
    ----------
    script_dir : str
        Directory (relative to project root) containing Windows packaging files:
        the Inno Setup script (``.iss``), launcher scripts (``.bat``, ``.ps1``),
        and application icon (``.ico``).  Defaults to ``"packaging/windows"``.
    """

    script_dir: str = "packaging/windows"


@dataclass
class DocsConfig:
    """
    Documentation build settings.

    Attributes
    ----------
    dist_dirs : list of str
        Subdirectory names under ``docs/`` whose built HTML output is copied
        into distribution artifacts (PyInstaller dist + Inno Setup).
        An empty list means no documentation is distributed.
    apidoc_dirs : list of str
        Subdirectory names that require a ``sphinx-apidoc`` pre-pass before
        ``sphinx-build`` is invoked.  Must be a subset of the Sphinx directories
        (i.e. those containing ``source/conf.py``).
    """

    dist_dirs: list[str] = field(default_factory=list)
    apidoc_dirs: list[str] = field(default_factory=list)


@dataclass
class BuildConfig:
    """
    Complete build configuration for a consuming project.

    Populated from ``builder.toml``; any missing section uses its defaults.
    """

    cython: CythonConfig = field(default_factory=CythonConfig)
    windows: WindowsConfig = field(default_factory=WindowsConfig)
    docs: DocsConfig = field(default_factory=DocsConfig)


def load_config(project_path: Path) -> BuildConfig:
    """
    Load build configuration from ``builder.toml``.

    Parameters
    ----------
    project_path : Path
        Root directory of the consuming project (where ``builder.toml`` lives).

    Returns
    -------
    BuildConfig
        Fully populated configuration.  Missing sections fall back to defaults.
    """
    config_file = project_path / "builder.toml"
    if not config_file.exists():
        return BuildConfig()

    try:
        with open(config_file, "rb") as f:
            data = tomllib.load(f)
    except tomllib.TOMLDecodeError as exc:
        raise RuntimeError(f"{config_file}: malformed TOML — {exc}") from exc

    cython_data = data.get("cython", {})
    windows_data = data.get("windows", {})
    docs_data = data.get("docs", {})

    return BuildConfig(
        cython=CythonConfig(
            compiled_modules=cython_data.get("compiled_modules", []),
            source_root=cython_data.get("source_root", "src"),
        ),
        windows=WindowsConfig(
            script_dir=windows_data.get("script_dir", "packaging/windows"),
        ),
        docs=DocsConfig(
            dist_dirs=docs_data.get("dist_dirs", []),
            apidoc_dirs=docs_data.get("apidoc_dirs", []),
        ),
    )
