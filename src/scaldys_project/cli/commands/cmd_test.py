import logging
import subprocess
from pathlib import Path

import typer

from scaldys_project.cli.utils import (
    AllPackagesOption,
    PackagesOption,
    current_workspace,
    find_project_root,
    resolve_targets_or_exit,
    run_for_targets,
)

logger = logging.getLogger(__name__)

_PYTEST_ARGS = ["-v", "--durations=0", "--cov", "--cov-report=xml"]


def _run(cmd: list[str], cwd: Path) -> None:
    logger.info(f"  [dim]Command: {' '.join(cmd)}[/dim]")
    result = subprocess.run(cmd, cwd=cwd, check=False)
    if result.returncode != 0:
        raise typer.Exit(result.returncode)


def test(
    packages: PackagesOption = None,
    all_packages: AllPackagesOption = False,
) -> None:
    """Run the test suite with pytest.

    In a uv workspace each selected member runs its own tests/ folder in its
    own environment (uv run --package).  At a virtual workspace root with no
    member selected, pytest runs once at the root, using the root testpaths.
    """
    workspace = current_workspace()

    if workspace is None:
        resolve_targets_or_exit(packages, all_packages)  # rejects --package outside a workspace
        _run(["uv", "run", "pytest", *_PYTEST_ARGS], cwd=Path.cwd())
        return

    at_virtual_root = workspace.member_at(find_project_root()) is None
    if not packages and not all_packages and at_virtual_root:
        _run(["uv", "run", "pytest", *_PYTEST_ARGS], cwd=workspace.root)
        return

    def action(path: Path) -> None:
        member = workspace.member_at(path)
        assert member is not None
        tests_dir = (path / "tests").relative_to(workspace.root).as_posix()
        _run(
            ["uv", "run", "--package", member.name, "pytest", tests_dir, *_PYTEST_ARGS],
            cwd=workspace.root,
        )

    run_for_targets(resolve_targets_or_exit(packages, all_packages), action, title="Test")
