# -*- coding: utf-8 -*-

import importlib.resources
import logging
import subprocess
from pathlib import Path

import typer
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn, TimeElapsedColumn

from scaldys_project.cli.utils import console

logger = logging.getLogger(__name__)

ci_app = typer.Typer(
    help="CI quality checks (mirrors the GitHub Actions pipeline).",
    no_args_is_help=True,
)


def _run(cmd: list[str], *, quiet: bool = False) -> None:
    """Run a subprocess in cwd; raise typer.Exit with its return code on failure."""
    result = subprocess.run(cmd, cwd=Path.cwd(), capture_output=True, text=True)
    if not quiet:
        output = (result.stdout + result.stderr).strip()
        for line in output.splitlines():
            if line.strip():
                logger.info(f"  {line}")
    if result.returncode != 0:
        raise typer.Exit(result.returncode)


def _run_format_diff(cmd: list[str]) -> None:
    """Run a format --diff command; show affected file names instead of full diffs."""
    result = subprocess.run(cmd, cwd=Path.cwd(), capture_output=True, text=True)
    output = result.stdout + result.stderr

    affected: list[str] = []
    for line in output.splitlines():
        if line.startswith("--- ") and line[4:].strip() not in ("/dev/null", ""):
            path = line[4:].split("\t")[0].strip()
            if path not in affected:
                affected.append(path)

    if affected:
        logger.info("  Files that would be reformatted:")
        for f in affected:
            logger.info(f"    [yellow]{f}[/yellow]")

    for line in output.splitlines():
        if "reformatted" in line or "already formatted" in line:
            logger.info(f"  {line.strip()}")

    if result.returncode != 0:
        raise typer.Exit(result.returncode)


@ci_app.command("lint")
def ci_lint() -> None:
    """Run ruff check (Python lint)."""
    logger.info("[bold]Running Python lint...[/bold]")
    _run(["uv", "run", "ruff", "check", "."])


@ci_app.command("format")
def ci_format() -> None:
    """Run ruff format --diff (check only, no rewrite)."""
    logger.info("[bold]Checking Python formatting...[/bold]")
    _run_format_diff(["uv", "run", "ruff", "format", "--diff", "."])


@ci_app.command("typecheck")
def ci_typecheck() -> None:
    """Run pyright type checking."""
    logger.info("[bold]Syncing Python dependencies...[/bold]")
    _run(["uv", "sync"], quiet=True)
    logger.info("[bold]Running Python type check...[/bold]")
    _run(["uv", "run", "pyright", "./src"])


@ci_app.command("markdown")
def ci_markdown() -> None:
    """Check markdown formatting with prettier (check only, no rewrite)."""
    logger.info("[bold]Checking markdown formatting...[/bold]")
    _check_config = importlib.resources.files("scaldys_project.resources").joinpath(
        ".pre-commit-check-config.yaml"
    )
    with importlib.resources.as_file(_check_config) as config_path:
        _run(
            [
                "uv",
                "run",
                "pre-commit",
                "run",
                "--config",
                str(config_path),
                "prettier",
                "--all-files",
            ]
        )


@ci_app.command("doclint")
def ci_doclint() -> None:
    """Run sphinx-lint on the docs directory."""
    logger.info("[bold]Running doc lint...[/bold]")
    _run(["uv", "run", "sphinx-lint", "docs/"])


@ci_app.command("all")
def ci_all() -> None:
    """Run all CI steps in sequence, stopping on first failure."""
    steps = [
        ("Python lint", ci_lint),
        ("Format check", ci_format),
        ("Type check", ci_typecheck),
        ("Markdown check", ci_markdown),
        ("Doc lint", ci_doclint),
    ]
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("{task.completed}/{task.total}"),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("[cyan]Running CI checks...", total=len(steps))
        for name, step_fn in steps:
            progress.update(task, description=f"[cyan]{name}...")
            step_fn()
            progress.advance(task)
        progress.update(task, description="[cyan]CI checks")
    logger.info("[bold green]\u2713 All CI checks passed![/bold green]")
