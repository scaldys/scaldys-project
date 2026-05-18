"""
Build configuration loader for scaldys-project.

Reads project-specific build settings from ``scaldys-project.toml`` in the project root.
If the file is absent, or a section is missing, all settings fall back to defaults —
so pure-Python projects with no Cython compilation and standard packaging layouts
require no configuration file at all.

Example ``scaldys-project.toml``::

    [cython]
    compiled_modules = [
        "myapp.core.engine",   # performance-critical
        "myapp.core.crypto",   # obfuscation
    ]

    [windows]
    script_dir = "packaging/windows"
    deployment_mode = "pyinstaller"  # or "pyruntime"

    [docs]
    public_doc_dirs = ["manual"]
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
    deployment_mode : str
        Controls how the application is packaged for end-user distribution.

        ``"pyinstaller"`` (default) — the application is bundled into a
        standalone executable using PyInstaller.  No Python runtime is deployed
        alongside it.  A binary wheel is still built and placed in
        ``dist/`` for users who manage their own virtual environments.

        ``"pyruntime"`` — PyInstaller is skipped entirely.  Instead a binary
        wheel is built and the Inno Setup installer deploys a managed Python
        virtual environment (``PythonRuntime``) into the installation directory.
        The launcher scripts activate that environment rather than calling a
        frozen executable.  Use this mode when the application needs to
        coexist with tools such as Quarto that require a real Python interpreter.

        ``"wheel_only"`` — Neither PyInstaller nor Inno Setup is used.  A
        binary wheel is built and placed in ``dist/``.  No installer is
        produced.  Use this mode when end users install the application into
        their own Python environment via ``pip``/``uv pip install``.
    bundle_pyruntime : bool
        Only meaningful when ``deployment_mode = "pyruntime"``.

        When ``True``, the packager uses the bundled ``uv.exe`` to pre-build the
        ``PythonRuntime`` virtual environment at ``artifacts/pyruntime/`` and passes
        its path to Inno Setup via the ``/DPythonRuntimeDir`` preprocessor
        define.  The resulting ``setup.exe`` is an *offline* installer — no
        internet connection is needed at install time.

        When ``False`` (default), ``uv.exe`` is still bundled in ``bin/`` but
        the environment is created *online* by ``setup_pyruntime.ps1``
        during installation.
    """

    script_dir: str = "packaging/windows"
    deployment_mode: str = "pyinstaller"
    bundle_pyruntime: bool = False


@dataclass
class DocsConfig:
    """
    Documentation build settings.

    Attributes
    ----------
    public_doc_dirs : list of str
        Subdirectory names under ``docs/`` whose built HTML output is copied
        into distribution artifacts (PyInstaller dist + Inno Setup).
        An empty list means no documentation is distributed.
    """

    public_doc_dirs: list[str] = field(default_factory=list)


@dataclass
class BuildConfig:
    """
    Complete build configuration for a consuming project.

    Populated from ``scaldys-project.toml``; any missing section uses its defaults.
    """

    cython: CythonConfig = field(default_factory=CythonConfig)
    windows: WindowsConfig = field(default_factory=WindowsConfig)
    docs: DocsConfig = field(default_factory=DocsConfig)


def load_config(project_path: Path) -> BuildConfig:
    """
    Load build configuration from ``scaldys-project.toml``.

    Parameters
    ----------
    project_path : Path
        Root directory of the consuming project (where ``scaldys-project.toml`` lives).

    Returns
    -------
    BuildConfig
        Fully populated configuration.  Missing sections fall back to defaults.
    """
    config_file = project_path / "scaldys-project.toml"
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

    deployment_mode = windows_data.get("deployment_mode", "pyinstaller")
    if deployment_mode not in ("pyinstaller", "pyruntime", "wheel_only"):
        raise RuntimeError(
            f"{config_file}: [windows] deployment_mode must be "
            f"'pyinstaller', 'pyruntime', or 'wheel_only', got '{deployment_mode}'"
        )

    return BuildConfig(
        cython=CythonConfig(
            compiled_modules=cython_data.get("compiled_modules", []),
            source_root=cython_data.get("source_root", "src"),
        ),
        windows=WindowsConfig(
            script_dir=windows_data.get("script_dir", "packaging/windows"),
            deployment_mode=deployment_mode,
            bundle_pyruntime=windows_data.get("bundle_pyruntime", False),
        ),
        docs=DocsConfig(
            public_doc_dirs=docs_data.get("public_doc_dirs", []),
        ),
    )
