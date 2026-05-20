# -*- coding: utf-8 -*-

import datetime
import logging
import re
import shutil
import subprocess
import tempfile
import urllib.request
import zipfile
from pathlib import Path
from typing import Any

import typer

from scaldys_project.cli.utils import console

logger = logging.getLogger(__name__)

# ── Constants ────────────────────────────────────────────────────────────────

_GITHUB_ZIP_HEADS = "https://github.com/scaldys/scaldys-template/archive/refs/heads/{ref}.zip"
_GITHUB_ZIP_TAGS = "https://github.com/scaldys/scaldys-template/archive/refs/tags/{ref}.zip"

_EXCLUDE_NAMES: frozenset[str] = frozenset(
    {".git", ".idea", "build", "app_data", "dist", "artifacts", "__pycache__"}
)
_EXCLUDE_EXACT: frozenset[str] = frozenset({"uv.lock"})
_EXCLUDE_SUFFIXES: tuple[str, ...] = (".egg-info",)
_BINARY_EXTENSIONS: frozenset[str] = frozenset(
    {
        ".ico",
        ".png",
        ".jpg",
        ".jpeg",
        ".gif",
        ".bmp",
        ".exe",
        ".dll",
        ".pyd",
        ".whl",
        ".zip",
        ".tar",
    }
)
_DEPLOYMENT_MODES: tuple[str, ...] = ("pyinstaller", "pyruntime", "wheel_only")
_PLACEHOLDER_DESCRIPTION = "A skeleton for Python projects by Scaldys."
_PLACEHOLDER_VERSION = "0.9.0"

# ── Name derivation helpers ───────────────────────────────────────────────────


def _to_package_name(s: str) -> str:
    """'My Cool App' → 'my_cool_app'"""
    return re.sub(r"[-\s]+", "_", s.strip()).lower()


def _to_project_slug(s: str) -> str:
    """'My Cool App' → 'my-cool-app'"""
    return re.sub(r"[_\s]+", "-", s.strip()).lower()


# ── Interactive parameter collection ─────────────────────────────────────────


def _collect_params() -> dict[str, Any]:
    """Prompt the user for all project parameters and return them as a dict."""
    from rich.rule import Rule

    console.print()
    console.print(Rule("[bold]Project identity[/bold]"))

    console.print(
        "  [dim]Prefer one word; multi-word → lowercase with dashes "
        "(e.g. [italic]my-cool-app[/italic]). Used in README and docs titles.[/dim]"
    )
    project_name: str = typer.prompt("Project name")
    console.print(
        "  [dim]Python import name — underscores only, dashes forbidden "
        "(e.g. [italic]my_cool_app[/italic]). Used in [italic]src/[/italic] layout and "
        "[italic]import[/italic] statements.[/dim]"
    )
    package_name: str = typer.prompt("Package name", default=_to_package_name(project_name))
    console.print(
        "  [dim]Repo / directory identifier — lowercase with dashes, underscores forbidden "
        "(e.g. [italic]my-cool-app[/italic]). Used as git repo name and CLI entry-point.[/dim]"
    )
    project_slug: str = typer.prompt("Project slug", default=_to_project_slug(project_name))
    console.print("  [dim]Used in copyright notices and package metadata.[/dim]")
    organization_name: str = typer.prompt("Organization name", default="Scaldys")

    console.print()
    console.print(Rule("[bold]Author & metadata[/bold]"))
    console.print("  [dim]Used in [italic]pyproject.toml[/italic] and Sphinx docs copyright.[/dim]")
    author_name: str = typer.prompt("Author name", default="")
    console.print("  [dim]Used in [italic]pyproject.toml[/italic] authors list.[/dim]")
    author_email: str = typer.prompt("Author email", default="")
    console.print(
        "  [dim]One-line summary (≤ 80 chars). Stored in [italic]pyproject.toml[/italic] "
        "and shown in README.[/dim]"
    )
    description: str = typer.prompt("Short description", default="A Python application.")
    console.print(
        "  [dim]Semantic version MAJOR.MINOR.PATCH. Stored in [italic]pyproject.toml[/italic]. "
        "Use [italic]0.1.0[/italic] for early development.[/dim]"
    )
    version: str = typer.prompt("Initial version", default="0.1.0")
    console.print(
        "  [dim]Used to generate badge URLs and repo links in README. "
        "Leave empty to skip.[/dim]"
    )
    github_username: str = typer.prompt("GitHub username/org", default="")

    console.print()
    console.print(Rule("[bold]Build configuration[/bold]"))
    console.print(
        "  [dim]Controls how the project is packaged and distributed "
        "(stored in [italic]scaldys-project.toml[/italic]):[/dim]\n"
        "  [dim]  [italic]pyinstaller[/italic]  — standalone executable; no Python required on target[/dim]\n"
        "  [dim]  [italic]pyruntime[/italic]    — bundled portable Python runtime[/dim]\n"
        "  [dim]  [italic]wheel_only[/italic]   — standard .whl; Python must be present on target[/dim]"
    )
    deployment_mode = ""
    while deployment_mode not in _DEPLOYMENT_MODES:
        deployment_mode = typer.prompt(
            f"Deployment mode ({'/'.join(_DEPLOYMENT_MODES)})", default="wheel_only"
        )
        if deployment_mode not in _DEPLOYMENT_MODES:
            logger.error(f"[red]Invalid mode.[/red] Choose one of: {', '.join(_DEPLOYMENT_MODES)}")

    console.print()
    console.print(Rule("[bold]Output[/bold]"))
    console.print(
        "  [dim]Where the project folder is created. "
        "Defaults to [italic]./<project-slug>[/italic] inside the current directory.[/dim]"
    )
    target_dir: str = typer.prompt("Target directory", default=f"./{project_slug}")

    console.print()
    console.print(Rule("[bold]Post-init actions[/bold]"))
    console.print(
        "  [dim]Runs [italic]git init[/italic] + initial commit inside the new project directory.[/dim]"
    )
    init_git: bool = typer.confirm("Initialise git repository?", default=True)
    console.print(
        "  [dim]Runs [italic]uv sync[/italic] to create [italic].venv[/italic] "
        "and install all dependencies immediately.[/dim]"
    )
    run_sync: bool = typer.confirm("Run uv sync?", default=True)

    return {
        "project_name": project_name,
        "package_name": package_name,
        "project_slug": project_slug,
        "organization_name": organization_name,
        "author_name": author_name,
        "author_email": author_email,
        "description": description,
        "version": version,
        "github_username": github_username,
        "deployment_mode": deployment_mode,
        "target_dir": target_dir,
        "init_git": init_git,
        "run_sync": run_sync,
    }


# ── Summary panel ─────────────────────────────────────────────────────────────


def _print_summary(params: dict[str, Any]) -> None:
    """Print a Rich panel summarising collected parameters before proceeding."""
    from rich.panel import Panel
    from rich.table import Table

    table = Table(show_header=False, box=None, padding=(0, 2))
    for label, value in [
        ("Project name", params["project_name"]),
        ("Package name", params["package_name"]),
        ("Project slug", params["project_slug"]),
        ("Organization", params["organization_name"]),
        ("Author", f"{params['author_name']} <{params['author_email']}>"),
        ("Description", params["description"]),
        ("Version", params["version"]),
        ("Deployment mode", params["deployment_mode"]),
        ("Target directory", params["target_dir"]),
        ("GitHub username/org", params["github_username"] or "(not set)"),
        ("Init git", "yes" if params["init_git"] else "no"),
        ("Run uv sync", "yes" if params["run_sync"] else "no"),
    ]:
        table.add_row(f"[bold]{label}[/bold]", str(value))

    console.print()
    console.print(Panel(table, title="[bold cyan]Project summary[/bold cyan]", expand=False))


# ── Template acquisition ──────────────────────────────────────────────────────


def _download_template(ref: str, tmp_dir: Path) -> Path:
    """Download the scaldys-template ZIP for *ref* and extract into *tmp_dir*.

    Returns the path of the single root directory inside the archive
    (e.g. ``tmp_dir/scaldys-template-main``).
    """
    zip_path = tmp_dir / "template.zip"
    urls = [_GITHUB_ZIP_HEADS.format(ref=ref), _GITHUB_ZIP_TAGS.format(ref=ref)]
    last_exc: Exception | None = None

    with console.status(f"[bold]Downloading scaldys-template @ {ref}…[/bold]"):
        for url in urls:
            try:
                urllib.request.urlretrieve(url, zip_path)
                last_exc = None
                break
            except Exception as exc:
                last_exc = exc

    if last_exc is not None:
        raise RuntimeError(
            f"Failed to download template from GitHub (ref={ref!r}).\n"
            f"  Tried: {urls[0]}\n"
            f"  Tried: {urls[1]}\n"
            f"  Error: {last_exc}"
        ) from last_exc

    extract_dir = tmp_dir / "extracted"
    extract_dir.mkdir()
    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(extract_dir)

    roots = [d for d in extract_dir.iterdir() if d.is_dir()]
    if len(roots) != 1:
        raise RuntimeError(
            f"Unexpected ZIP structure: expected exactly one root directory, got {[r.name for r in roots]}."
        )
    return roots[0]


# ── Filtered copy ─────────────────────────────────────────────────────────────


def _should_exclude(p: Path) -> bool:
    """Return True if this path (file or directory) should be excluded."""
    name = p.name
    if name in _EXCLUDE_NAMES or name in _EXCLUDE_EXACT:
        return True
    return any(name.endswith(s) for s in _EXCLUDE_SUFFIXES)


def _copy_filtered(src: Path, dst: Path) -> None:
    """Recursively copy *src* to *dst*, skipping excluded entries."""
    dst.mkdir(parents=True, exist_ok=True)
    for item in src.iterdir():
        if _should_exclude(item):
            continue
        target = dst / item.name
        if item.is_dir():
            _copy_filtered(item, target)
        else:
            shutil.copy2(item, target)


# ── Content replacement ───────────────────────────────────────────────────────


def _build_replacements(params: dict[str, Any]) -> list[tuple[str, str]]:
    """Return ordered (find, replace) pairs.

    The order matters: more-specific strings (containing sub-strings of others)
    must appear first to prevent partial-match corruption.
    """
    pairs: list[tuple[str, str]] = [
        ("Scaldys-Template", params["project_name"]),
        ("scaldys_template", params["package_name"]),
        ("scaldys-template", params["project_slug"]),
        ("scaldys@scaldys.net", params["author_email"]),
        ("Scaldys", params["organization_name"]),
    ]
    if params["github_username"]:
        pairs.append(("github.com/scaldys/", f"github.com/{params['github_username']}/"))
    return pairs


def _is_binary(path: Path) -> bool:
    """Return True if the file should be skipped for text content replacement."""
    if path.suffix.lower() in _BINARY_EXTENSIONS:
        return True
    try:
        path.read_bytes()[:1024].decode("utf-8")
        return False
    except (UnicodeDecodeError, OSError):
        return True


def _replace_in_file(path: Path, replacements: list[tuple[str, str]]) -> None:
    """Apply all *replacements* to a single text file in-place."""
    if _is_binary(path):
        return
    try:
        text = path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return
    new_text = text
    for find, replace in replacements:
        new_text = new_text.replace(find, replace)
    if new_text != text:
        path.write_text(new_text, encoding="utf-8")


def _replace_content(root: Path, replacements: list[tuple[str, str]]) -> None:
    """Walk the entire tree and apply *replacements* to every text file."""
    for path in root.rglob("*"):
        if path.is_file():
            _replace_in_file(path, replacements)


# ── File / directory renaming ─────────────────────────────────────────────────


def _rename_component(name: str, package_name: str, project_slug: str) -> str:
    """Replace template strings within a single path component name."""
    name = name.replace("scaldys_template", package_name)
    name = name.replace("scaldys-template", project_slug)
    return name


def _rename_paths(root: Path, package_name: str, project_slug: str) -> None:
    """Rename every file and directory whose name contains a template string.

    Processes in post-order (deepest paths first) so that child renames
    do not invalidate parent paths before they are processed.
    """
    all_paths = sorted(root.rglob("*"), key=lambda p: len(p.parts), reverse=True)
    for path in all_paths:
        if not path.exists():
            continue
        new_name = _rename_component(path.name, package_name, project_slug)
        if new_name != path.name:
            path.rename(path.parent / new_name)


# ── Targeted post-processing ──────────────────────────────────────────────────


def _post_process(root: Path, params: dict[str, Any]) -> None:
    """Apply fixes that cannot be expressed as simple string replacement.

    1. Sphinx conf.py: correct the copyright year and author fields.
    2. pyproject.toml: set the description and initial version.
    3. scaldys-project.toml: set the deployment_mode if not the default.
    """
    year = str(datetime.date.today().year)
    package_name: str = params["package_name"]
    author_name: str = params["author_name"] or package_name

    # 1. Sphinx conf.py files
    for conf in root.rglob("conf.py"):
        try:
            text = conf.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        # copyright = "2024-2026, {package_name}" → "{year}, {author_name}"
        text = re.sub(
            rf'copyright = "[\d]+-[\d]+, {re.escape(package_name)}"',
            f'copyright = "{year}, {author_name}"',
            text,
        )
        # author = "{package_name}" → author = "{author_name}"
        text = text.replace(f'author = "{package_name}"', f'author = "{author_name}"')
        conf.write_text(text, encoding="utf-8")

    # 2. pyproject.toml: description and version
    toml = root / "pyproject.toml"
    if toml.exists():
        text = toml.read_text(encoding="utf-8")
        text = text.replace(
            f'description = "{_PLACEHOLDER_DESCRIPTION}"',
            f'description = "{params["description"]}"',
        )
        text = re.sub(
            rf'^version = "{re.escape(_PLACEHOLDER_VERSION)}"',
            f'version = "{params["version"]}"',
            text,
            flags=re.MULTILINE,
        )
        toml.write_text(text, encoding="utf-8")

    # 3. scaldys-project.toml: deployment_mode (only when not the default)
    sp_toml = root / "scaldys-project.toml"
    if sp_toml.exists() and params["deployment_mode"] != "pyinstaller":
        text = sp_toml.read_text(encoding="utf-8")
        text = text.replace(
            'deployment_mode = "pyinstaller"',
            f'deployment_mode = "{params["deployment_mode"]}"',
        )
        sp_toml.write_text(text, encoding="utf-8")


# ── Post-init actions ─────────────────────────────────────────────────────────


def _run_post_init(project_dir: Path, init_git: bool, run_sync: bool) -> None:
    """Run optional post-creation steps; failures are warnings, not fatal errors."""
    if init_git:
        with console.status("[bold]Initialising git repository…[/bold]"):
            r1 = subprocess.run(["git", "init"], cwd=project_dir, capture_output=True)
            r2 = subprocess.run(["git", "add", "."], cwd=project_dir, capture_output=True)
            r3 = subprocess.run(
                ["git", "commit", "-m", "chore: initial project scaffolded from scaldys-template"],
                cwd=project_dir,
                capture_output=True,
            )
        if any(r.returncode != 0 for r in (r1, r2, r3)):
            logger.warning("[yellow]⚠ git initialisation failed.[/yellow] Run 'git init' manually.")
        else:
            logger.info("[green]✓[/green] git repository initialised with initial commit.")

    if run_sync:
        with console.status("[bold]Running uv sync…[/bold]"):
            result = subprocess.run(["uv", "sync"], cwd=project_dir)
        if result.returncode != 0:
            logger.warning(
                "[yellow]⚠ uv sync failed.[/yellow] Run 'uv sync' manually inside the project."
            )
        else:
            logger.info("[green]✓[/green] uv sync completed.")


# ── Main command ──────────────────────────────────────────────────────────────


def init(
    local: Path | None = typer.Option(
        None,
        "--local",
        metavar="PATH",
        help="Use a local template directory instead of downloading from GitHub.",
    ),
    template_ref: str = typer.Option(
        "main",
        "--template-ref",
        help="Branch or tag of scaldys-template to download (e.g. 'v1.0.0').",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Overwrite target directory if it already exists.",
    ),
    no_git: bool = typer.Option(False, "--no-git", help="Skip git repository initialisation."),
    no_sync: bool = typer.Option(False, "--no-sync", help="Skip running 'uv sync' after creation."),
) -> None:
    """Create a new scaldys-template-based project interactively.

    Downloads the scaldys-template from GitHub (or uses --local PATH) and
    scaffolds a new project by substituting all placeholder names with the
    values you provide.
    """
    params = _collect_params()
    if no_git:
        params["init_git"] = False
    if no_sync:
        params["run_sync"] = False

    _print_summary(params)
    if not typer.confirm("Proceed?", default=True):
        logger.info("Aborted.")
        raise typer.Exit(0)

    target_dir = Path(params["target_dir"]).expanduser().resolve()

    if target_dir.exists():
        if not force:
            logger.error(
                f"[bold red]✗ Target directory already exists:[/bold red] {target_dir}\n"
                "  Use --force to overwrite."
            )
            raise typer.Exit(1)
        logger.warning(f"[yellow]Removing existing directory:[/yellow] {target_dir}")
        shutil.rmtree(target_dir)

    tmp_dir: Path | None = None
    try:
        if local is not None:
            if not local.is_dir():
                logger.error(f"[bold red]✗ Local path is not a directory:[/bold red] {local}")
                raise typer.Exit(1)
            template_src = local
        else:
            tmp_dir = Path(tempfile.mkdtemp())
            try:
                template_src = _download_template(template_ref, tmp_dir)
            except RuntimeError as exc:
                logger.error(f"[bold red]✗ Download failed:[/bold red] {exc}")
                raise typer.Exit(1) from exc

        replacements = _build_replacements(params)

        with console.status("[bold]Copying template…[/bold]"):
            _copy_filtered(template_src, target_dir)

        with console.status("[bold]Replacing template placeholders…[/bold]"):
            _replace_content(target_dir, replacements)

        with console.status("[bold]Renaming files and directories…[/bold]"):
            _rename_paths(target_dir, params["package_name"], params["project_slug"])

        with console.status("[bold]Applying final fixes…[/bold]"):
            _post_process(target_dir, params)

    except typer.Exit:
        # Clean up partial output on early exit
        if target_dir.exists():
            shutil.rmtree(target_dir, ignore_errors=True)
        raise
    finally:
        if tmp_dir is not None:
            shutil.rmtree(tmp_dir, ignore_errors=True)

    logger.info(f"[bold green]✓ Project created:[/bold green] {target_dir}")

    _run_post_init(target_dir, bool(params["init_git"]), bool(params["run_sync"]))

    from rich.panel import Panel

    next_steps = (
        f"  [bold]cd[/bold] {params['project_slug']}\n"
        f"  [bold]uv run scaldys-project check[/bold]   # verify project compliance\n"
        f"  [bold]uv run scaldys-project ci all[/bold]  # run full quality pipeline\n"
        f"\n"
        f"  Tip: 'uv run' uses the project-local .venv regardless of any\n"
        f"  currently activated environment."
    )
    console.print()
    console.print(
        Panel(next_steps, title="[bold green]✓ Done — next steps[/bold green]", expand=False)
    )
