# -*- coding: utf-8 -*-

from pathlib import Path

from rich.console import Console

console = Console()


def find_project_root() -> Path:
    """Walk up from cwd to find the first directory containing pyproject.toml.

    Falls back to cwd if no pyproject.toml is found.
    """
    cwd = Path.cwd()
    for candidate in [cwd, *cwd.parents]:
        if (candidate / "pyproject.toml").exists():
            return candidate
    return cwd
