# -*- coding: utf-8 -*-

import logging
import subprocess

import typer

from scaldys_project.cli.utils import find_project_root

logger = logging.getLogger(__name__)

_PURE_PYTHON_SUFFIX = "-none-any.whl"


def publish(
    test: bool = typer.Option(False, "--test", help="Publish to TestPyPI instead of PyPI."),
) -> None:
    """Publish the binary wheel from dist/ to PyPI.

    Refuses to publish pure-Python wheels to prevent Cython source code
    from being exposed on PyPI.  Run 'scaldys-project build all' first to
    produce a binary wheel with compiled extensions in dist/.
    """
    project_root = find_project_root()
    dist_dir = project_root / "dist"

    if not dist_dir.exists():
        logger.error(
            "[bold red]\u2717 dist/ directory not found.[/bold red] "
            "Run 'scaldys-project build all' first."
        )
        raise typer.Exit(1)

    wheels = list(dist_dir.glob("*.whl"))
    if not wheels:
        logger.error(
            "[bold red]\u2717 No wheel found in dist/.[/bold red] "
            "Run 'scaldys-project build all' first."
        )
        raise typer.Exit(1)

    binary_wheels = [w for w in wheels if not w.name.endswith(_PURE_PYTHON_SUFFIX)]
    if not binary_wheels:
        names = [w.name for w in wheels]
        logger.error(
            f"[bold red]\u2717 Only pure-Python wheels found in dist/:[/bold red] {names}\n"
            "  Publishing a pure wheel would expose Cython source code on PyPI.\n"
            "  Run 'scaldys-project build all' to produce a binary wheel first."
        )
        raise typer.Exit(1)

    if len(binary_wheels) > 1:
        names = [w.name for w in binary_wheels]
        logger.error(
            f"[bold red]\u2717 Multiple binary wheels found in dist/:[/bold red] {names}\n"
            "  Run 'scaldys-project build clean' then 'scaldys-project build all' "
            "to get a clean build."
        )
        raise typer.Exit(1)

    wheel = binary_wheels[0]
    target = "TestPyPI" if test else "PyPI"
    logger.info(f"[bold]Publishing[/bold] {wheel.name} [bold]\u2192[/bold] {target}")

    cmd: list[str] = ["uv", "publish", str(wheel)]
    if test:
        cmd += ["--index", "testpypi"]

    result = subprocess.run(cmd, cwd=project_root)
    if result.returncode != 0:
        raise typer.Exit(result.returncode)

    logger.info("[bold green]\u2713 Published successfully.[/bold green]")
