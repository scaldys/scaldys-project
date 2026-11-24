import ast
import logging
import os
import shutil
import sys
import tomllib
from pathlib import Path
from subprocess import CalledProcessError, run
from typing import Any

from scaldys_project.common.config import BuildConfig, load_config
from scaldys_project.common.utils import safe_empty_dir, safe_unlink
from scaldys_project.common.workspace import Member, Workspace, find_workspace

logger = logging.getLogger(__name__)


class BaseBuildEnvironment:
    """
    Handle path discovery, tool location, and command execution.

    This base class manages common paths and tools that are likely to be
    used across different platforms.
    """

    def __init__(self, project_path: Path, verbose: bool = False) -> None:
        """
        Initialize the build environment.

        Parameters
        ----------
        project_path : Path
            The root directory of the project.
        verbose : bool, default False
            If True, set logging level to DEBUG.
        """
        if verbose:
            logger.setLevel(logging.DEBUG)

        self.verbose = verbose
        self.project_path = project_path.resolve()

        # Read project name and version from pyproject.toml — single source of truth.
        with open(self.project_path / "pyproject.toml", "rb") as _f:
            _meta = tomllib.load(_f)["project"]
        # Raw name (hyphens preserved) — used for exe naming, packaging file names,
        # and display.  Do not use for Python import paths.
        self.project_name: str = _meta["name"]
        # PEP 503/508: package directories must use underscores; hyphens are
        # valid in pyproject.toml [project] name but illegal in Python imports.
        self.project_package_name: str = _meta["name"].replace("-", "_")
        self.version: str = _meta["version"]

        # uv workspace this project belongs to (None for a standalone project).
        # build/, dist/, artifacts/, docs/ and packaging/ stay per member; only
        # .python-version and scaldys-project.toml defaults come from the root.
        self.workspace: Workspace | None = find_workspace(self.project_path)
        self.workspace_root_path: Path = (
            self.workspace.root if self.workspace else self.project_path
        )

        # Load project-specific build configuration from scaldys-project.toml
        # (defaults if absent; merged over the workspace root's file for members).
        self.config: BuildConfig = load_config(
            self.project_path, self.workspace_root_path if self.workspace else None
        )

        self.python_exe_path = Path(sys.executable)
        self.python_dir_path = self.python_exe_path.parent
        # Executable base name: [windows] exe_name, falling back to the project name.
        self.exe_name = self.config.windows.exe_name or self.project_name

        # Core project paths
        self.build_dir_path = self.project_path.joinpath("build")
        # The member's own .python-version wins; otherwise the workspace root's.
        self.python_version_file_path = self.project_path / ".python-version"
        if not self.python_version_file_path.exists():
            root_version_file = self.workspace_root_path / ".python-version"
            if root_version_file.exists():
                self.python_version_file_path = root_version_file
        self.docs_dir_path = self.project_path.joinpath("docs")
        self.src_dir_path = self.project_path / self.config.cython.source_root
        self.dist_dir_path = self.project_path.joinpath("dist")
        self.artifacts_dir_path = self.project_path.joinpath("artifacts")

        # Executables (find in PATH)
        self.sphinx_exe_path = self._find_tool(
            "sphinx-build" + (".exe" if os.name == "nt" else ""), self.python_dir_path
        )

    @property
    def workspace_member(self) -> Member | None:
        """This project's entry in the workspace, or ``None`` outside a workspace."""
        return self.workspace.member_at(self.project_path) if self.workspace else None

    def _find_tool(self, name: str, fallback_path: Path) -> Path:
        """
        Find a tool in PATH or in a fallback location.

        Parameters
        ----------
        name : str
            The name of the tool executable.
        fallback_path : Path
            The directory to look in if the tool is not in PATH.

        Returns
        -------
        Path
            The path to the tool.
        """
        tool_path = shutil.which(name)
        if tool_path:
            return Path(tool_path)
        return fallback_path.joinpath(name)

    def run_command(self, cmd: list[str], err_msg: str, cwd: Path | None = None) -> tuple[str, str]:
        """
        Run command in subprocess and raise on unexpected exit status.

        Parameters
        ----------
        cmd : list of str
            The command to run.
        err_msg : str
            The error message to display if the command fails.
        cwd : Path, optional
            The working directory to run the command in.

        Returns
        -------
        stdout : str
            The standard output of the command.
        stderr : str
            The standard error of the command.

        Raises
        ------
        RuntimeError
            If the command returns a non-zero exit status.
        """
        try:
            proc = run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
                cwd=cwd,
            )
            return proc.stdout, proc.stderr
        except CalledProcessError as e:
            logger.error(f"{err_msg}: {e}")
            if e.stderr:
                logger.error(f"Error output: {e.stderr}")
            raise RuntimeError(err_msg) from e
        except Exception as e:  # Catch-all for unexpected OS-level errors (FileNotFoundError, etc.)
            logger.error(f"{err_msg}: {e}")
            raise RuntimeError(err_msg) from e

    def validate_cython_modules(self) -> list[str]:
        """Check that modules to be compiled with Cython do not use match/case.

        Returns
        -------
        list of str
            List of paths to files containing match/case constructs.
        """
        issues = []
        # ast.Match is available in Python 3.10+
        match_type = getattr(ast, "Match", None)
        if match_type is None:
            return issues

        for module in self.config.cython.compiled_modules:
            # Convert dotted module path to file path relative to src_dir_path
            rel_path = module.replace(".", "/") + ".py"
            file_path = self.src_dir_path / rel_path

            if not file_path.exists():
                continue

            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    tree = ast.parse(f.read())

                for node in ast.walk(tree):
                    if isinstance(node, match_type):
                        issues.append(str(file_path.relative_to(self.project_path)))
                        break
            except (SyntaxError, OSError):
                # If it doesn't parse as valid Python, Cython will fail anyway.
                pass
        return issues


class BaseBuilder:
    """
    Base class for platform-specific builders.

    Orchestrates the build pipeline for a specific platform.
    """

    def __init__(self, env: BaseBuildEnvironment):
        """
        Initialize the builder.

        Parameters
        ----------
        env : BaseBuildEnvironment
            The build environment configuration.
        """
        self.env = env

    def pre_flight_checks(self, **kwargs: Any) -> None:
        """
        Perform checks before starting the build.

        Parameters
        ----------
        **kwargs : Any
            Arguments passed to the environment's pre-flight checks.
        """

    def clean_docs(self) -> None:
        """
        Clean out files generated by previous documentation builds.
        """
        logger.info("[bold]Cleaning documentation build directories...[/bold]")
        if self.env.docs_dir_path.is_dir():
            for doc_dir in sorted(p for p in self.env.docs_dir_path.iterdir() if p.is_dir()):
                target_path = self.env.build_dir_path / doc_dir.name
                if target_path.exists():
                    logger.info(f"  [green]\u25ba[/green] Cleaning directory '{target_path}'")
                    safe_empty_dir(target_path)

    def clean_windows(self) -> None:
        """
        Clean out files generated by previous Windows distribution builds.
        """
        logger.info("[bold]Cleaning Windows build artifacts...[/bold]")
        for subdir_name in ("compiled", "internal_wheels", "pyinstaller"):
            path = self.env.build_dir_path / subdir_name
            if path.exists():
                logger.info(f"  [green]\u25ba[/green] Cleaning directory '{path}'")
                safe_empty_dir(path)

        if self.env.build_dir_path.exists():
            for spec_file in self.env.build_dir_path.glob("*.spec"):
                safe_unlink(spec_file)

        target_dirs = [self.env.dist_dir_path, self.env.artifacts_dir_path]
        for path in target_dirs:
            if path.exists():
                logger.info(f"  [green]\u25ba[/green] Cleaning directory '{path}'")
                safe_empty_dir(path)

        for c_file in self.env.src_dir_path.rglob("*.c"):
            safe_unlink(c_file)

    def clean_all(self) -> None:
        """
        Clean all build, documentation, and distribution directories.
        """
        target_dirs = [self.env.build_dir_path, self.env.dist_dir_path, self.env.artifacts_dir_path]
        logger.info("[bold]Cleaning all build directories...[/bold]")
        for path in target_dirs:
            logger.info(f"  [green]\u25ba[/green] Cleaning directory '{path}'")
            safe_empty_dir(path)

        for c_file in self.env.src_dir_path.rglob("*.c"):
            safe_unlink(c_file)

    def clean(self) -> None:
        """
        Clean out files generated by previous builds (alias for clean_all).
        """
        self.clean_all()
