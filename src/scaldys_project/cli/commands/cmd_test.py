# -*- coding: utf-8 -*-

import subprocess
from pathlib import Path

import typer


def test() -> None:
    """Run the test suite with pytest."""
    result = subprocess.run(
        ["uv", "run", "pytest", "-v", "--durations=0", "--cov", "--cov-report=xml"],
        cwd=Path.cwd(),
    )
    if result.returncode != 0:
        raise typer.Exit(result.returncode)
