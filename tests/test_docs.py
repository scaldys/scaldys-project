import logging
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

from scaldys_project.common.docs import (
    DocEngine,
    DocumentationBuilder,
    _detect_engine,
    get_markdown_target_files,
)

# ---------------------------------------------------------------------------
# _detect_engine
# ---------------------------------------------------------------------------


def test_detect_engine_sphinx():
    """_detect_engine returns SPHINX when source/conf.py exists."""
    with tempfile.TemporaryDirectory() as tmpdir:
        doc_dir = Path(tmpdir)
        (doc_dir / "source").mkdir()
        (doc_dir / "source" / "conf.py").touch()
        assert _detect_engine(doc_dir) == DocEngine.SPHINX


def test_detect_engine_mkdocs():
    """_detect_engine returns MKDOCS when mkdocs.yml exists."""
    with tempfile.TemporaryDirectory() as tmpdir:
        doc_dir = Path(tmpdir)
        (doc_dir / "mkdocs.yml").touch()
        assert _detect_engine(doc_dir) == DocEngine.MKDOCS


def test_detect_engine_unknown():
    """_detect_engine returns UNKNOWN for an empty directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        assert _detect_engine(Path(tmpdir)) == DocEngine.UNKNOWN


def test_detect_engine_sphinx_takes_priority_over_mkdocs():
    """_detect_engine returns SPHINX when both source/conf.py and mkdocs.yml are present."""
    with tempfile.TemporaryDirectory() as tmpdir:
        doc_dir = Path(tmpdir)
        (doc_dir / "source").mkdir()
        (doc_dir / "source" / "conf.py").touch()
        (doc_dir / "mkdocs.yml").touch()
        assert _detect_engine(doc_dir) == DocEngine.SPHINX


# ---------------------------------------------------------------------------
# DocumentationBuilder.build() — using a stub env (no subprocess)
# ---------------------------------------------------------------------------


def _make_env(docs_dir: Path, build_dir: Path) -> MagicMock:
    """Return a minimal mock BaseBuildEnvironment."""
    env = MagicMock()
    env.docs_dir_path = docs_dir
    env.build_dir_path = build_dir
    env.run_command.return_value = ("", "")
    return env


def test_build_warns_and_skips_when_docs_root_missing(caplog):
    """build() logs a warning and does not raise when docs/ does not exist."""
    with tempfile.TemporaryDirectory() as tmpdir:
        docs_dir = Path(tmpdir) / "docs"  # does not exist
        build_dir = Path(tmpdir) / "build"
        env = _make_env(docs_dir, build_dir)
        builder = DocumentationBuilder(env)
        with caplog.at_level(logging.WARNING):
            builder.build()
    assert any("not found" in r.message for r in caplog.records)
    env.run_command.assert_not_called()


def test_build_warns_and_skips_when_docs_root_empty(caplog):
    """build() logs a warning when docs/ exists but has no subdirectories."""
    with tempfile.TemporaryDirectory() as tmpdir:
        docs_dir = Path(tmpdir) / "docs"
        docs_dir.mkdir()
        build_dir = Path(tmpdir) / "build"
        env = _make_env(docs_dir, build_dir)
        builder = DocumentationBuilder(env)
        with caplog.at_level(logging.WARNING):
            builder.build()
    assert any("Nothing to build" in r.message for r in caplog.records)
    env.run_command.assert_not_called()


def test_build_warns_and_skips_unknown_engine(caplog):
    """build() warns and skips subdirectories with no recognised engine."""
    with tempfile.TemporaryDirectory() as tmpdir:
        docs_dir = Path(tmpdir) / "docs"
        docs_dir.mkdir()
        (docs_dir / "unknown_dir").mkdir()  # no conf.py, no mkdocs.yml
        build_dir = Path(tmpdir) / "build"
        env = _make_env(docs_dir, build_dir)
        builder = DocumentationBuilder(env)
        with caplog.at_level(logging.WARNING):
            builder.build()
    assert any("no recognised engine" in r.message for r in caplog.records)
    env.run_command.assert_not_called()


def test_build_warns_and_skips_mkdocs(caplog):
    """build() warns and skips MkDocs directories (not yet supported)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        docs_dir = Path(tmpdir) / "docs"
        docs_dir.mkdir()
        mkdocs_dir = docs_dir / "site"
        mkdocs_dir.mkdir()
        (mkdocs_dir / "mkdocs.yml").touch()
        build_dir = Path(tmpdir) / "build"
        env = _make_env(docs_dir, build_dir)
        builder = DocumentationBuilder(env)
        with caplog.at_level(logging.WARNING):
            builder.build()
    assert any("MkDocs" in r.message for r in caplog.records)
    env.run_command.assert_not_called()


def test_build_sphinx_calls_sphinx_build(caplog):
    """build() calls run_command for html and singlehtml when Sphinx is detected."""
    with tempfile.TemporaryDirectory() as tmpdir:
        docs_dir = Path(tmpdir) / "docs"
        docs_dir.mkdir()
        manual_dir = docs_dir / "manual"
        manual_dir.mkdir()
        (manual_dir / "source").mkdir()
        (manual_dir / "source" / "conf.py").touch()
        build_dir = Path(tmpdir) / "build"
        env = _make_env(docs_dir, build_dir)
        builder = DocumentationBuilder(env)
        builder.build()
    # Two sphinx-build calls: html and singlehtml
    assert env.run_command.call_count == 2


# ---------------------------------------------------------------------------
# get_markdown_target_files
# ---------------------------------------------------------------------------


def test_get_markdown_target_files_empty():
    """Returns empty list when project root has no README.md or MkDocs docs."""
    with tempfile.TemporaryDirectory() as tmpdir:
        assert get_markdown_target_files(Path(tmpdir)) == []


def test_get_markdown_target_files_readme_only():
    """Discovers README.md and ignores RELEASES.md and other root files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        (root / "README.md").touch()
        (root / "RELEASES.md").touch()
        (root / "ideas.md").touch()
        (root / "licenses").mkdir()
        (root / "licenses" / "README.md").touch()

        targets = get_markdown_target_files(root)
        assert targets == [Path("README.md")]


def test_get_markdown_target_files_mkdocs_subdirectories():
    """Discovers README.md and .md files in MkDocs doc subdirectories, ignoring Sphinx doc markdown."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        (root / "README.md").touch()
        (root / "RELEASES.md").touch()

        docs_dir = root / "docs"
        docs_dir.mkdir()

        # MkDocs unit
        site_dir = docs_dir / "site"
        site_dir.mkdir()
        (site_dir / "mkdocs.yml").touch()
        (site_dir / "index.md").touch()
        sub_dir = site_dir / "sub"
        sub_dir.mkdir()
        (sub_dir / "page.md").touch()

        # Sphinx unit
        manual_dir = docs_dir / "manual"
        manual_dir.mkdir()
        (manual_dir / "source").mkdir()
        (manual_dir / "source" / "conf.py").touch()
        (manual_dir / "source" / "notes.md").touch()

        targets = get_markdown_target_files(root)
        expected = [
            Path("README.md"),
            Path("docs/site/index.md"),
            Path("docs/site/sub/page.md"),
        ]
        assert targets == expected


def test_get_markdown_target_files_mkdocs_at_docs_root():
    """Discovers .md files when mkdocs.yml is directly inside docs/."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        docs_dir = root / "docs"
        docs_dir.mkdir()
        (docs_dir / "mkdocs.yml").touch()
        (docs_dir / "index.md").touch()

        targets = get_markdown_target_files(root)
        assert targets == [Path("docs/index.md")]


def test_get_markdown_target_files_explicit_targets():
    """Resolves specific markdown files and scans directories recursively when configured."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        (root / "README.md").touch()
        (root / "ideas.md").touch()
        (root / "improvements.md").touch()

        notes_dir = root / "notes"
        notes_dir.mkdir()
        (notes_dir / "draft1.md").touch()
        (notes_dir / "sub").mkdir()
        (notes_dir / "sub" / "draft2.md").touch()
        (notes_dir / "sub" / "ignored.txt").touch()

        (root / "scaldys-project.toml").write_text(
            '[format]\nmarkdown_targets = ["README.md", "notes", "ideas.md"]\n'
        )

        targets = get_markdown_target_files(root)
        expected = [
            Path("README.md"),
            Path("ideas.md"),
            Path("notes/draft1.md"),
            Path("notes/sub/draft2.md"),
        ]
        assert targets == expected


def test_get_markdown_target_files_explicit_empty_list():
    """Returns empty list when markdown_targets is explicitly set to []."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        (root / "README.md").touch()
        (root / "scaldys-project.toml").write_text("[format]\nmarkdown_targets = []\n")

        targets = get_markdown_target_files(root)
        assert targets == []
