import logging
from pathlib import Path

import typer

from scaldys_project.cli.utils import (
    AllPackagesOption,
    PackagesOption,
    resolve_targets_or_exit,
    run_for_targets,
)
from scaldys_project.windows.builder import WindowsBuilder

logger = logging.getLogger(__name__)


def _check_one(path: Path, verbose: bool) -> None:
    try:
        builder = WindowsBuilder(path, verbose=verbose)
    except (FileNotFoundError, KeyError) as exc:
        logger.error(f"[bold red]Cannot read project metadata:[/bold red] {exc}")
        logger.error(
            "  [red]\u2717[/red] Ensure a valid 'pyproject.toml' with "
            "[project] name and version is present at the project root."
        )
        raise SystemExit(1) from exc

    mode = builder.env.config.windows.deployment_mode
    is_wheel_only = mode == "wheel_only"
    # __main__.py is only required for apps; check_compliance skips it in wheel_only mode.
    builder.env.check_compliance(require_exe=True, require_installer=not is_wheel_only)
    logger.info("[bold green]\u2713 Project is compliant.[/bold green]")


def check(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose output."),
    packages: PackagesOption = None,
    all_packages: AllPackagesOption = False,
) -> None:
    """Check that the current project is compliant with scaldys-project requirements."""
    run_for_targets(
        resolve_targets_or_exit(packages, all_packages),
        lambda path: _check_one(path, verbose),
        title="Check",
    )
