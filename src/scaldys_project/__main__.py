"""
Main entry point for the scaldys-project build system.

Provides a unified CLI for building projects.  Run from the root of the
consuming project (the directory that contains ``pyproject.toml``)::

    scaldys-project build all       # full build: docs + Windows distribution
    scaldys-project build docs      # documentation only
    scaldys-project build windows   # Windows distribution only (mode-dependent)
    scaldys-project build clean     # remove build/, dist/ and artifacts/
    scaldys-project check           # verify project compliance

The Windows distribution step is controlled by ``deployment_mode`` in
``builder.toml``:

    pyinstaller  (default) — PyInstaller exe + Inno Setup installer
    pyruntime              — binary wheel + Inno Setup installer with PythonRuntime
    wheel_only             — binary wheel only, no installer
"""

import logging
from pathlib import Path
import typer
from rich.console import Console
from rich.logging import RichHandler

from scaldys_project.windows.builder import WindowsBuilder


def _find_project_root() -> Path:
    """
    Walk up from the current directory to find the project root.

    The project root is identified as the first directory containing a
    ``pyproject.toml`` file.  Falls back to ``cwd`` if none is found.
    """
    cwd = Path.cwd()
    for candidate in [cwd, *cwd.parents]:
        if (candidate / "pyproject.toml").exists():
            return candidate
    return cwd


PROJECT_ROOT = _find_project_root()

console = Console()
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(rich_tracebacks=True, console=console, show_path=False, markup=True)],
)
logger = logging.getLogger(__name__)

app = typer.Typer(help="Scaldys Builder", no_args_is_help=True)
build_app = typer.Typer(help="Build subcommands", no_args_is_help=True)

app.add_typer(build_app, name="build")


@build_app.command("all")
def build_all(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose output."),
) -> None:
    """Full build: documentation + Windows distribution."""
    builder = WindowsBuilder(PROJECT_ROOT, verbose=verbose)
    builder.main(console=console)


@build_app.command("docs")
def build_docs(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose output."),
) -> None:
    """Build documentation only."""
    builder = WindowsBuilder(PROJECT_ROOT, verbose=verbose)
    builder.env.pre_flight_checks(require_sphinx=True)
    builder.build_docs()


@build_app.command("windows")
def build_windows(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose output."),
) -> None:
    """Build Windows distribution artifact (behaviour depends on deployment_mode in builder.toml)."""
    builder = WindowsBuilder(PROJECT_ROOT, verbose=verbose)
    builder.build_distribution(console=console)


@build_app.command("clean")
def build_clean(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose output."),
) -> None:
    """Remove build/, dist/ and artifacts/ directories."""
    builder = WindowsBuilder(PROJECT_ROOT, verbose=verbose)
    builder.clean()


@app.command("check")
def check(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose output."),
) -> None:
    """Check that the current project is compliant with scaldys-project requirements."""
    try:
        builder = WindowsBuilder(PROJECT_ROOT, verbose=verbose)
    except (FileNotFoundError, KeyError) as exc:
        logger.error(f"[bold red]Cannot read project metadata:[/bold red] {exc}")
        logger.error(
            "  [red]\u2717[/red] Ensure a valid 'pyproject.toml' with "
            "[project] name and version is present at the project root."
        )
        raise SystemExit(1) from exc

    mode = builder.env.config.windows.deployment_mode
    is_wheel_only = mode == "wheel_only"
    builder.env.check_compliance(require_exe=True, require_installer=not is_wheel_only)
    logger.info("[bold green]\u2713 Project is compliant.[/bold green]")


if __name__ == "__main__":
    app()
