import logging
import subprocess
import tomllib
from pathlib import Path

import typer
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn, TimeElapsedColumn

from scaldys_project.cli.utils import console, current_workspace, workspace_root
from scaldys_project.common.config import load_config
from scaldys_project.common.docs import check_ci_markdown_drift, get_markdown_target_files

logger = logging.getLogger(__name__)

ci_app = typer.Typer(
    help="CI quality checks (mirrors the GitHub Actions pipeline).",
    no_args_is_help=True,
)


def _run(cmd: list[str], *, quiet: bool = False) -> None:
    """Run a subprocess at the workspace (or project) root; raise typer.Exit on failure."""
    logger.info(f"  [dim]Command: {' '.join(cmd)}[/dim]")
    result = subprocess.run(cmd, cwd=workspace_root(), capture_output=True, text=True, check=False)
    if not quiet:
        output = (result.stdout + result.stderr).strip()
        for line in output.splitlines():
            if line.strip():
                logger.info(f"  {line}")
    if result.returncode != 0:
        raise typer.Exit(result.returncode)


def _run_format_diff(cmd: list[str]) -> None:
    """Run a format --diff command; show affected file names instead of full diffs."""
    logger.info(f"  [dim]Command: {' '.join(cmd)}[/dim]")
    result = subprocess.run(cmd, cwd=workspace_root(), capture_output=True, text=True, check=False)
    output = result.stdout + result.stderr

    affected: list[str] = []
    for line in output.splitlines():
        if line.startswith("--- ") and line[4:].strip() not in ("/dev/null", ""):
            path = line[4:].split("\t")[0].strip()
            if path not in affected:
                affected.append(path)

    if affected:
        logger.info("  Files that would be reformatted:")
        for f in affected:
            logger.info(f"    [yellow]{f}[/yellow]")

    for line in output.splitlines():
        if "reformatted" in line or "already formatted" in line:
            logger.info(f"  {line.strip()}")

    if result.returncode != 0:
        raise typer.Exit(result.returncode)


@ci_app.command("lint")
def ci_lint() -> None:
    """Run ruff check (Python lint)."""
    logger.info("[bold]Running Python lint...[/bold]")
    _run(["uv", "run", "ruff", "check", "."])


@ci_app.command("format")
def ci_format() -> None:
    """Run ruff format --diff (check only, no rewrite)."""
    logger.info("[bold]Checking Python formatting...[/bold]")
    _run_format_diff(["uv", "run", "ruff", "format", "--diff", "."])


@ci_app.command("typecheck")
def ci_typecheck() -> None:
    """Run pyright type checking."""
    logger.info("[bold]Syncing Python dependencies...[/bold]")
    # A bare 'uv sync' in a workspace member uninstalls the other members.
    workspace = current_workspace()
    _run(["uv", "sync", "--all-packages"] if workspace else ["uv", "sync"], quiet=True)
    logger.info("[bold]Running Python type check...[/bold]")
    if workspace is None:
        _run(["uv", "run", "pyright", "./src", "./tests"])
    elif _root_has_pyright_config(workspace.root):
        # Let the root [tool.pyright] include/exclude decide what is checked.
        _run(["uv", "run", "pyright"])
    else:
        # No root config: check every member's source root and tests/.
        paths: list[str] = []
        for member in workspace.members.values():
            source_root = load_config(member.path, workspace.root).cython.source_root
            for folder in (member.path / source_root, member.path / "tests"):
                if folder.is_dir():
                    paths.append(folder.relative_to(workspace.root).as_posix())
        _run(["uv", "run", "pyright", *paths])


def _root_has_pyright_config(root: Path) -> bool:
    """Return True when the workspace root pyproject.toml has [tool.pyright]."""
    try:
        with open(root / "pyproject.toml", "rb") as f:
            return "pyright" in tomllib.load(f).get("tool", {})
    except (OSError, tomllib.TOMLDecodeError):
        return False


@ci_app.command("markdown")
def ci_markdown() -> None:
    """Check markdown formatting with mdformat (check only, no rewrite)."""
    logger.info("[bold]Checking markdown formatting...[/bold]")
    project_root = workspace_root()
    config = load_config(project_root)
    drift_warning = check_ci_markdown_drift(project_root, config=config.format)
    if drift_warning:
        logger.warning(f"[yellow]\u26a0 {drift_warning}[/yellow]")
    target_files = get_markdown_target_files(project_root, config=config.format)
    if not target_files:
        logger.info("  No markdown files to check.")
        return
    _run(["uv", "run", "mdformat", "--check", *[str(p) for p in target_files]])


@ci_app.command("doclint")
def ci_doclint() -> None:
    """Run sphinx-lint on the docs directory (every member's in a workspace)."""
    logger.info("[bold]Running doc lint...[/bold]")
    workspace = current_workspace()
    if workspace is None:
        _run(["uv", "run", "sphinx-lint", "docs/"])
        return
    doc_dirs = [workspace.root / "docs"] + [m.path / "docs" for m in workspace.members.values()]
    targets: list[str] = []
    for doc_dir in doc_dirs:
        if doc_dir.is_dir():
            rel = doc_dir.relative_to(workspace.root).as_posix() + "/"
            if rel not in targets:
                targets.append(rel)
    if not targets:
        logger.info("  No docs/ directories to lint.")
        return
    _run(["uv", "run", "sphinx-lint", *targets])


@ci_app.command("all")
def ci_all() -> None:
    """Run all CI steps in sequence, continuing regardless of errors."""
    steps = [
        ("Python lint", ci_lint),
        ("Format check", ci_format),
        ("Type check", ci_typecheck),
        ("Markdown check", ci_markdown),
        ("Doc lint", ci_doclint),
    ]
    failed_steps = []
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("{task.completed}/{task.total}"),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("[cyan]Running CI checks...", total=len(steps))
        for name, step_fn in steps:
            progress.update(task, description=f"[cyan]{name}...")
            try:
                step_fn()
            except typer.Exit as e:
                if e.exit_code != 0:
                    failed_steps.append(name)
            except Exception as e:  # noqa: BLE001
                logger.error(f"Step '{name}' failed with an unexpected error: {e}")
                failed_steps.append(name)
            progress.advance(task)
        progress.update(task, description="[cyan]CI checks")

    if failed_steps:
        logger.error(f"[bold red]\u2717 CI checks failed in: {', '.join(failed_steps)}[/bold red]")
        raise typer.Exit(code=1)

    logger.info("[bold green]\u2713 All CI checks passed![/bold green]")
