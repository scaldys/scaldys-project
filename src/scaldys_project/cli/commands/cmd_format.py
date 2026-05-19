# -*- coding: utf-8 -*-

import logging
import subprocess
from pathlib import Path

import typer
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn, TimeElapsedColumn

from scaldys_project.cli.utils import console

logger = logging.getLogger(__name__)

format_app = typer.Typer(
    help="Auto-format source and documentation files.",
    no_args_is_help=True,
)


def _run(cmd: list[str]) -> None:
    """Run a subprocess in cwd; raise typer.Exit with its return code on failure."""
    result = subprocess.run(cmd, cwd=Path.cwd(), capture_output=True, text=True)
    output = (result.stdout + result.stderr).strip()
    for line in output.splitlines():
        if line.strip():
            logger.info(f"  {line}")
    if result.returncode != 0:
        raise typer.Exit(result.returncode)


@format_app.command("python")
def format_python() -> None:
    """Auto-format Python source files with ruff."""
    logger.info("[bold]Formatting Python files...[/bold]")
    _run(["uv", "run", "ruff", "format", "."])


@format_app.command("markdown")
def format_markdown() -> None:
    """Auto-format Markdown files with prettier (rewrites files in place)."""
    logger.info("[bold]Formatting Markdown files...[/bold]")
    _run(["uv", "run", "pre-commit", "run", "prettier", "--all-files"])


@format_app.command("all")
def format_all() -> None:
    """Auto-format all files (Python + Markdown) in sequence."""
    steps = [
        ("Python", format_python),
        ("Markdown", format_markdown),
    ]
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("{task.completed}/{task.total}"),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("[cyan]Formatting files...", total=len(steps))
        for name, step_fn in steps:
            progress.update(task, description=f"[cyan]Formatting {name}...")
            step_fn()
            progress.advance(task)
        progress.update(task, description="[cyan]Format")
    logger.info("[bold green]\u2713 All files formatted![/bold green]")
