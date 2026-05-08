import logging
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

from scaldys_builder.common.docs import DocEngine, DocumentationBuilder, _detect_engine


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


def _make_env(docs_dir: Path, build_dir: Path, apidoc_dirs: list[str] | None = None) -> MagicMock:
    """Return a minimal mock BaseBuildEnvironment."""
    env = MagicMock()
    env.docs_dir_path = docs_dir
    env.build_dir_path = build_dir
    env.config.docs.apidoc_dirs = apidoc_dirs or []
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


def test_build_sphinx_apidoc_calls_apidoc_then_sphinx_build(caplog):
    """build() runs sphinx-apidoc before sphinx-build for apidoc_dirs entries."""
    with tempfile.TemporaryDirectory() as tmpdir:
        docs_dir = Path(tmpdir) / "docs"
        docs_dir.mkdir()
        dev_dir = docs_dir / "developer_guide"
        dev_dir.mkdir()
        (dev_dir / "source").mkdir()
        (dev_dir / "source" / "conf.py").touch()
        build_dir = Path(tmpdir) / "build"
        env = _make_env(docs_dir, build_dir, apidoc_dirs=["developer_guide"])
        builder = DocumentationBuilder(env)
        builder.build()
    # Three calls: sphinx-apidoc + html + singlehtml
    assert env.run_command.call_count == 3
