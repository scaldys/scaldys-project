# -*- coding: utf-8 -*-

import logging

import typer

from scaldys_project.cli.utils import find_project_root
from scaldys_project.windows.builder import WindowsBuilder

logger = logging.getLogger(__name__)


def check(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose output."),
) -> None:
    """Check that the current project is compliant with scaldys-project requirements."""
    try:
        builder = WindowsBuilder(find_project_root(), verbose=verbose)
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
