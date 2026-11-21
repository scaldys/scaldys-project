"""
Build configuration loader for scaldys-project.

Reads project-specific build settings from ``scaldys-project.toml`` in the project root.
If the file is absent, or a section is missing, all settings fall back to defaults —
so pure-Python projects with no Cython compilation and standard packaging layouts
require no configuration file at all.

In a uv workspace, the workspace root's ``scaldys-project.toml`` provides
defaults that the member's file is merged over (see :func:`load_config`).

Example ``scaldys-project.toml``::

    [cython]
    compiled_modules = [
        "myapp.core.engine",   # performance-critical
        "myapp.core.crypto",   # obfuscation
    ]

    [windows]
    script_dir = "packaging/windows"
    deployment_mode = "wheel_only"  # or "pyinstaller", "pyruntime"

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

        ``"pyinstaller"`` — the application is bundled into a
        standalone executable using PyInstaller.  No Python runtime is deployed
        alongside it.  A binary wheel is still built and placed in
        ``dist/`` for users who manage their own virtual environments.

        ``"pyruntime"`` — PyInstaller is skipped entirely.  Instead a binary
        wheel is built and the Inno Setup installer deploys a managed Python
        virtual environment (``PythonRuntime``) into the installation directory.
        The launcher scripts activate that environment rather than calling a
        frozen executable.  Use this mode when the application needs to
        coexist with tools such as Quarto that require a real Python interpreter.

        ``"wheel_only"`` (default) — Neither PyInstaller nor Inno Setup is used.  A
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
    exe_name : str or None
        Base name (without ``.exe``) of the executable produced by PyInstaller
        in ``pyinstaller`` mode.  ``None`` (default) uses the ``[project] name``
        from ``pyproject.toml``.  Set it when the command-line name differs
        from the distribution name (e.g. distribution ``trill-py``, command
        ``trill``).  Packaging file names (``.iss``, launchers, ``.ico``) are
        not affected and keep using the project name.
    """

    script_dir: str = "packaging/windows"
    deployment_mode: str = "wheel_only"
    bundle_pyruntime: bool = False
    exe_name: str | None = None


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
class FormatConfig:
    """
    Markdown and code formatting settings.

    Attributes
    ----------
    markdown_targets : list of str or None
        List of files and directories to format with mdformat.
        If None (default), auto-discovery applies (README.md + MkDocs docs).
        If empty list [], no markdown files are formatted.
    """

    markdown_targets: list[str] | None = None


@dataclass
class BuildConfig:
    """
    Complete build configuration for a consuming project.

    Populated from ``scaldys-project.toml``; any missing section uses its defaults.
    """

    cython: CythonConfig = field(default_factory=CythonConfig)
    windows: WindowsConfig = field(default_factory=WindowsConfig)
    docs: DocsConfig = field(default_factory=DocsConfig)
    format: FormatConfig = field(default_factory=FormatConfig)


def _read_toml(config_file: Path) -> dict:
    """Read *config_file*; an absent file reads as an empty table."""
    if not config_file.exists():
        return {}
    try:
        with open(config_file, "rb") as f:
            return tomllib.load(f)
    except tomllib.TOMLDecodeError as exc:
        raise RuntimeError(f"{config_file}: malformed TOML — {exc}") from exc


def _merge_config(root_data: dict, member_data: dict) -> dict:
    """
    Merge a member's configuration over the workspace root defaults.

    Each section is merged key by key: a key set in the member wins, any other
    key comes from the root.  ``[format]`` is workspace-wide and is always
    taken from the root.
    """
    merged: dict = {}
    for section in set(root_data) | set(member_data):
        if section == "format":
            continue
        root_section = root_data.get(section, {})
        member_section = member_data.get(section, {})
        if isinstance(root_section, dict) and isinstance(member_section, dict):
            merged[section] = {**root_section, **member_section}
        else:
            merged[section] = member_data.get(section, root_section)
    if "format" in root_data:
        merged["format"] = root_data["format"]
    return merged


def load_config(project_path: Path, workspace_root: Path | None = None) -> BuildConfig:
    """
    Load build configuration from ``scaldys-project.toml``.

    Parameters
    ----------
    project_path : Path
        Root directory of the consuming project (where ``scaldys-project.toml`` lives).
    workspace_root : Path, optional
        Root of the uv workspace that *project_path* belongs to.  When given
        and different from *project_path*, the root ``scaldys-project.toml``
        provides the defaults, the member file is merged over it section by
        section, and ``[format]`` is read from the root only.

    Returns
    -------
    BuildConfig
        Fully populated configuration.  Missing sections fall back to defaults.
    """
    config_file = project_path / "scaldys-project.toml"
    data = _read_toml(config_file)

    if workspace_root is not None and workspace_root.resolve() != project_path.resolve():
        root_file = workspace_root / "scaldys-project.toml"
        data = _merge_config(_read_toml(root_file), data)
        if not config_file.exists():
            config_file = root_file

    cython_data = data.get("cython", {})
    windows_data = data.get("windows", {})
    docs_data = data.get("docs", {})
    format_data = data.get("format", {})

    deployment_mode = windows_data.get("deployment_mode", "wheel_only")
    if deployment_mode not in ("pyinstaller", "pyruntime", "wheel_only"):
        raise RuntimeError(
            f"{config_file}: [windows] deployment_mode must be "
            f"'pyinstaller', 'pyruntime', or 'wheel_only', got '{deployment_mode}'"
        )

    exe_name = windows_data.get("exe_name")
    if exe_name is not None and (
        not isinstance(exe_name, str)
        or not exe_name.strip()
        or exe_name != exe_name.strip()
        or any(c in exe_name for c in '/\\:*?"<>|')
        or exe_name.lower().endswith(".exe")
    ):
        raise RuntimeError(
            f"{config_file}: [windows] exe_name must be a non-empty file base name "
            f"without path separators or '.exe' suffix, got {exe_name!r}"
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
            exe_name=exe_name,
        ),
        docs=DocsConfig(
            public_doc_dirs=docs_data.get("public_doc_dirs", []),
        ),
        format=FormatConfig(
            markdown_targets=format_data.get("markdown_targets", None),
        ),
    )
