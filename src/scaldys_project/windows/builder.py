"""
Windows build orchestration for scaldys-project.

Provides three focused classes that compose into a complete Windows distribution
pipeline:

- ``WindowsBuildEnvironment`` — discovers tools, resolves paths, runs pre-flight
  checks.
- ``Compiler`` — stages source files and optionally compiles selected modules
  with Cython, then bundles everything into a standalone executable via
  PyInstaller.
- ``Packager`` — assembles the distribution layout (examples, helper scripts,
  documentation) and produces an Inno Setup installer.

``WindowsBuilder`` ties them together and exposes both individual step methods
and a ``main()`` entry point for the complete end-to-end workflow.
"""

import logging
import os
import re
import shutil
import tomllib
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from packaging.version import InvalidVersion, Version

from scaldys_project.common.base import BaseBuildEnvironment, BaseBuilder
from scaldys_project.common.docs import DocEngine, DocumentationBuilder, _detect_engine
from scaldys_project.common.utils import (
    safe_copy,
    safe_copytree,
    safe_empty_dir,
    safe_rename,
    safe_rmtree,
    safe_unlink,
)
from scaldys_project.common.workspace import Member

logger = logging.getLogger(__name__)

# Wheels built during this process, keyed by member directory.  One CLI run
# builds each workspace member at most once, even when several apps of an
# ``--all-packages`` build depend on it.
_BUILT_WHEELS: dict[Path, Path] = {}


def reset_built_wheels() -> None:
    """Forget the wheels built so far in this process (used by tests)."""
    _BUILT_WHEELS.clear()


# A TOML table header: [a.b] or [[a.b]], optionally followed by a comment.
_TOML_HEADER_RE = re.compile(r"^\s*(\[\[?)\s*([^\[\]]+?)\s*(\]\]?)\s*(?:#.*)?$")
# Quoted TOML strings, removed before counting brackets on a line.
_TOML_STRING_RE = re.compile(r'"(?:[^"\\]|\\.)*"|' + r"'[^']*'")


def _normalize_toml_key(key: str) -> str:
    """Return a dotted TOML key without whitespace around dots or quotes on parts."""
    parts = [part.strip().strip('"').strip("'") for part in key.split(".")]
    return ".".join(parts)


def _remove_toml_sections(text: str, *section_headers: str) -> str:
    """Return *text* with the named TOML table sections (and their keys) removed.

    Each *section_header* should be the bare header string, e.g.
    ``"tool.setuptools.packages.find"``.  A header also removes its dotted
    sub-tables (``"tool.uv.sources"`` removes ``[tool.uv.sources.x]``) and
    arrays of tables (``[[tool.uv.index]]``).  A section extends from its
    header line up to the next table header or the end of the file.  Lines
    inside a multi-line array that start with ``[`` are not mistaken for
    headers.
    """
    prefixes = [_normalize_toml_key(h) for h in section_headers]

    def is_removed(name: str) -> bool:
        return any(name == p or name.startswith(p + ".") for p in prefixes)

    out: list[str] = []
    skipping = False
    depth = 0  # open-bracket depth of a multi-line value
    for line in text.splitlines(keepends=True):
        if depth == 0:
            header = _TOML_HEADER_RE.match(line)
            if header and len(header.group(1)) == len(header.group(3)):
                skipping = is_removed(_normalize_toml_key(header.group(2)))
                if not skipping:
                    out.append(line)
                continue
        code = _TOML_STRING_RE.sub("", line).split("#", 1)[0]
        depth = max(
            0, depth + code.count("[") + code.count("{") - code.count("]") - code.count("}")
        )
        if not skipping:
            out.append(line)
    return "".join(out)


class WindowsBuildEnvironment(BaseBuildEnvironment):
    """
    Windows-specific build environment.

    Discovers tools like Inno Setup and PyInstaller, and manages paths
    specific to the Windows build process.
    """

    def __init__(self, project_path: Path, verbose: bool = False) -> None:
        """
        Initialize the Windows build environment.

        Parameters
        ----------
        project_path : Path
            The root directory of the project.
        verbose : bool, default False
            If True, enables verbose output.
        """
        super().__init__(project_path, verbose)

        self.program_files_dir_path = Path(os.getenv("PROGRAMFILES") or "C:\\Program Files")
        self.program_files_x86_dir_path = Path(
            os.getenv("PROGRAMFILES(x86)") or "C:\\Program Files (x86)"
        )

        # Discovery of executables
        self.pyinstaller_exe_path = self._find_tool("pyinstaller.exe", self.python_dir_path)
        self.innosetup_exe_path = self._find_tool(
            "ISCC.exe", self.program_files_x86_dir_path.joinpath("Inno Setup 6")
        )

        # Windows packaging files (.iss, .bat, .ps1, .ico) live in the directory
        # specified by scaldys-project.toml [windows] script_dir (default: packaging/windows).
        self.script_dir_path = (self.project_path / self.config.windows.script_dir).resolve()
        self.win32_icon_file_path = self.script_dir_path.joinpath(f"{self.project_name}.ico")

        self.src_compiled_dir_path = self.build_dir_path.joinpath("compiled")
        self.examples_dir_path = self.project_path.joinpath("examples")
        self.dist_exe_dir_path = self.artifacts_dir_path.joinpath("portable")
        self.dist_wheels_dir_path = self.dist_dir_path
        self.dist_setup_dir_path = self.artifacts_dir_path.joinpath("installer")
        # Wheels of internal workspace dependencies, collected for the installer.
        # Not dist/: publish refuses more than one binary wheel there.
        self.internal_wheels_dir_path = self.build_dir_path.joinpath("internal_wheels")

    def internal_closure(self) -> list[Member]:
        """
        Return the workspace members this project depends on, libraries first.

        Empty for a standalone project or a member without internal dependencies.
        """
        member = self.workspace_member
        if self.workspace is None or member is None:
            return []
        return [self.workspace.members[k] for k in self.workspace.internal_closure(member.name)]

    def _check_internal_constraints(self) -> list[str]:
        """
        Check the version constraints on internal workspace dependencies.

        A dependency without a constraint produces a warning.  A constraint that
        the dependency's current version does not satisfy is returned as an issue.
        """
        member = self.workspace_member
        if self.workspace is None or member is None or not member.internal_deps:
            return []
        issues: list[str] = []
        for key, spec in member.internal_deps.items():
            dep = self.workspace.members[key]
            if spec is None:
                logger.warning(
                    f"  [yellow]\u26a0[/yellow] Internal dependency '{dep.name}' has no version "
                    f"constraint; consider '{dep.name}>={dep.version}'."
                )
                continue
            try:
                ok = spec.contains(Version(dep.version), prereleases=True)
            except InvalidVersion:
                ok = False
            if not ok:
                issues.append(
                    f"Internal dependency constraint '{dep.name}{spec}' is not met by the "
                    f"workspace version {dep.version!r}."
                )
        if not issues:
            logger.info("  [green]\u2713[/green] Internal workspace dependency constraints")
        return issues

    def pre_flight_checks(
        self,
        require_sphinx: bool = False,
        require_pyinstaller: bool = False,
        require_innosetup: bool = False,
    ) -> None:
        """
        Verify that all required tools are available before starting.

        Parameters
        ----------
        require_sphinx : bool, default False
            Whether Sphinx is required.
        require_pyinstaller : bool, default False
            Whether PyInstaller is required.
        require_innosetup : bool, default False
            Whether Inno Setup is required.

        Raises
        ------
        RuntimeError
            If any required tool is missing.
        """
        logger.info("[bold]Running pre-flight checks...[/bold]")

        missing = []
        if require_sphinx:
            if self.sphinx_exe_path.exists():
                logger.info(
                    f"  [green]\u2713[/green] Sphinx found at [green]'{self.sphinx_exe_path}'[/green]"
                )
            else:
                missing.append(f"Sphinx (sphinx-build.exe) at {self.sphinx_exe_path}")
        if require_pyinstaller:
            if self.pyinstaller_exe_path.exists():
                logger.info(
                    f"  [green]\u2713[/green] PyInstaller found at [green]'{self.pyinstaller_exe_path}'[/green]"
                )
            else:
                missing.append(f"PyInstaller (pyinstaller.exe) at {self.pyinstaller_exe_path}")
        if require_innosetup:
            if self.innosetup_exe_path.exists():
                logger.info(
                    f"  [green]\u2713[/green] Inno Setup found at [green]'{self.innosetup_exe_path}'[/green]"
                )
            else:
                missing.append(f"Inno Setup (ISCC.exe) at {self.innosetup_exe_path}")

        if missing:
            logger.error("[bold red]Missing required tools:[/bold red]")
            for item in missing:
                logger.error(f"  - {item}")
            raise RuntimeError("Pre-flight checks failed.")

    def check_compliance(
        self,
        require_exe: bool = False,
        require_installer: bool = False,
    ) -> None:
        """
        Verify that the target project has the required structure for scaldys-project.

        Checks project-level files, layout, and environment — not tool
        availability (use ``pre_flight_checks`` for that).  All issues are
        collected and reported together so the user can fix everything in one
        pass.

        Parameters
        ----------
        require_exe : bool, default False
            Check that the package entry point exists
            (``{source_root}/{package}/__main__.py``).
        require_installer : bool, default False
            Check that the Inno Setup script and launcher scripts exist in the
            Windows packaging directory.

        Raises
        ------
        SystemExit
            If any compliance issues are found.
        """
        logger.info("[bold]Checking project compliance...[/bold]")

        issues: list[str] = []

        # Always: source root and package directory must exist.
        pkg_dir = self.src_dir_path / self.project_package_name
        layout_ok = True
        if not self.src_dir_path.is_dir():
            issues.append(f"Source root directory not found: '{self.config.cython.source_root}/'")
            layout_ok = False
        elif not pkg_dir.is_dir():
            issues.append(
                f"Package directory not found: "
                f"'{self.config.cython.source_root}/{self.project_package_name}/'"
            )
            layout_ok = False

        if layout_ok:
            logger.info("  [green]\u2713[/green] Source root and package layout")
            # Libraries (wheel_only) have no entry point; only apps need __main__.py.
            if require_exe and self.config.windows.deployment_mode != "wheel_only":
                # Only check __main__.py when the package dir exists (avoids duplicate noise).
                main_py = pkg_dir / "__main__.py"
                if not main_py.exists():
                    issues.append(
                        f"Package entry point not found: "
                        f"'{self.config.cython.source_root}/{self.project_package_name}/__main__.py'"
                    )
                else:
                    logger.info("  [green]\u2713[/green] Package entry point (__main__.py)")

        # .python-version is always required: it is the single source of truth
        # for the Python version used by the build and the PythonRuntime setup.
        if not self.python_version_file_path.exists():
            issues.append(
                ".python-version not found in project root"
                + (" or workspace root" if self.workspace else "")
                + ". "
                "Create it with the target Python version (e.g. '3.13')."
            )
        else:
            logger.info("  [green]\u2713[/green] Python version configuration (.python-version)")

        # In pyinstaller mode the hook calls copy_metadata() to bundle dist-info
        # into the frozen executable so that importlib.metadata.version() works at
        # runtime.  copy_metadata() requires the package to be installed in the
        # active virtual environment.  A missing dist-info produces a cryptic
        # StopIteration deep inside PyInstaller; catch it here instead.
        if self.config.windows.deployment_mode == "pyinstaller":
            import importlib.metadata as _meta

            # The internal dependencies are bundled with --copy-metadata too.
            missing_dists = []
            for dist_name in [self.project_name, *(m.name for m in self.internal_closure())]:
                try:
                    _meta.distribution(dist_name)
                except _meta.PackageNotFoundError:
                    missing_dists.append(dist_name)
            if not missing_dists:
                logger.info("  [green]\u2713[/green] Package installation in virtual environment")
            elif self.workspace:
                issues.append(
                    f"Package(s) {', '.join(repr(d) for d in missing_dists)} not installed in "
                    f"the active virtual environment (no dist-info found). In a uv workspace, "
                    f"run 'uv sync --all-packages', or add the members to the root dev "
                    f"dependency group, and retry."
                )
            else:
                issues.append(
                    f"Package '{self.project_name}' is not installed in the active virtual "
                    f"environment (no dist-info found). Run 'uv sync' (or 'pip install -e .') "
                    f"and retry."
                )

        issues.extend(self._check_internal_constraints())

        if require_installer:
            if not self.script_dir_path.is_dir():
                issues.append(
                    f"Windows packaging directory not found: '{self.config.windows.script_dir}/'"
                )
            else:
                all_files_exist = True
                for fname in [
                    f"{self.project_name}.iss",
                    f"{self.project_name}_commandline.bat",
                    f"{self.project_name}_powershell.ps1",
                ]:
                    if not self.script_dir_path.joinpath(fname).exists():
                        issues.append(
                            f"Required packaging file not found: "
                            f"'{self.config.windows.script_dir}/{fname}'"
                        )
                        all_files_exist = False
                if all_files_exist:
                    logger.info("  [green]\u2713[/green] Windows packaging scripts and ISS file")

        # Tests directory must exist at project root.
        tests_dir = self.project_path / "tests"
        if not tests_dir.is_dir():
            issues.append(
                "Tests directory not found: 'tests/'. Create it and add at least one test file."
            )
        else:
            logger.info("  [green]\u2713[/green] Tests directory")

        # Cython pre-flight: match/case not supported (PEP 634)
        match_issues = self.validate_cython_modules()
        if match_issues:
            issues.append(
                "match/case is not fully supported yet in cython. Replace it with an equivalent if-elif-else structure. "
                f"Concerned files: {', '.join(match_issues)}"
            )
        elif self.config.cython.compiled_modules:
            logger.info(
                "  [green]\u2713[/green] Cython modules syntax compatibility (no match/case)"
            )

        if issues:
            logger.error(
                f"[bold red]Project compliance check failed — "
                f"{len(issues)} issue(s) must be resolved before building:[/bold red]"
            )
            for issue in issues:
                logger.error(f"  [red]\u2717[/red] {issue}")
            logger.error(
                'For details on each requirement, see "Project Compliance" '
                "in the documentation (In-Depth Guides \u2192 Project Compliance)."
            )
            raise SystemExit(1)


class Compiler:
    """Handles Cython compilation and PyInstaller bundling on Windows."""

    def __init__(self, env: WindowsBuildEnvironment) -> None:
        """
        Initialize the compiler.

        Parameters
        ----------
        env : WindowsBuildEnvironment
            The Windows build environment.
        """
        self.env = env

    def run_cython(self) -> None:
        """
        Stage source files and optionally compile selected modules with Cython.

        If ``scaldys-project.toml`` declares no ``compiled_modules``, the Cython step
        is skipped and all source files are staged as-is.

        Raises
        ------
        RuntimeError
            If the Cython build command fails.
        """
        logger.info("[bold]Running Cython compilation stage...[/bold]")
        src_path = self.env.src_dir_path
        compiled_path = self.env.src_compiled_dir_path

        # 1. Clean and prepare staging directory
        safe_empty_dir(compiled_path)

        compiled_py_files: set[str] = set()

        # 2. Run Cython compilation if modules are declared in scaldys-project.toml
        if self.env.config.cython.compiled_modules:
            # Pre-flight check: match/case not supported (PEP 634)
            match_issues = self.env.validate_cython_modules()
            if match_issues:
                logger.info(
                    "[bold yellow]match/case is not fully supported yet in cython[/bold yellow]. Replace it with an equivalent if-elif-else structure."
                )
                for issue in match_issues:
                    logger.info(f"  [yellow]\u25ba[/yellow] Concerned file: {issue}")
                raise RuntimeError(
                    "Cython compilation aborted due to unsupported syntax (match/case)."
                )

            logger.info("  [green]\u25ba[/green] Compiling modules with Cython...")
            # -P disables adding cwd to sys.path (security/reproducibility).
            # --compiler=msvc is required for CPython extensions on Windows.
            cmd = [
                str(self.env.python_exe_path),
                "-P",
                "-m",
                "scaldys_project.common.compile_runner",
                "build_ext",
                "--build-lib",
                str(compiled_path),
                "--compiler=msvc",
            ]
            self.env.run_command(cmd, "Error running Cython build", cwd=self.env.project_path)

            # 3. Identify which modules were compiled to .pyd so their .py
            #    source files are excluded from the staging copy below.
            for pyd in compiled_path.rglob("*.pyd"):
                rel_pyd = pyd.relative_to(compiled_path)
                # Strip the platform suffix (e.g. .cp313-win_amd64) from the stem.
                name = rel_pyd.name.split(".")[0]
                py_rel_path = rel_pyd.with_name(f"{name}.py")
                compiled_py_files.add(str(py_rel_path))
        else:
            logger.info(
                "  [green]\u25ba[/green] No compiled_modules declared. Staging source files only."
            )

        # 4. Copy remaining source files from src to the staging area.
        #    Excludes .py files already present as .pyd and common build artefacts.
        def ignore_logic(directory: str | Path, contents: list[str]) -> Iterable[str]:
            ignored = []
            dir_path = Path(directory)
            try:
                rel_dir = dir_path.relative_to(src_path)
            except ValueError:
                return []

            for name in contents:
                full_rel_path = rel_dir.joinpath(name)
                # Ignore common junk and build artifacts
                if (
                    name == "__pycache__"
                    or name.endswith((".pyc", ".pyo", ".c", ".html", ".obj", ".lib", ".exp"))
                    or str(full_rel_path) in compiled_py_files
                ):
                    ignored.append(name)
            return ignored

        logger.info("  [green]\u25ba[/green] Collecting remaining source files to staging area...")
        safe_copytree(src_path, compiled_path, ignore=ignore_logic, dirs_exist_ok=True)

        # 5. Clean up .c files generated by Cython in the source tree.
        if self.env.config.cython.compiled_modules:
            logger.info("  [green]\u25ba[/green] Cleaning up lingering .c files in src...")
            for c_file in src_path.rglob("*.c"):
                safe_unlink(c_file)

    def run_pyinstaller(self) -> None:
        """
        Run PyInstaller to bundle the staged sources into a standalone executable.

        Notes
        -----
        UPX compression is disabled (``--noupx``) because UPX-packed binaries
        trigger false-positive detections in some Windows antivirus products.

        Raises
        ------
        RuntimeError
            If the PyInstaller command fails.
        """
        logger.info("[bold]Running PyInstaller...[/bold]")

        entry_point = self.env.src_compiled_dir_path.joinpath(
            f"{self.env.project_package_name}", "__main__.py"
        )
        hooks_dir = self.env.project_path.joinpath("packaging", "hooks")
        if not hooks_dir.exists():
            hooks_dir = self.env.src_compiled_dir_path.joinpath("extra_hooks")

        # Internal workspace dependencies: their staged build/compiled/ trees go
        # ahead of the app's own on the search path, so PyInstaller picks the
        # staged (possibly Cython-compiled) copy over the editable install.
        closure = self.env.internal_closure()
        dep_paths: list[str] = []
        for dep in closure:
            dep_paths += ["--paths", str(dep.path / "build" / "compiled")]

        cmd = [
            str(self.env.pyinstaller_exe_path),
            "--noconfirm",
            "--clean",
            "--onedir",
            "--console",
            "--name",
            self.env.exe_name,
            *dep_paths,
            "--paths",
            str(self.env.src_compiled_dir_path),
            "--distpath",
            str(self.env.dist_exe_dir_path),
            "--workpath",
            str(self.env.build_dir_path.joinpath("pyinstaller")),
            "--specpath",
            str(self.env.build_dir_path),
            "--collect-submodules",
            self.env.project_package_name,
            "--noupx",  # UPX disabled: causes false-positive AV detections on some systems
        ]

        if hooks_dir.exists():
            cmd.extend(["--additional-hooks-dir", str(hooks_dir)])

        for dep in closure:
            # Plugins load through entry points, which PyInstaller's analysis
            # cannot follow: collect every submodule, and copy the dist-info so
            # importlib.metadata.entry_points() and version() work when frozen.
            cmd.extend(["--collect-submodules", dep.package_name])
            cmd.extend(["--copy-metadata", dep.name])
            dep_hooks = dep.path / "packaging" / "hooks"
            if dep_hooks.is_dir():
                cmd.extend(["--additional-hooks-dir", str(dep_hooks)])

        if self.env.win32_icon_file_path.exists():
            cmd.extend(["--icon", str(self.env.win32_icon_file_path)])

        cmd.append(str(entry_point))

        self.env.run_command(cmd, "Error running PyInstaller", cwd=self.env.project_path)

        # Post-build: Rename the application directory to 'bin' for a cleaner
        # distribution structure.
        pkg_dir = self.env.dist_exe_dir_path.joinpath(self.env.exe_name)
        bin_dir = self.env.dist_exe_dir_path.joinpath("bin")
        if pkg_dir.exists():
            safe_rmtree(bin_dir)
            safe_rename(pkg_dir, bin_dir)

    def _build_wheel(self) -> Path:
        """
        Build a distribution wheel from the compiled staging area.

        Copies ``pyproject.toml`` into ``build/compiled/`` so that setuptools
        can discover the package (which is at the root of the staging tree,
        not under ``src/``), then runs ``uv build --wheel``.  The resulting
        ``.whl`` file — containing the compiled ``.pyd`` extensions but no
        Python source files — is written to ``dist/``.

        In ``pyinstaller`` mode this wheel is available for users who manage
        their own virtual environments.  In ``pyruntime`` mode the packager
        additionally stages it into ``artifacts/portable/wheels/`` so that Inno
        Setup includes it in the installer and ``setup_pyruntime.ps1`` can
        install it into the PythonRuntime via ``uv pip install --find-links``.

        The staged ``pyproject.toml`` has its uv-only tables
        (``tool.uv.sources``, ``tool.uv.workspace``, ``tool.uv.index``)
        removed and the build runs with ``--no-sources``, so a workspace
        member builds exactly like a standalone project.

        Returns
        -------
        Path
            The wheel that was built.

        Raises
        ------
        RuntimeError
            If ``uv`` is not found or the build command fails.
        """
        uv_exe = shutil.which("uv")
        if not uv_exe:
            raise RuntimeError("uv not found in PATH. Cannot build the distribution wheel.")

        compiled_path = self.env.src_compiled_dir_path
        wheels_dir = self.env.dist_wheels_dir_path
        wheels_dir.mkdir(parents=True, exist_ok=True)

        # Place pyproject.toml alongside the compiled package so that the build
        # backend (setuptools) can discover it in the flat layout of build/compiled/.
        dest_pyproject = compiled_path / "pyproject.toml"
        safe_copy(self.env.project_path / "pyproject.toml", dest_pyproject)

        # Copy the readme file referenced in pyproject.toml so that setuptools
        # can embed its contents as the package description when building the wheel.
        # Without this, setuptools silently omits the description and PyPI shows
        # "The author of this package has not provided a project description".
        with open(self.env.project_path / "pyproject.toml", "rb") as _f:
            _pyproject_meta = tomllib.load(_f)
        _readme = _pyproject_meta.get("project", {}).get("readme")
        if isinstance(_readme, str) and _readme:
            _readme_src = self.env.project_path / _readme
            if _readme_src.exists():
                safe_copy(_readme_src, compiled_path / _readme)
        elif isinstance(_readme, dict) and _readme.get("file"):
            _readme_src = self.env.project_path / _readme["file"]
            if _readme_src.exists():
                safe_copy(_readme_src, compiled_path / _readme["file"])

        # Copy the license files: setuptools resolves [project] license-files
        # globs (and a legacy license = {file = ...}) relative to the staged
        # pyproject.toml, and fails or omits them when they are missing.
        for _license_file in self._license_files(_pyproject_meta.get("project", {})):
            _license_dest = compiled_path / _license_file.relative_to(self.env.project_path)
            _license_dest.parent.mkdir(parents=True, exist_ok=True)
            safe_copy(_license_file, _license_dest)

        # Restrict setuptools package discovery to the project package only.
        # build/compiled/ contains extra_hooks/ (PyInstaller hooks) alongside the
        # package directory, and setuptools flat-layout auto-discovery refuses to
        # proceed when it finds more than one top-level package.
        #
        # Strip any existing copies of these sections before appending so that we
        # don't produce duplicate TOML table headers when the source pyproject.toml
        # already defines them (which would cause a parse error).
        text = dest_pyproject.read_text(encoding="utf-8")
        text = _remove_toml_sections(
            text,
            "tool.setuptools.packages.find",
            "tool.setuptools.package-data",
            # uv-only tables: workspace sources cannot resolve from build/compiled/.
            "tool.uv.sources",
            "tool.uv.workspace",
            "tool.uv.index",
        )
        text = text.rstrip() + (
            "\n\n"
            "[tool.setuptools.packages.find]\n"
            f'include = ["{self.env.project_package_name}*"]\n'
            "\n"
            "[tool.setuptools.package-data]\n"
            '"*" = ["*.pyd"]\n'
        )
        dest_pyproject.write_text(text, encoding="utf-8")

        # Write a setup.py that forces setuptools to tag the wheel as platform-specific.
        # Without this, setuptools sees no ext_modules being compiled at build time
        # (the .pyd is pre-built) and falls back to the pure-Python tag py3-none-any,
        # which is incorrect for a wheel containing compiled extensions.
        # Only inject this when compiled_modules are declared; a pure-Python build
        # must produce the standard py3-none-any tag.
        setup_py = compiled_path / "setup.py"
        if self.env.config.cython.compiled_modules:
            setup_py.write_text(
                "from setuptools import setup\n"
                "from setuptools.dist import Distribution\n\n"
                "class BinaryDistribution(Distribution):\n"
                "    def has_ext_modules(self):\n"
                "        return True\n\n"
                "setup(distclass=BinaryDistribution)\n",
                encoding="utf-8",
            )
        else:
            # Ensure no stale setup.py from a previous build forces a binary tag.
            safe_unlink(setup_py)

        logger.info("[bold]Building distribution wheel from compiled sources...[/bold]")
        self.env.run_command(
            [uv_exe, "build", "--wheel", "--no-sources", "--out-dir", str(wheels_dir)],
            "Failed to build the distribution wheel",
            cwd=compiled_path,
        )
        logger.info(f"  [green]\u2713[/green] Wheel written to '{wheels_dir}'")
        return self._find_wheel(wheels_dir)

    def _license_files(self, project: dict[str, Any]) -> list[Path]:
        """Return the files that ``[project] license-files`` (or ``license.file``) names."""
        root = self.env.project_path
        files: list[Path] = []
        for pattern in project.get("license-files", []) or []:
            files.extend(p for p in sorted(root.glob(pattern)) if p.is_file())
        license_meta = project.get("license")
        if isinstance(license_meta, dict) and license_meta.get("file"):
            candidate = root / license_meta["file"]
            if candidate.is_file():
                files.append(candidate)
        unique: list[Path] = []
        for f in files:
            if f not in unique and f.resolve().is_relative_to(root):
                unique.append(f)
        return unique

    def _find_wheel(self, wheels_dir: Path) -> Path:
        """Return the newest wheel for this project's name and version in *wheels_dir*."""
        dist_name = re.sub(r"[-_.]+", "_", self.env.project_name).lower()
        try:
            version = str(Version(self.env.version))
        except InvalidVersion:
            version = self.env.version
        prefix = f"{dist_name}-{version}-".lower()
        matches = [w for w in wheels_dir.glob("*.whl") if w.name.lower().startswith(prefix)]
        if not matches:
            raise RuntimeError(f"No wheel for {self.env.project_name} found in '{wheels_dir}'.")
        return max(matches, key=lambda w: w.stat().st_mtime)

    def build(self) -> None:
        """
        Execute the compilation and bundling pipeline.

        In ``pyinstaller`` mode: Cython → PyInstaller → wheel.
        In ``pyruntime`` mode: Cython → wheel only (no PyInstaller).
        """
        self.run_cython()
        if self.env.config.windows.deployment_mode == "pyinstaller":
            self.run_pyinstaller()
        wheel = self._build_wheel()
        # An app built later in this run reuses this wheel instead of rebuilding it.
        _BUILT_WHEELS[self.env.project_path] = wheel


class Packager:
    """Handles distribution preparation and Inno Setup installer creation."""

    def __init__(self, env: WindowsBuildEnvironment) -> None:
        """
        Initialize the packager.

        Parameters
        ----------
        env : WindowsBuildEnvironment
            The Windows build environment.
        """
        self.env = env

    def prepare_examples(self) -> None:
        """
        Copy examples to distribution.

        Notes
        -----
        Expects ``examples`` directory to exist in the project root.
        """
        if self.env.examples_dir_path.is_dir():
            logger.info("[bold]Copying example files...[/bold]")
            target = self.env.dist_exe_dir_path.joinpath("examples")
            safe_empty_dir(target)
            safe_copytree(self.env.examples_dir_path, target, dirs_exist_ok=True)

    def prepare_windows_files(self) -> None:
        """
        Copy Windows helpers and docs.

        Includes batch scripts, PowerShell scripts, and help files.
        In ``pyruntime`` mode also stages the PythonRuntime setup files and
        copies the built wheel into ``dist/portable/wheels/`` so that Inno
        Setup can include it in the installer.
        """
        logger.info("[bold]Copying extra files for Windows...[/bold]")
        is_pyruntime = self.env.config.windows.deployment_mode == "pyruntime"

        self.env.dist_exe_dir_path.joinpath("logs").mkdir(parents=True, exist_ok=True)
        bin_dir = self.env.dist_exe_dir_path.joinpath("bin")
        bin_dir.mkdir(parents=True, exist_ok=True)

        # Launcher scripts are always included; their content differs per mode.
        for script in [
            f"{self.env.project_name}_commandline.bat",
            f"{self.env.project_name}_powershell.ps1",
        ]:
            script_path = self.env.script_dir_path.joinpath(script)
            if script_path.exists():
                safe_copy(script_path, bin_dir.joinpath(script))

        if is_pyruntime:
            # setup_pyruntime.ps1 and its dependencies are only needed in
            # pyruntime mode where the installer creates a managed Python venv.
            setup_script = self.env.script_dir_path.joinpath("setup_pyruntime.ps1")
            if setup_script.exists():
                safe_copy(setup_script, bin_dir / "setup_pyruntime.ps1")

            # Copy .python-version so setup_pyruntime.ps1 can determine the
            # required Python version without any hardcoded value.
            if self.env.python_version_file_path.exists():
                safe_copy(self.env.python_version_file_path, bin_dir / ".python-version")
                logger.info("  [green]\u25ba[/green] Copied .python-version")
            else:
                logger.warning(
                    "  .python-version not found; setup_pyruntime.ps1 will not be able "
                    "to determine the Python version."
                )

            # Bundle uv.exe so that the online PythonRuntime setup can run
            # without requiring uv to be installed on the end-user's machine.
            uv_path = shutil.which("uv")
            if uv_path:
                safe_copy(Path(uv_path), bin_dir / "uv.exe")
                logger.info(f"  [green]\u25ba[/green] Copied uv.exe from '{uv_path}'")
            else:
                logger.warning(
                    "  uv not found in PATH. The PythonRuntime online setup will require "
                    "uv to be installed on the end-user's machine."
                )

            # Stage the built wheel into dist/portable/wheels/ so that the ISS
            # script can bundle it in the installer.  The wheel is always built
            # first by Compiler._build_wheel() into dist/.
            src_wheels = self.env.dist_wheels_dir_path
            dest_wheels = self.env.dist_exe_dir_path / "wheels"
            if src_wheels.is_dir():
                safe_empty_dir(dest_wheels)
                safe_copytree(src_wheels, dest_wheels, dirs_exist_ok=True)
                # Wheels of internal workspace dependencies go next to the app
                # wheel, so setup_pyruntime.ps1 can install them from wheels/.
                internal = self.env.internal_wheels_dir_path
                if internal.is_dir():
                    for wheel in sorted(internal.glob("*.whl")):
                        safe_copy(wheel, dest_wheels / wheel.name)
                logger.info(f"  Staged wheels into '{dest_wheels}'")
            else:
                logger.warning(
                    "  dist/ not found; the installer will not contain the "
                    "package wheel.  Ensure the compiler step ran successfully."
                )

        for dir_name in self.env.config.docs.public_doc_dirs:
            help_src = self.env.build_dir_path.joinpath(dir_name, "html")
            if not help_src.is_dir():
                logger.warning(
                    f"Built HTML for public_doc_dir '{dir_name}' not found at '{help_src}'. Skipping."
                )
                continue
            for dest_root in [
                self.env.dist_exe_dir_path.joinpath("documentation"),
                self.env.artifacts_dir_path.joinpath("documentation"),
            ]:
                dist_doc = dest_root.joinpath(dir_name)
                safe_empty_dir(dist_doc)
                safe_copytree(help_src, dist_doc, dirs_exist_ok=True)
                for f in ["_sources", "objects.inv", ".buildinfo"]:
                    p = dist_doc.joinpath(f)
                    if p.is_dir():
                        safe_rmtree(p)
                    elif p.exists():
                        safe_unlink(p)

    def run_innosetup(self) -> None:
        """
        Create the installer using Inno Setup.

        Notes
        -----
        Requires ``ISCC.exe`` to be available.  If it is not found, a warning
        is logged and the step is skipped (rather than raising), so that
        ``build_installer`` can be called standalone without a hard failure.
        Use pre-flight checks (``require_innosetup=True``) to enforce tool
        presence before the full pipeline runs.

        Raises
        ------
        RuntimeError
            If the Inno Setup command fails.
        """
        if not self.env.innosetup_exe_path.exists():
            logger.warning("Inno Setup not found. Skipping installer.")
            return

        logger.info("[bold]Running Inno Setup...[/bold]")
        iss_file = self.env.script_dir_path.joinpath(f"{self.env.project_name}.iss")
        if not iss_file.exists():
            logger.warning(f"Inno Setup script not found: {iss_file}")
            return

        self.env.dist_setup_dir_path.mkdir(parents=True, exist_ok=True)
        cmd = [
            str(self.env.innosetup_exe_path),
            f"/DMyAppVersion={self.env.version}",
            f"/DSourceDir={self.env.dist_exe_dir_path}",
            f"/O{self.env.dist_setup_dir_path}",
            "/Q",
            str(iss_file),
        ]

        if self.env.config.windows.deployment_mode == "pyruntime":
            # Tell the ISS script which deployment mode is active.
            cmd.append("/DPyruntimeMode=1")

            # Offline mode: if a pre-built PythonRuntime environment exists,
            # tell Inno Setup where to find it so it can be bundled into the
            # installer without an internet download at install time.
            pyruntime_dir = self.env.artifacts_dir_path / "pyruntime"
            if pyruntime_dir.is_dir():
                cmd.append(f"/DPythonRuntimeDir={pyruntime_dir}")
                logger.info(f"  Offline mode: PythonRuntime bundled from '{pyruntime_dir}'")
            else:
                logger.info("  Online mode: PythonRuntime will be downloaded at install time")

        self.env.run_command(cmd, "Error running Inno Setup", cwd=self.env.project_path)

    def _build_pyruntime(self) -> None:
        """
        Pre-build the PythonRuntime virtual environment for offline installer packaging.

        Uses the ``uv`` tool (must be on PATH) to:

        1. Download the Python version declared in ``.python-version``.
        2. Create a virtual environment at ``artifacts/pyruntime/``.
        3. Install the project's own binary wheel (resolved from ``dist/`` by
           its ``[project] name``) and ``pyyaml``, with all their dependencies.

        The resulting directory is picked up automatically by ``run_innosetup()``
        and included in the ``setup.exe`` as an optional component, producing an
        *offline* installer that does not require an internet connection at
        install time.

        Raises
        ------
        RuntimeError
            If ``uv`` is not found or any build step fails.
        """
        uv_exe = shutil.which("uv")
        if not uv_exe:
            raise RuntimeError(
                "uv not found in PATH. Cannot pre-build the PythonRuntime environment. "
                "Install uv (https://docs.astral.sh/uv/) and retry, or set "
                "bundle_pyruntime = false in scaldys-project.toml to use the online installer."
            )

        python_version = self.env.python_version_file_path.read_text().strip()
        pyruntime_dir = self.env.artifacts_dir_path / "pyruntime"
        safe_empty_dir(pyruntime_dir)

        logger.info("[bold]Pre-building PythonRuntime environment (offline installer)...[/bold]")

        logger.info(f"  [green]\u25ba[/green] [1/3] Installing Python {python_version} via uv ...")
        self.env.run_command(
            [uv_exe, "python", "install", python_version],
            f"Failed to install Python {python_version} via uv",
        )

        logger.info(
            f"  [green]\u25ba[/green] [2/3] Creating virtual environment at '{pyruntime_dir}' ..."
        )
        self.env.run_command(
            [uv_exe, "venv", str(pyruntime_dir), "--python", python_version],
            "Failed to create PythonRuntime virtual environment",
        )

        python_exe = pyruntime_dir / "Scripts" / "python.exe"
        wheels_dir = self.env.dist_wheels_dir_path
        package_name = self.env.project_name
        logger.info(
            f"  [green]\u25ba[/green] [3/3] Installing {package_name} "
            "(with dependencies) and pyyaml ..."
        )
        # Internal workspace dependencies are not on any index: point uv at
        # their wheels too.
        extra_links: list[str] = []
        internal = self.env.internal_wheels_dir_path
        if internal.is_dir() and any(internal.glob("*.whl")):
            extra_links = ["--find-links", str(internal)]
        self.env.run_command(
            [
                uv_exe,
                "pip",
                "install",
                "--python",
                str(python_exe),
                "--find-links",
                str(wheels_dir),
                *extra_links,
                package_name,
                "pyyaml",
            ],
            "Failed to install packages into PythonRuntime environment",
        )

        logger.info(f"  PythonRuntime environment ready at '{pyruntime_dir}'")

    def _distribute_docs(self) -> None:
        """
        Copy public documentation HTML output to ``artifacts/documentation/``.

        Used in ``wheel_only`` mode where no installer is produced but
        built docs still need to land in the artifacts directory.
        Entries in ``public_doc_dirs`` that have not yet been built are
        skipped with a warning.
        """
        for dir_name in self.env.config.docs.public_doc_dirs:
            help_src = self.env.build_dir_path.joinpath(dir_name, "html")
            if not help_src.is_dir():
                logger.warning(
                    f"Built HTML for public_doc_dir '{dir_name}' not found at '{help_src}'. Skipping."
                )
                continue
            dist_doc = self.env.artifacts_dir_path.joinpath("documentation", dir_name)
            safe_empty_dir(dist_doc)
            safe_copytree(help_src, dist_doc, dirs_exist_ok=True)
            for f in ["_sources", "objects.inv", ".buildinfo"]:
                p = dist_doc.joinpath(f)
                if p.is_dir():
                    safe_rmtree(p)
                elif p.exists():
                    safe_unlink(p)
            logger.info(
                f"  [green]\u25ba[/green] Distributed documentation '{dir_name}' → '{dist_doc}'"
            )

    def build(self) -> None:
        """
        Orchestrate the final packaging process.

        Includes preparing examples, copying Windows-specific files, optionally
        pre-building the PythonRuntime environment (offline installer), and
        running Inno Setup.

        In ``wheel_only`` mode no installer is produced, but any configured
        ``public_doc_dirs`` are still copied to ``dist/documentation/``.
        """
        if self.env.config.windows.deployment_mode == "wheel_only":
            self._distribute_docs()
            return
        self.prepare_examples()
        self.prepare_windows_files()
        if self.env.config.windows.bundle_pyruntime:
            self._build_pyruntime()
        self.run_innosetup()


class WindowsBuilder(BaseBuilder):
    """
    Orchestrates the Windows build pipeline.

    This class brings together documentation generation, Cython
    compilation, PyInstaller bundling, and installer creation.
    """

    def __init__(self, project_path: Path, verbose: bool = False) -> None:
        """
        Initialize the Windows builder pipeline.

        Parameters
        ----------
        project_path : Path
            The root directory of the project.
        verbose : bool, default False
            If True, enables verbose output.
        """
        env = WindowsBuildEnvironment(project_path, verbose)
        super().__init__(env)
        self.env: WindowsBuildEnvironment = env  # Narrow type from BaseBuildEnvironment
        self.doc_builder = DocumentationBuilder(self.env)
        self.compiler = Compiler(self.env)
        self.packager = Packager(self.env)

    def _any_sphinx_docs(self) -> bool:
        """Return True if any docs subdirectory is detected as a Sphinx project."""
        docs_root = self.env.docs_dir_path
        if not docs_root.is_dir():
            return False
        return any(_detect_engine(p) == DocEngine.SPHINX for p in docs_root.iterdir() if p.is_dir())

    def _is_in_onedrive(self) -> bool:
        """Check if the project is located within a OneDrive-synchronized folder."""
        project_path = self.env.project_path.resolve()
        for key, value in os.environ.items():
            if "onedrive" in key.lower() and value:
                try:
                    onedrive_root = Path(value).resolve()
                    if project_path.is_relative_to(onedrive_root):
                        return True
                except (ValueError, TypeError, OSError):
                    continue
        return False

    def _run_steps(
        self,
        steps: list[tuple[str, Any]],
        title: str,
        console: Any | None = None,
    ) -> None:
        """
        Execute a list of named build steps with a Rich progress bar.

        Parameters
        ----------
        steps : list of (description, callable)
            Each tuple is a human-readable step description and the callable
            to invoke for that step.
        title : str
            Title shown on the overall progress bar task.
        console : Console, optional
            A rich console instance for synchronized output.
        """
        from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn, TimeElapsedColumn

        if console is None:
            from rich.console import Console

            console = Console()

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
            console=console,
        ) as progress:
            total_task = progress.add_task(f"[green]{title}", total=len(steps))
            for description, step_func in steps:
                progress.update(total_task, description=f"[cyan]{description}...")
                step_func()
                progress.advance(total_task)

    def clean_docs(self) -> None:
        """
        Clean out files generated by previous documentation builds.
        """
        super().clean_docs()

    def clean_windows(self) -> None:
        """
        Clean out files generated by previous Windows distribution builds.

        Specially handles OneDrive environments to avoid sync conflicts.
        """
        target_dirs = [
            self.env.src_compiled_dir_path,
            self.env.internal_wheels_dir_path,
            self.env.build_dir_path.joinpath("pyinstaller"),
            self.env.dist_dir_path,
            self.env.artifacts_dir_path,
        ]

        if self._is_in_onedrive() and any(p.exists() for p in target_dirs):
            logger.info(
                "[yellow]OneDrive detected: active synchronization may cause the cleaning process to take several minutes. "
                "If it becomes excessively slow, you can manually delete the 'dist', 'artifacts' or 'build' subdirectories via File Explorer.[/yellow]"
            )

        super().clean_windows()

    def clean_all(self) -> None:
        """
        Clean all build, documentation, and distribution directories.

        Specially handles OneDrive environments to avoid sync conflicts.
        """
        target_dirs = [self.env.build_dir_path, self.env.dist_dir_path, self.env.artifacts_dir_path]

        if self._is_in_onedrive() and any(p.exists() for p in target_dirs):
            logger.info(
                "[yellow]OneDrive detected: active synchronization may cause the cleaning process to take several minutes. "
                "If it becomes excessively slow, you can manually delete the 'build', 'dist' and 'artifacts' directories via File Explorer.[/yellow]"
            )

        super().clean_all()

    def clean(self) -> None:
        """
        Clean out files generated by previous builds (alias for clean_all).
        """
        self.clean_all()

    def build_docs(self) -> None:
        """Generate all documentation using the documentation builder."""
        self.doc_builder.build()

    def build_internal_deps(self) -> list[Path]:
        """
        Build the wheels of this app's internal workspace dependencies.

        For every member in the app's internal closure (libraries first), runs
        that member's own ``clean``, Cython staging and wheel build, so its own
        ``compiled_modules`` apply, then copies the wheel into this project's
        ``build/internal_wheels/``.  Not ``dist/``: ``publish`` refuses more
        than one binary wheel there.

        Each member is built at most once per process: a member already built
        in this run (as a target of its own or for another app) is reused.
        Its ``build/compiled/`` tree is what PyInstaller bundles via
        ``--paths``.

        Returns
        -------
        list of Path
            The collected wheels in ``build/internal_wheels/``.
        """
        closure = self.env.internal_closure()
        if not closure:
            return []

        logger.info("[bold]Building internal workspace dependencies...[/bold]")
        dest_dir = self.env.internal_wheels_dir_path
        safe_empty_dir(dest_dir)
        collected: list[Path] = []
        for member in closure:
            wheel = _BUILT_WHEELS.get(member.path)
            if wheel is not None and wheel.exists():
                logger.info(f"  [green]\u25ba[/green] {member.name}: reusing '{wheel.name}'")
            else:
                logger.info(f"  [green]\u25ba[/green] {member.name}: building wheel")
                dep = WindowsBuilder(member.path, verbose=self.env.verbose)
                dep.clean()
                dep.compiler.run_cython()
                wheel = dep.compiler._build_wheel()
                _BUILT_WHEELS[member.path] = wheel
            target = dest_dir / wheel.name
            safe_copy(wheel, target)
            collected.append(target)
        logger.info(f"  [green]\u2713[/green] Internal wheels collected in '{dest_dir}'")
        return collected

    def build_exe(self) -> None:
        """
        Run the compilation and bundling step.

        What this produces depends on ``deployment_mode``:

        - ``pyinstaller``  — Cython → PyInstaller executable → wheel
        - ``pyruntime``    — Cython → wheel (no PyInstaller)
        - ``wheel_only``   — Cython → wheel (no PyInstaller)
        """
        self.compiler.build()

    def build_installer(self) -> None:
        """
        Run the packaging and installer step.

        What this produces depends on ``deployment_mode``:

        - ``pyinstaller`` / ``pyruntime`` — assembles ``artifacts/portable/`` and
          produces ``artifacts/installer/setup.exe`` via Inno Setup.
        - ``wheel_only`` — no-op; logs a message and returns immediately.
        """
        self.packager.build()

    def _distribution_steps(self, require_sphinx: bool = False) -> list[tuple[str, Any]]:
        """
        Return the ordered list of steps for the Windows distribution build,
        adapted to the current ``deployment_mode``.

        Parameters
        ----------
        require_sphinx : bool, default False
            When ``True``, the pre-flight check also verifies that
            ``sphinx-build`` is available.  Pass ``True`` from ``main()``
            when documentation is included in the build.

        Used by both ``build_distribution()`` and ``main()``.
        """
        mode = self.env.config.windows.deployment_mode
        is_pyruntime = mode == "pyruntime"
        is_wheel_only = mode == "wheel_only"
        dist_label = "Building executable" if mode == "pyinstaller" else "Building distribution"

        steps: list[tuple[str, Any]] = [
            (
                "Checking project compliance",
                lambda: self.env.check_compliance(
                    require_exe=True,
                    require_installer=not is_wheel_only,
                ),
            ),
            (
                "Pre-flight checks",
                lambda: self.env.pre_flight_checks(
                    require_sphinx=require_sphinx,
                    require_pyinstaller=not (is_pyruntime or is_wheel_only),
                    require_innosetup=not is_wheel_only,
                ),
            ),
            ("Cleaning build directories", self.clean),
        ]
        # Apps of a uv workspace bundle their internal dependencies; libraries
        # (wheel_only) only build their own wheel.
        if not is_wheel_only and self.env.internal_closure():
            steps.append(("Building internal dependencies", self.build_internal_deps))
        steps.append((dist_label, self.build_exe))
        if is_wheel_only:
            steps.append(("Distributing documentation", self.build_installer))
        else:
            steps.append(("Building installer", self.build_installer))
        return steps

    def build_distribution(self, console: Any | None = None) -> None:
        """
        Build the Windows distribution artifact without building documentation.

        Runs compliance checks, pre-flight checks, cleans previous artefacts,
        then compiles and packages according to ``deployment_mode``.  For the
        full workflow including documentation see ``main()``.

        Parameters
        ----------
        console : Console, optional
            A rich console instance for synchronized output.
        """
        steps = self._distribution_steps()
        self._run_steps(
            steps,
            f"Building {self.env.project_name} (Windows)...",
            console=console,
        )
        logger.info("Windows distribution build completed successfully!")

    def main(self, console: Any | None = None) -> None:
        """
        Run the complete end-to-end build workflow (documentation + distribution).

        Parameters
        ----------
        console : Console, optional
            A rich console instance for synchronized output.
        """
        has_sphinx = self._any_sphinx_docs()
        steps = self._distribution_steps(require_sphinx=has_sphinx)
        # Insert the documentation step right after clean (index 3).  A project
        # (typically a workspace library) without docs/ simply has no such step.
        if self.env.docs_dir_path.is_dir():
            steps.insert(3, ("Building documentation", self.build_docs))
        else:
            logger.info(f"No docs/ directory in '{self.env.project_path}'; skipping documentation.")
        self._run_steps(
            steps,
            f"Building {self.env.project_name}...",
            console=console,
        )
        logger.info("[bold green]\u2713 Build completed successfully[/bold green]")
