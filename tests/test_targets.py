"""Tests for CLI target resolution in ``scaldys_project.cli.utils``."""

import pytest

from scaldys_project.cli.utils import TargetError, resolve_targets, workspace_root
from tests.conftest import make_member


def test_virtual_root_without_selection_lists_members(tmp_workspace, monkeypatch):
    """At a virtual root, no selection is an error that lists the members."""
    monkeypatch.chdir(tmp_workspace.root)
    with pytest.raises(TargetError, match="wsapp, wslib"):
        resolve_targets(None, False)


def test_all_packages_in_topological_order(tmp_workspace, monkeypatch):
    """--all-packages returns every member, libraries first."""
    monkeypatch.chdir(tmp_workspace.root)
    assert resolve_targets(None, True) == [tmp_workspace.lib, tmp_workspace.app]


def test_package_selection_is_reordered(tmp_workspace, monkeypatch):
    """--package values are validated and put in topological order."""
    monkeypatch.chdir(tmp_workspace.root)
    assert resolve_targets(["wsapp", "WSLib"], False) == [tmp_workspace.lib, tmp_workspace.app]


def test_unknown_package_is_an_error(tmp_workspace, monkeypatch):
    """An unknown --package name raises TargetError."""
    monkeypatch.chdir(tmp_workspace.root)
    with pytest.raises(TargetError, match="not a workspace member"):
        resolve_targets(["nope"], False)


def test_cwd_in_member_and_subfolder(tmp_workspace, monkeypatch):
    """Inside a member (or a subfolder of it), the member is the target."""
    monkeypatch.chdir(tmp_workspace.app)
    assert resolve_targets(None, False) == [tmp_workspace.app]
    monkeypatch.chdir(tmp_workspace.app / "src" / "wsapp")
    assert resolve_targets(None, False) == [tmp_workspace.app]
    # --package from a member still selects by name.
    assert resolve_targets(["wslib"], False) == [tmp_workspace.lib]


def test_no_workspace(tmp_path, monkeypatch):
    """Outside a workspace the project root is the target; --package is an error."""
    (tmp_path / "pyproject.toml").write_text('[project]\nname = "x"\nversion = "1"\n')
    (tmp_path / "sub").mkdir()
    monkeypatch.chdir(tmp_path / "sub")
    assert resolve_targets(None, False) == [tmp_path]
    assert workspace_root() == tmp_path
    with pytest.raises(TargetError):
        resolve_targets(["x"], False)
    with pytest.raises(TargetError):
        resolve_targets(None, True)


def test_workspace_root_from_member(tmp_workspace, monkeypatch):
    """workspace_root() is the workspace root, also from inside a member."""
    monkeypatch.chdir(tmp_workspace.lib)
    assert workspace_root() == tmp_workspace.root


def test_excluded_project_is_standalone(tmp_workspace, monkeypatch):
    """A project excluded from the workspace resolves as a standalone project."""
    root = tmp_workspace.root
    skip = make_member(root, "skip-me", version="1.0", mode="wheel_only")
    (root / "pyproject.toml").write_text(
        '[tool.uv.workspace]\nmembers = ["packages/*"]\nexclude = ["packages/skip*"]\n'
    )
    monkeypatch.chdir(skip)
    assert resolve_targets(None, False) == [skip]
