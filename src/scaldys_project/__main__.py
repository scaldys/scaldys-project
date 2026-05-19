"""
Main entry point for the scaldys-project build system.

Provides a unified CLI for building projects.  Run from the root of the
consuming project (the directory that contains ``pyproject.toml``)::

    scaldys-project init             # scaffold a new project from scaldys-template
    scaldys-project build all       # full build: docs + Windows distribution
    scaldys-project build docs      # documentation only
    scaldys-project build windows   # Windows distribution only (mode-dependent)
    scaldys-project build clean     # remove build/, dist/ and artifacts/
    scaldys-project check           # verify project compliance
    scaldys-project publish         # upload binary wheel from dist/ to PyPI
    scaldys-project publish --test  # upload binary wheel to TestPyPI
    scaldys-project ci all          # run full CI pipeline locally (lint + format + typecheck)
    scaldys-project ci lint         # ruff check only
    scaldys-project ci format       # ruff format --diff only
    scaldys-project ci typecheck    # pyright only
    scaldys-project test            # run pytest

The Windows distribution step is controlled by ``deployment_mode`` in
``scaldys-project.toml``:

    pyinstaller  (default) — PyInstaller exe + Inno Setup installer
    pyruntime              — binary wheel + Inno Setup installer with PythonRuntime
    wheel_only             — binary wheel only, no installer
"""

from scaldys_project.cli.cli import app

if __name__ == "__main__":
    app()
