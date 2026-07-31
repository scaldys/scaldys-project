import ast
import logging
import os
import shutil
import sys
import tomllib
from pathlib import Path
from subprocess import PIPE, CalledProcessError, run
from typing import Any

from scaldys_project.common.config import BuildConfig, load_config
from scaldys_project.common.utils import safe_empty_dir, safe_unlink

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

        # Load project-specific build configuration from scaldys-project.toml (defaults if absent).
        self.config: BuildConfig = load_config(self.project_path)

        self.python_exe_path = Path(sys.executable)
        self.python_dir_path = self.python_exe_path.parent
        self.exe_name = self.project_name

        # Core project paths
        self.build_dir_path = self.project_path.joinpath("build")
        self.python_version_file_path = self.project_path / ".python-version"
        self.docs_dir_path = self.project_path.joinpath("docs")
        self.src_dir_path = self.project_path / self.config.cython.source_root
        self.dist_dir_path = self.project_path.joinpath("dist")
        self.artifacts_dir_path = self.project_path.joinpath("artifacts")

        # Executables (find in PATH)
        self.sphinx_exe_path = self._find_tool(
            "sphinx-build" + (".exe" if os.name == "nt" else ""), self.python_dir_path
        )

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
                stdout=PIPE,
                stderr=PIPE,
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

    def clean(self) -> None:
        """
        Clean out files generated by previous builds.
        """
        target_dirs = [self.env.build_dir_path, self.env.dist_dir_path, self.env.artifacts_dir_path]
        logger.info("[bold]Cleaning build directories...[/bold]")
        for path in target_dirs:
            logger.info(f"  [green]\u25ba[/green] Cleaning directory '{path}'")
            safe_empty_dir(path)

        for c_file in self.env.src_dir_path.rglob("*.c"):
            safe_unlink(c_file)
