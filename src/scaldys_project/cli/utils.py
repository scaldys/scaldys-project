import logging
from collections.abc import Callable
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.rule import Rule
from rich.table import Table

from scaldys_project.common.workspace import Workspace, WorkspaceError, find_workspace

console = Console()

logger = logging.getLogger(__name__)

# Shared target-selection options for commands that act on workspace members.
PackagesOption = Annotated[
    list[str] | None,
    typer.Option(
        "--package",
        "-p",
        help="Workspace member to act on (repeatable). Default: the member at the cwd.",
    ),
]
AllPackagesOption = Annotated[
    bool,
    typer.Option("--all-packages", help="Act on every workspace member, libraries first."),
]


class TargetError(RuntimeError):
    """Raised when the requested targets cannot be resolved."""


def find_project_root() -> Path:
    """Walk up from cwd to find the first directory containing pyproject.toml.

    Falls back to cwd if no pyproject.toml is found.
    """
    cwd = Path.cwd()
    for candidate in [cwd, *cwd.parents]:
        if (candidate / "pyproject.toml").exists():
            return candidate
    return cwd


def current_workspace() -> Workspace | None:
    """Return the uv workspace the cwd belongs to, or ``None``."""
    return find_workspace(Path.cwd())


def workspace_root() -> Path:
    """Return the workspace root, or the project root when there is no workspace."""
    workspace = current_workspace()
    return workspace.root if workspace else find_project_root()


def resolve_targets(packages: list[str] | None, all_packages: bool) -> list[Path]:
    """
    Return the project directories a command should act on.

    - No workspace: the project root, as before.  ``--package`` is an error.
    - ``--all-packages``: every member, in topological order (libraries first).
    - ``--package NAME`` (repeatable): those members, in topological order.
    - Neither, cwd inside a member: that member.
    - Neither, cwd at a virtual workspace root: an error listing the members.

    Raises
    ------
    TargetError
        If the selection is invalid.
    """
    packages = packages or []
    workspace = current_workspace()

    if workspace is None:
        if packages or all_packages:
            raise TargetError(
                "--package and --all-packages need a uv workspace "
                "(a pyproject.toml with [tool.uv.workspace])."
            )
        return [find_project_root()]

    try:
        if all_packages:
            keys = workspace.topological_order()
        elif packages:
            keys = workspace.topological_order(packages)
        else:
            member = workspace.member_at(find_project_root())
            if member is None:
                raise TargetError(
                    f"'{workspace.root}' is a virtual workspace root; choose the members to "
                    f"act on with --package NAME or --all-packages. "
                    f"Members: {', '.join(workspace.member_names())}"
                )
            keys = [member.key]
    except WorkspaceError as exc:
        raise TargetError(str(exc)) from exc

    return [workspace.members[k].path for k in keys]


def resolve_targets_or_exit(packages: list[str] | None, all_packages: bool) -> list[Path]:
    """Like :func:`resolve_targets`, but log the error and exit with code 2."""
    try:
        return resolve_targets(packages, all_packages)
    except TargetError as exc:
        logger.error(f"[bold red]\u2717[/bold red] {exc}")
        raise typer.Exit(2) from exc


def run_for_targets(targets: list[Path], action: Callable[[Path], None], *, title: str) -> None:
    """
    Run *action* once per target directory, stopping on the first failure.

    With several targets each one gets a header, and a summary table is
    printed at the end (also after a failure).  A single target runs exactly
    as it always did, without header or summary.
    """
    if len(targets) == 1:
        action(targets[0])
        return

    results: list[tuple[str, str]] = []
    failure: BaseException | None = None
    for target in targets:
        console.print(Rule(f"[bold]{title}: {target.name}[/bold]"))
        try:
            action(target)
        except (Exception, SystemExit, typer.Exit) as exc:  # noqa: BLE001
            code = getattr(exc, "exit_code", getattr(exc, "code", 1))
            if isinstance(exc, (SystemExit, typer.Exit)) and code in (0, None):
                results.append((target.name, "[green]ok[/green]"))
                continue
            results.append((target.name, "[red]failed[/red]"))
            failure = exc
            break
        results.append((target.name, "[green]ok[/green]"))

    done = {name for name, _ in results}
    results.extend((t.name, "[dim]not run[/dim]") for t in targets if t.name not in done)

    table = Table(title=f"{title} summary")
    table.add_column("Package")
    table.add_column("Result")
    for name, status in results:
        table.add_row(name, status)
    console.print(table)

    if failure is not None:
        raise failure
