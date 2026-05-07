import logging
import os
import sys
import shutil
import tomllib
from pathlib import Path
from subprocess import PIPE, CalledProcessError, run
from typing import Any

from scaldys_builder.common.config import load_config, BuildConfig
from scaldys_builder.common.utils import safe_empty_dir, safe_unlink

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

        # Load project-specific build configuration from builder.toml (defaults if absent).
        self.config: BuildConfig = load_config(self.project_path)

        self.python_exe_path = Path(sys.executable)
        self.python_dir_path = self.python_exe_path.parent
        self.exe_name = self.project_name

        # Core project paths
        self.build_dir_path = self.project_path.joinpath("build")
        self.docs_dir_path = self.project_path.joinpath("docs")
        self.src_dir_path = self.project_path / self.config.cython.source_root
        self.dist_dir_path = self.project_path.joinpath("dist")

        # Documentation paths
        self.user_guide_dir_path = self.docs_dir_path.joinpath("manual")
        self.user_guide_build_dir_path = self.build_dir_path.joinpath("manual")
        self.developer_guide_dir_path = self.docs_dir_path.joinpath("developer_guide")
        self.developer_guide_build_dir_path = self.build_dir_path.joinpath("developer_guide")

        # Executables (find in PATH)
        self.sphinx_exe_path = self._find_tool(
            "sphinx-build" + (".exe" if os.name == "nt" else ""), self.python_dir_path
        )
        self.sphinx_apidoc_exe_path = self._find_tool(
            "sphinx-apidoc" + (".exe" if os.name == "nt" else ""), self.python_dir_path
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
        pass

    def clean(self) -> None:
        """
        Clean out files generated by previous builds.
        """
        target_dirs = [self.env.build_dir_path, self.env.dist_dir_path]
        logger.info("[bold]Cleaning build directories...[/bold]")
        for path in target_dirs:
            logger.info(f"  Cleaning directory '{path}'")
            safe_empty_dir(path)

        for c_file in self.env.src_dir_path.rglob("*.c"):
            safe_unlink(c_file)
