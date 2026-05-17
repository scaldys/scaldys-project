# -*- coding: utf-8 -*-

import typer

from scaldys_project.cli.utils import console, find_project_root
from scaldys_project.windows.builder import WindowsBuilder

build_app = typer.Typer(help="Build subcommands.", no_args_is_help=True)


@build_app.command("all")
def build_all(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose output."),
) -> None:
    """Full build: documentation + Windows distribution."""
    builder = WindowsBuilder(find_project_root(), verbose=verbose)
    builder.main(console=console)


@build_app.command("docs")
def build_docs(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose output."),
) -> None:
    """Build documentation only."""
    builder = WindowsBuilder(find_project_root(), verbose=verbose)
    builder.env.pre_flight_checks(require_sphinx=True)
    builder.build_docs()


@build_app.command("windows")
def build_windows(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose output."),
) -> None:
    """Build Windows distribution artifact (behaviour depends on deployment_mode in scaldys.toml)."""
    builder = WindowsBuilder(find_project_root(), verbose=verbose)
    builder.build_distribution(console=console)


@build_app.command("clean")
def build_clean(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose output."),
) -> None:
    """Remove build/, dist/ and artifacts/ directories."""
    builder = WindowsBuilder(find_project_root(), verbose=verbose)
    builder.clean()
