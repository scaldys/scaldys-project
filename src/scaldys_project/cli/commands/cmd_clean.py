from pathlib import Path

import typer

from scaldys_project.cli.utils import (
    AllPackagesOption,
    PackagesOption,
    resolve_targets_or_exit,
    run_for_targets,
)
from scaldys_project.windows.builder import WindowsBuilder

clean_app = typer.Typer(help="Clean build and output directories.", no_args_is_help=True)


@clean_app.command("all")
def clean_all(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose output."),
    packages: PackagesOption = None,
    all_packages: AllPackagesOption = False,
) -> None:
    """Remove all build/, dist/ and artifacts/ directories and generated C files."""

    def action(path: Path) -> None:
        WindowsBuilder(path, verbose=verbose).clean_all()

    run_for_targets(resolve_targets_or_exit(packages, all_packages), action, title="Clean all")


@clean_app.command("docs")
def clean_docs(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose output."),
    packages: PackagesOption = None,
    all_packages: AllPackagesOption = False,
) -> None:
    """Remove documentation build output directories."""

    def action(path: Path) -> None:
        WindowsBuilder(path, verbose=verbose).clean_docs()

    run_for_targets(resolve_targets_or_exit(packages, all_packages), action, title="Clean docs")


@clean_app.command("windows")
def clean_windows(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose output."),
    packages: PackagesOption = None,
    all_packages: AllPackagesOption = False,
) -> None:
    """Remove Windows compilation and distribution artifacts."""

    def action(path: Path) -> None:
        WindowsBuilder(path, verbose=verbose).clean_windows()

    run_for_targets(resolve_targets_or_exit(packages, all_packages), action, title="Clean windows")
