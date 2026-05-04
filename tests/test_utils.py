import tempfile
from pathlib import Path

import pytest

from scaldys_builder.common.utils import (
    safe_copy,
    safe_empty_dir,
    safe_rename,
    safe_unlink,
)


def test_safe_unlink_nonexistent_is_noop():
    """safe_unlink on a non-existent path does not raise."""
    safe_unlink(Path("/nonexistent/path/file.txt"))


def test_safe_unlink_removes_file():
    """safe_unlink deletes an existing file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        f = Path(tmpdir) / "test.txt"
        f.write_text("hello")
        safe_unlink(f)
        assert not f.exists()


def test_safe_empty_dir_creates_missing_directory():
    """safe_empty_dir creates the directory when it does not exist."""
    with tempfile.TemporaryDirectory() as tmpdir:
        target = Path(tmpdir) / "new_dir"
        assert not target.exists()
        safe_empty_dir(target)
        assert target.is_dir()


def test_safe_empty_dir_clears_contents():
    """safe_empty_dir removes all contents but keeps the directory itself."""
    with tempfile.TemporaryDirectory() as tmpdir:
        target = Path(tmpdir) / "some_dir"
        target.mkdir()
        (target / "file.txt").write_text("data")
        (target / "subdir").mkdir()
        safe_empty_dir(target)
        assert target.is_dir()
        assert list(target.iterdir()) == []


def test_safe_empty_dir_idempotent_on_empty_dir():
    """safe_empty_dir on an already-empty directory is a no-op."""
    with tempfile.TemporaryDirectory() as tmpdir:
        target = Path(tmpdir) / "empty"
        target.mkdir()
        safe_empty_dir(target)
        assert target.is_dir()
        assert list(target.iterdir()) == []


def test_safe_copy_copies_file():
    """safe_copy places an exact copy at the destination."""
    with tempfile.TemporaryDirectory() as tmpdir:
        src = Path(tmpdir) / "src.txt"
        dst = Path(tmpdir) / "dst.txt"
        src.write_text("content")
        safe_copy(src, dst)
        assert dst.exists()
        assert dst.read_text() == "content"


def test_safe_rename_moves_file():
    """safe_rename moves a file to the destination path."""
    with tempfile.TemporaryDirectory() as tmpdir:
        src = Path(tmpdir) / "original.txt"
        dst = Path(tmpdir) / "renamed.txt"
        src.write_text("data")
        safe_rename(src, dst)
        assert not src.exists()
        assert dst.read_text() == "data"


def test_safe_rename_overwrites_existing_destination():
    """safe_rename removes an existing destination before renaming."""
    with tempfile.TemporaryDirectory() as tmpdir:
        src = Path(tmpdir) / "new.txt"
        dst = Path(tmpdir) / "old.txt"
        src.write_text("new content")
        dst.write_text("old content")
        safe_rename(src, dst)
        assert not src.exists()
        assert dst.read_text() == "new content"
