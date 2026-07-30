# -*- coding: utf-8 -*-

import logging
import subprocess
from pathlib import Path

import typer

logger = logging.getLogger(__name__)


def test() -> None:
    """Run the test suite with pytest."""
    cmd = ["uv", "run", "pytest", "-v", "--durations=0", "--cov", "--cov-report=xml"]
    logger.info(f"  [dim]Command: {' '.join(cmd)}[/dim]")
    result = subprocess.run(
        cmd,
        cwd=Path.cwd(),
    )
    if result.returncode != 0:
        raise typer.Exit(result.returncode)
