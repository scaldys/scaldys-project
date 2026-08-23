import logging
from enum import Enum
from pathlib import Path

from scaldys_project.common.base import BaseBuildEnvironment
from scaldys_project.common.config import BuildConfig, FormatConfig, load_config
from scaldys_project.common.utils import safe_empty_dir

logger = logging.getLogger(__name__)


class DocEngine(Enum):
    """Documentation engine detected for a docs subdirectory."""

    SPHINX = "sphinx"
    MKDOCS = "mkdocs"
    UNKNOWN = "unknown"


def _detect_engine(doc_dir: Path) -> DocEngine:
    """
    Detect the documentation engine for a docs subdirectory by inspecting its contents.

    Parameters
    ----------
    doc_dir : Path
        A subdirectory under the project's ``docs/`` folder.

    Returns
    -------
    DocEngine
        - ``SPHINX`` if ``source/conf.py`` is present.
        - ``MKDOCS`` if ``mkdocs.yml`` is present.
        - ``UNKNOWN`` if neither marker is found.
    """
    if doc_dir.joinpath("source", "conf.py").exists():
        return DocEngine.SPHINX
    if doc_dir.joinpath("mkdocs.yml").exists():
        return DocEngine.MKDOCS
    return DocEngine.UNKNOWN


def get_markdown_target_files(
    project_root: Path | None = None,
    config: FormatConfig | BuildConfig | None = None,
) -> list[Path]:
    """
    Discover all target Markdown files for formatting and CI checks.

    When ``config`` or its ``markdown_targets`` is ``None``, falls back to default
    auto-discovery:
    - ``README.md`` in the project root if it exists.
    - All ``*.md`` files under ``docs/`` subdirectories where MkDocs is detected
      (or directly under ``docs/`` if ``docs/mkdocs.yml`` is present).
    - Excludes ``RELEASES.md`` and non-MkDocs doc directories.

    When ``markdown_targets`` is configured:
    - If empty (``[]``), returns an empty list.
    - If specified, resolves all given files and recursively searches specified
      directories for ``*.md`` files.

    Parameters
    ----------
    project_root : Path | None
        The root directory of the project (defaults to ``Path.cwd()``).
    config : FormatConfig | BuildConfig | None
        Configuration containing formatting settings. If ``None``, configuration
        is loaded from ``scaldys-project.toml`` at ``project_root``.

    Returns
    -------
    list[Path]
        Sorted list of unique target Markdown file paths (relative to ``project_root``).
    """
    if project_root is None:
        project_root = Path.cwd()

    format_config: FormatConfig
    if config is None:
        format_config = load_config(project_root).format
    elif isinstance(config, BuildConfig):
        format_config = config.format
    else:
        format_config = config

    targets: list[Path] = []

    if format_config.markdown_targets is not None:
        if not format_config.markdown_targets:
            return []

        for target_str in format_config.markdown_targets:
            target_path = project_root / target_str
            if target_path.is_file():
                targets.append(target_path)
            elif target_path.is_dir():
                targets.extend(p for p in target_path.rglob("*.md") if p.is_file())
    else:
        readme = project_root / "README.md"
        if readme.is_file():
            targets.append(readme)

        docs_root = project_root / "docs"
        if docs_root.is_dir():
            if _detect_engine(docs_root) == DocEngine.MKDOCS:
                targets.extend(p for p in docs_root.rglob("*.md") if p.is_file())
            else:
                for doc_dir in sorted(p for p in docs_root.iterdir() if p.is_dir()):
                    if _detect_engine(doc_dir) == DocEngine.MKDOCS:
                        targets.extend(p for p in doc_dir.rglob("*.md") if p.is_file())

    resolved_root = project_root.resolve()
    unique_paths = list(
        {
            p.resolve().relative_to(resolved_root)
            for p in targets
            if (format_config.markdown_targets is not None or p.name != "RELEASES.md")
        }
    )
    return sorted(
        unique_paths,
        key=lambda p: (0 if p == Path("README.md") else 1, p.as_posix().lower()),
    )


def check_ci_markdown_drift(
    project_root: Path | None = None,
    config: FormatConfig | BuildConfig | None = None,
) -> str | None:
    """
    Check for discrepancies between configured markdown targets and CI workflow arguments.

    Parses ``.github/workflows/ci.yml`` if it exists and checks whether the arguments
    passed to ``mdformat`` in the workflow match the targets defined in configuration.

    Parameters
    ----------
    project_root : Path | None
        The root directory of the project (defaults to ``Path.cwd()``).
    config : FormatConfig | BuildConfig | None
        Configuration containing formatting settings.

    Returns
    -------
    str | None
        A descriptive warning message if drift is detected; ``None`` if targets match
        or if no CI workflow file / mdformat step is found.
    """
    if project_root is None:
        project_root = Path.cwd()

    workflow_file = project_root / ".github" / "workflows" / "ci.yml"
    if not workflow_file.is_file():
        return None

    try:
        content = workflow_file.read_text(encoding="utf-8")
    except OSError:
        return None

    workflow_targets: list[str] | None = None
    for line in content.splitlines():
        if "mdformat" in line:
            parts = line.strip().split()
            if "mdformat" in parts:
                idx = parts.index("mdformat")
                args = parts[idx + 1 :]
                targets = [
                    Path(arg).as_posix()
                    for arg in args
                    if not arg.startswith("-") and arg not in (">", "|")
                ]
                workflow_targets = targets
                break

    if workflow_targets is None:
        return None

    format_config: FormatConfig
    if config is None:
        format_config = load_config(project_root).format
    elif isinstance(config, BuildConfig):
        format_config = config.format
    else:
        format_config = config

    expected_targets: list[str]
    if format_config.markdown_targets is not None:
        expected_targets = [Path(t).as_posix() for t in format_config.markdown_targets]
    else:
        target_files = get_markdown_target_files(project_root, config=format_config)
        expected_targets = [p.as_posix() for p in target_files]

    if sorted(workflow_targets) != sorted(expected_targets):
        return (
            f"CI workflow (.github/workflows/ci.yml) markdown targets {workflow_targets} "
            f"differ from configured targets {expected_targets}."
        )

    return None


class DocumentationBuilder:
    """
    Handles documentation generation for all doc units found under ``docs/``.

    Each immediate subdirectory of ``docs/`` is treated as an independent
    documentation unit.  The engine used to build each unit is auto-detected
    from its contents (see ``_detect_engine``).

    Currently supported engines:
    - **Sphinx** — detected by the presence of ``source/conf.py``.

    Currently unsupported (detected but skipped with a warning):
    - **MkDocs** — detected by the presence of ``mkdocs.yml``.
    """

    def __init__(self, env: BaseBuildEnvironment) -> None:
        """
        Initialize the documentation builder.

        Parameters
        ----------
        env : BaseBuildEnvironment
            The build environment configuration.
        """
        self.env = env

    def _build_sphinx(self, doc_dir: Path, build_dir: Path) -> None:
        """
        Run ``sphinx-build`` for ``html`` and ``singlehtml`` targets.

        Parameters
        ----------
        doc_dir : Path
            The documentation unit directory (e.g. ``docs/manual``).
        build_dir : Path
            The output build directory (e.g. ``build/manual``).
        """
        safe_empty_dir(build_dir)
        source_dir = str(doc_dir.joinpath("source"))

        for builder_name in ("html", "singlehtml"):
            out = str(build_dir.joinpath(builder_name))
            logger.info(f"  [green]\u25ba[/green] Building {builder_name} ({doc_dir.name})...")
            self.env.run_command(
                [str(self.env.sphinx_exe_path), "-b", builder_name, source_dir, out],
                f"Error running sphinx-build -{builder_name} for '{doc_dir.name}'",
                cwd=doc_dir,
            )

    def _build_one(self, doc_dir: Path) -> None:
        """
        Build a single documentation unit.

        Detects the engine, then builds.  Logs a warning and returns without
        building for unknown or unsupported engines.

        Parameters
        ----------
        doc_dir : Path
            A subdirectory under the project's ``docs/`` folder.
        """
        dir_name = doc_dir.name
        engine = _detect_engine(doc_dir)

        if engine == DocEngine.UNKNOWN:
            logger.warning(
                f"Documentation directory '{dir_name}' has no recognised engine "
                f"(no source/conf.py or mkdocs.yml). Skipping."
            )
            return

        if engine == DocEngine.MKDOCS:
            logger.warning(
                f"Documentation directory '{dir_name}' uses MkDocs, "
                f"which is not yet supported. Skipping."
            )
            return

        # SPHINX path
        build_dir = self.env.build_dir_path / dir_name
        logger.info(f"[bold]Building Sphinx documentation: '{dir_name}'...[/bold]")
        self._build_sphinx(doc_dir, build_dir)

    def build(self) -> None:
        """
        Build all documentation units found under ``docs/``.

        Iterates every immediate subdirectory of ``docs_dir_path`` in sorted
        order, detects the engine for each, and builds it.  Subdirectories
        with unrecognised engines produce a warning and are skipped.

        If ``docs/`` does not exist or contains no subdirectories, a warning
        is logged and the method returns without error.
        """
        docs_root = self.env.docs_dir_path
        if not docs_root.is_dir():
            logger.warning(f"Documentation directory not found: '{docs_root}'. Skipping.")
            return

        doc_dirs = sorted(p for p in docs_root.iterdir() if p.is_dir())
        if not doc_dirs:
            logger.warning(f"No subdirectories found in '{docs_root}'. Nothing to build.")
            return

        for doc_dir in doc_dirs:
            self._build_one(doc_dir)
