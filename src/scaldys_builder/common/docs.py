import logging
from enum import Enum
from pathlib import Path

from scaldys_builder.common.base import BaseBuildEnvironment
from scaldys_builder.common.utils import safe_empty_dir

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

    def _run_apidoc(self, doc_dir: Path) -> None:
        """
        Run ``sphinx-apidoc`` on the project source, writing RST output into ``doc_dir/source/``.

        Parameters
        ----------
        doc_dir : Path
            The documentation unit directory (e.g. ``docs/developer_guide``).
        """
        source_dir = str(self.env.src_dir_path)
        output_dir = str(doc_dir.joinpath("source"))
        logger.info("  Running sphinx-apidoc...")
        self.env.run_command(
            [str(self.env.sphinx_apidoc_exe_path), "-f", "-o", output_dir, source_dir],
            f"Error running sphinx-apidoc for '{doc_dir.name}'",
        )

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
            logger.info(f"  Building {builder_name} ({doc_dir.name})...")
            self.env.run_command(
                [str(self.env.sphinx_exe_path), "-b", builder_name, source_dir, out],
                f"Error running sphinx-build -{builder_name} for '{doc_dir.name}'",
                cwd=doc_dir,
            )

    def _build_one(self, doc_dir: Path) -> None:
        """
        Build a single documentation unit.

        Detects the engine, optionally runs sphinx-apidoc (if configured in
        ``builder.toml`` ``[docs] apidoc_dirs``), then builds.  Logs a warning
        and returns without building for unknown or unsupported engines.

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

        if dir_name in self.env.config.docs.apidoc_dirs:
            self._run_apidoc(doc_dir)

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
