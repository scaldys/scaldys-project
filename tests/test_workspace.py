"""Tests for uv workspace discovery in ``scaldys_project.common.workspace``."""

from pathlib import Path

import pytest
from packaging.specifiers import SpecifierSet

from scaldys_project.common.workspace import (
    WorkspaceError,
    find_workspace,
    find_workspace_root,
    load_workspace,
)
from tests.conftest import make_member


def test_find_workspace_from_root_member_and_subfolder(tmp_workspace):
    """The workspace is found from its root, from a member and from a member subfolder."""
    for start in [tmp_workspace.root, tmp_workspace.app, tmp_workspace.app / "src" / "wsapp"]:
        ws = find_workspace(start)
        assert ws is not None
        assert ws.root == tmp_workspace.root
    ws = find_workspace(tmp_workspace.root)
    assert ws is not None
    assert ws.is_virtual_root
    assert ws.member_names() == ["wsapp", "wslib"]  # sorted path discovery order


def test_find_workspace_none_for_standalone(tmp_path):
    """A standalone project is not part of any workspace."""
    (tmp_path / "pyproject.toml").write_text('[project]\nname = "x"\nversion = "1"\n')
    assert find_workspace(tmp_path) is None
    assert find_workspace_root(tmp_path) is None


def test_member_globs_and_exclude(tmp_workspace):
    """exclude globs remove members; directories without pyproject.toml are ignored."""
    root = tmp_workspace.root
    make_member(root, "skip-me", version="1.0", mode="wheel_only")
    (root / "packages" / "not-a-project").mkdir()
    (root / "pyproject.toml").write_text(
        '[tool.uv.workspace]\nmembers = ["packages/*"]\nexclude = ["packages/skip*"]\n'
    )
    ws = load_workspace(root)
    assert sorted(ws.members) == ["wsapp", "wslib"]
    # A project in the tree that is excluded is not part of the workspace.
    assert find_workspace(root / "packages" / "skip-me") is None


def test_non_virtual_root_is_a_member(tmp_workspace):
    """A root pyproject.toml with [project] makes the root itself a member."""
    root = tmp_workspace.root
    (root / "pyproject.toml").write_text(
        '[project]\nname = "ws-root"\nversion = "1.0"\n\n'
        '[tool.uv.workspace]\nmembers = ["packages/*"]\n'
    )
    ws = load_workspace(root)
    assert not ws.is_virtual_root
    assert ws.members["ws-root"].path == root
    assert ws.member_at(root) is ws.members["ws-root"]


def test_internal_deps_from_member_sources(tmp_workspace):
    """A dependency with a workspace source in the member's own sources is internal."""
    ws = load_workspace(tmp_workspace.root)
    app = ws.members["wsapp"]
    assert app.internal_deps == {"wslib": SpecifierSet(">=0.1")}
    assert ws.members["wslib"].internal_deps == {}


def test_internal_deps_from_root_sources_and_no_constraint(tmp_workspace):
    """Root [tool.uv.sources] also count; a bare name has constraint None."""
    root = tmp_workspace.root
    make_member(root, "wsplugin", version="0.3", mode="wheel_only", dependencies=["WSLib"])
    (root / "pyproject.toml").write_text(
        '[tool.uv.workspace]\nmembers = ["packages/*"]\n\n'
        "[tool.uv.sources]\nwslib = { workspace = true }\n"
    )
    ws = load_workspace(root)
    assert ws.members["wsplugin"].internal_deps == {"wslib": None}


def test_external_dependency_is_not_internal(tmp_workspace):
    """A dependency without a workspace source is external, even if a member has its name."""
    root = tmp_workspace.root
    make_member(root, "wsother", version="1.0", mode="wheel_only", dependencies=["wslib", "rich"])
    ws = load_workspace(root)
    assert ws.members["wsother"].internal_deps == {}


def test_topological_order_and_closure(tmp_workspace):
    """Libraries come first; the closure is transitive and excludes the member itself."""
    root = tmp_workspace.root
    make_member(
        root,
        "wstop",
        version="1.0",
        mode="pyinstaller",
        dependencies=["wsapp>=0.2"],
        workspace_sources=["wsapp"],
    )
    ws = load_workspace(root)
    assert ws.topological_order() == ["wslib", "wsapp", "wstop"]
    assert ws.topological_order(["wstop", "wslib"]) == ["wslib", "wstop"]
    assert ws.internal_closure("wstop") == ["wslib", "wsapp"]
    assert ws.internal_closure("wslib") == []


def test_topological_order_unknown_name(tmp_workspace):
    """An unknown member name raises WorkspaceError listing the members."""
    ws = load_workspace(tmp_workspace.root)
    with pytest.raises(WorkspaceError, match="Members: wsapp, wslib"):
        ws.topological_order(["nope"])


def test_cycle_raises(tmp_workspace):
    """A dependency cycle between members raises WorkspaceError."""
    lib_pyproject = Path(tmp_workspace.lib / "pyproject.toml")
    text = lib_pyproject.read_text().replace("dependencies = []", 'dependencies = ["wsapp"]') + (
        "\n[tool.uv.sources]\nwsapp = { workspace = true }\n"
    )
    lib_pyproject.write_text(text)
    ws = load_workspace(tmp_workspace.root)
    with pytest.raises(WorkspaceError, match="cycle"):
        ws.topological_order()


def test_private_classifier(tmp_workspace):
    """The 'Private :: Do Not Upload' classifier marks a member private."""
    root = tmp_workspace.root
    make_member(
        root,
        "wsprivate",
        version="1.0",
        mode="pyinstaller",
        extra_project='classifiers = ["Private :: Do Not Upload"]\n',
    )
    ws = load_workspace(root)
    assert ws.members["wsprivate"].private
    assert not ws.members["wslib"].private
