# -*- coding: utf-8 -*-

import logging
import re
import subprocess
from pathlib import Path

import typer
from rich.markup import escape as markup_escape
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn, TimeElapsedColumn

from scaldys_project.cli.utils import console

logger = logging.getLogger(__name__)

# Matches any ANSI/VT escape sequence (CSI, OSC, single-char escapes, …).
_ANSI_RE = re.compile(r"\x1b(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")

format_app = typer.Typer(
    help="Auto-format source and documentation files.",
    no_args_is_help=True,
)


def _run(cmd: list[str], success_codes: frozenset[int] = frozenset({0})) -> None:
    """Run a subprocess in cwd; raise typer.Exit with its return code on failure.

    success_codes: set of return codes treated as success (default: {0}).
    Use frozenset({0, 1}) for pre-commit format commands where exit code 1
    means "files were reformatted" rather than an error.
    """
    result = subprocess.run(cmd, cwd=Path.cwd(), capture_output=True, text=True)
    output = (result.stdout + result.stderr).strip()
    lines = [
        f"  {markup_escape(_ANSI_RE.sub('', line))}"
        for line in output.splitlines()
        if _ANSI_RE.sub("", line).strip()
    ]
    if lines:
        logger.info("\n".join(lines))
    if result.returncode not in success_codes:
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
    _run(["uv", "run", "pre-commit", "run", "prettier", "--all-files"], frozenset({0, 1}))


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
