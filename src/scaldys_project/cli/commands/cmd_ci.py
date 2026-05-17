# -*- coding: utf-8 -*-

import subprocess
from pathlib import Path

import typer

ci_app = typer.Typer(
    help="CI quality checks (mirrors the GitHub Actions pipeline).",
    no_args_is_help=True,
)


def _run(cmd: list[str]) -> None:
    """Run a subprocess in cwd; raise typer.Exit with its return code on failure."""
    result = subprocess.run(cmd, cwd=Path.cwd())
    if result.returncode != 0:
        raise typer.Exit(result.returncode)


@ci_app.command("lint")
def ci_lint() -> None:
    """Run ruff check (lint)."""
    _run(["uv", "run", "ruff", "check", "."])


@ci_app.command("format")
def ci_format() -> None:
    """Run ruff format --diff (check only, no rewrite)."""
    _run(["uv", "run", "ruff", "format", "--diff", "."])


@ci_app.command("typecheck")
def ci_typecheck() -> None:
    """Run pyright type checking."""
    _run(["uv", "sync"])
    _run(["uv", "run", "pyright", "./src"])


@ci_app.command("all")
def ci_all() -> None:
    """Run all CI steps in sequence, stopping on first failure."""
    ci_lint()
    ci_format()
    ci_typecheck()
