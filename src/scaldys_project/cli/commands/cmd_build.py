from pathlib import Path

import typer

from scaldys_project.cli.utils import (
    AllPackagesOption,
    PackagesOption,
    console,
    resolve_targets_or_exit,
    run_for_targets,
)
from scaldys_project.windows.builder import WindowsBuilder

build_app = typer.Typer(help="Build subcommands.", no_args_is_help=True)


@build_app.command("all")
def build_all(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose output."),
    packages: PackagesOption = None,
    all_packages: AllPackagesOption = False,
) -> None:
    """Full build: documentation + Windows distribution."""

    def action(path: Path) -> None:
        WindowsBuilder(path, verbose=verbose).main(console=console)

    run_for_targets(resolve_targets_or_exit(packages, all_packages), action, title="Build")


@build_app.command("docs")
def build_docs(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose output."),
    packages: PackagesOption = None,
    all_packages: AllPackagesOption = False,
) -> None:
    """Build documentation only."""

    def action(path: Path) -> None:
        builder = WindowsBuilder(path, verbose=verbose)
        builder.env.pre_flight_checks(require_sphinx=True)
        builder.build_docs()

    run_for_targets(resolve_targets_or_exit(packages, all_packages), action, title="Build docs")


@build_app.command("windows")
def build_windows(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose output."),
    packages: PackagesOption = None,
    all_packages: AllPackagesOption = False,
) -> None:
    """Build Windows distribution artifact (behaviour depends on deployment_mode in scaldys-project.toml)."""

    def action(path: Path) -> None:
        WindowsBuilder(path, verbose=verbose).build_distribution(console=console)

    run_for_targets(resolve_targets_or_exit(packages, all_packages), action, title="Build windows")


@build_app.command("clean")
def build_clean(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose output."),
    packages: PackagesOption = None,
    all_packages: AllPackagesOption = False,
) -> None:
    """Remove build/, dist/ and artifacts/ directories."""

    def action(path: Path) -> None:
        WindowsBuilder(path, verbose=verbose).clean()

    run_for_targets(resolve_targets_or_exit(packages, all_packages), action, title="Clean")
