"""
uv workspace discovery for scaldys-project.

A uv workspace is a directory whose ``pyproject.toml`` contains a
``[tool.uv.workspace]`` table.  Its ``members`` globs (minus ``exclude``)
select the member projects; the root itself is a member when it also has a
``[project]`` table, otherwise it is a *virtual* root.

This module only reads metadata.  It never runs uv.
"""

import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from packaging.requirements import InvalidRequirement, Requirement
from packaging.specifiers import SpecifierSet
from packaging.utils import canonicalize_name

PRIVATE_CLASSIFIER = "Private :: Do Not Upload"


class WorkspaceError(RuntimeError):
    """Raised for an inconsistent workspace (dependency cycle, unknown member)."""


@dataclass(frozen=True)
class Member:
    """
    One project of a uv workspace.

    Attributes
    ----------
    name : str
        The ``[project] name`` as written in ``pyproject.toml``.
    path : Path
        The member directory (resolved).
    version : str
        The ``[project] version``.
    package_name : str
        The import package name (``name`` with hyphens replaced by underscores).
    internal_deps : dict of str to SpecifierSet or None
        Dependencies on other workspace members, keyed by canonical name.  The
        value is the version constraint, or ``None`` when there is none.
    private : bool
        ``True`` when the ``Private :: Do Not Upload`` classifier is set.
    """

    name: str
    path: Path
    version: str
    package_name: str
    internal_deps: dict[str, SpecifierSet | None] = field(default_factory=dict)
    private: bool = False

    @property
    def key(self) -> str:
        """The canonical (PEP 503) name used to index members."""
        return canonicalize_name(self.name)


@dataclass
class Workspace:
    """
    A uv workspace: its root directory and its members.

    Attributes
    ----------
    root : Path
        The directory holding the ``pyproject.toml`` with ``[tool.uv.workspace]``.
    members : dict of str to Member
        Members keyed by canonical name, in discovery order.
    is_virtual_root : bool
        ``True`` when the root ``pyproject.toml`` has no ``[project]`` table.
    """

    root: Path
    members: dict[str, Member]
    is_virtual_root: bool

    def get(self, name: str) -> Member | None:
        """Return the member called *name* (any spelling), or ``None``."""
        return self.members.get(canonicalize_name(name))

    def member_at(self, path: Path) -> Member | None:
        """Return the member whose directory is *path*, or ``None``."""
        resolved = path.resolve()
        for member in self.members.values():
            if member.path == resolved:
                return member
        return None

    def topological_order(self, names: list[str] | None = None) -> list[str]:
        """
        Return member keys ordered so that dependencies come before dependents.

        Parameters
        ----------
        names : list of str, optional
            The members to order (any spelling).  ``None`` orders all members.

        Returns
        -------
        list of str
            Canonical member names, libraries first.  Ties keep discovery order.

        Raises
        ------
        WorkspaceError
            If a name is not a member, or the dependency graph has a cycle.
        """
        order: list[str] = []
        state: dict[str, int] = {}  # 1 = visiting, 2 = done

        def visit(key: str, chain: list[str]) -> None:
            if state.get(key) == 2:
                return
            if state.get(key) == 1:
                cycle = " -> ".join([*chain[chain.index(key) :], key])
                raise WorkspaceError(f"Dependency cycle between workspace members: {cycle}")
            state[key] = 1
            for dep in self.members[key].internal_deps:
                visit(dep, [*chain, key])
            state[key] = 2
            order.append(key)

        for key in self.members:
            visit(key, [])

        if names is None:
            return order
        wanted = set()
        for name in names:
            key = canonicalize_name(name)
            if key not in self.members:
                raise WorkspaceError(
                    f"'{name}' is not a workspace member. Members: {', '.join(self.member_names())}"
                )
            wanted.add(key)
        return [key for key in order if key in wanted]

    def internal_closure(self, name: str) -> list[str]:
        """
        Return the transitive internal dependencies of *name*, in topological order.

        The member itself is not included.
        """
        root_key = canonicalize_name(name)
        if root_key not in self.members:
            raise WorkspaceError(f"'{name}' is not a workspace member.")
        seen: set[str] = set()
        stack = list(self.members[root_key].internal_deps)
        while stack:
            key = stack.pop()
            if key in seen:
                continue
            seen.add(key)
            stack.extend(self.members[key].internal_deps)
        seen.discard(root_key)
        return self.topological_order(sorted(seen)) if seen else []

    def member_names(self) -> list[str]:
        """Return the members' ``[project] name`` values, in discovery order."""
        return [m.name for m in self.members.values()]


def _load_toml(path: Path) -> dict[str, Any]:
    with open(path, "rb") as f:
        return tomllib.load(f)


def _workspace_sources(data: dict[str, Any]) -> set[str]:
    """Return the canonical names with a ``{ workspace = true }`` source in *data*."""
    sources = data.get("tool", {}).get("uv", {}).get("sources", {})
    names: set[str] = set()
    for name, spec in sources.items():
        specs = spec if isinstance(spec, list) else [spec]
        if any(isinstance(s, dict) and s.get("workspace") is True for s in specs):
            names.add(canonicalize_name(name))
    return names


def _read_member(path: Path, data: dict[str, Any], root_sources: set[str]) -> Member:
    project = data["project"]
    ws_names = _workspace_sources(data) | root_sources
    internal: dict[str, SpecifierSet | None] = {}
    for dep in project.get("dependencies", []):
        try:
            req = Requirement(dep)
        except InvalidRequirement:
            continue
        key = canonicalize_name(req.name)
        if key in ws_names:
            internal[key] = req.specifier if str(req.specifier) else None
    return Member(
        name=project["name"],
        path=path.resolve(),
        version=str(project.get("version", "")),
        package_name=project["name"].replace("-", "_"),
        internal_deps=internal,
        private=PRIVATE_CLASSIFIER in project.get("classifiers", []),
    )


def load_workspace(root: Path) -> Workspace:
    """
    Read the workspace whose root is *root*.

    Raises
    ------
    WorkspaceError
        If *root* has no ``[tool.uv.workspace]`` table.
    """
    root = root.resolve()
    data = _load_toml(root / "pyproject.toml")
    ws_cfg = data.get("tool", {}).get("uv", {}).get("workspace")
    if ws_cfg is None:
        raise WorkspaceError(f"'{root / 'pyproject.toml'}' has no [tool.uv.workspace] table.")

    excluded: set[Path] = set()
    for pattern in ws_cfg.get("exclude", []):
        excluded.update(p.resolve() for p in root.glob(pattern))

    candidates: list[Path] = []
    if "project" in data:
        candidates.append(root)
    for pattern in ws_cfg.get("members", []):
        for p in sorted(root.glob(pattern)):
            p = p.resolve()
            if (
                p.is_dir()
                and p not in excluded
                and p not in candidates
                and (p / "pyproject.toml").is_file()
            ):
                candidates.append(p)

    root_sources = _workspace_sources(data)
    members: dict[str, Member] = {}
    for path in candidates:
        member_data = data if path == root else _load_toml(path / "pyproject.toml")
        if "project" not in member_data or "name" not in member_data["project"]:
            continue
        member = _read_member(path, member_data, root_sources)
        members[member.key] = member

    # Keep only dependencies that are actual members.
    for key, member in list(members.items()):
        deps = {k: v for k, v in member.internal_deps.items() if k in members and k != key}
        if deps != member.internal_deps:
            members[key] = Member(
                name=member.name,
                path=member.path,
                version=member.version,
                package_name=member.package_name,
                internal_deps=deps,
                private=member.private,
            )

    return Workspace(root=root, members=members, is_virtual_root="project" not in data)


def find_workspace_root(start: Path) -> Path | None:
    """Return the nearest directory at or above *start* with ``[tool.uv.workspace]``."""
    start = start.resolve()
    for candidate in [start, *start.parents]:
        pyproject = candidate / "pyproject.toml"
        if not pyproject.is_file():
            continue
        try:
            data = _load_toml(pyproject)
        except (OSError, tomllib.TOMLDecodeError):
            continue
        if "workspace" in data.get("tool", {}).get("uv", {}):
            return candidate
    return None


def _nearest_project(start: Path) -> Path | None:
    for candidate in [start, *start.parents]:
        if (candidate / "pyproject.toml").is_file():
            return candidate
    return None


def find_workspace(start: Path) -> Workspace | None:
    """
    Return the uv workspace that *start* belongs to, or ``None``.

    *start* belongs to the workspace when its nearest project directory is the
    workspace root or one of its members.  A project inside the workspace tree
    that is not a member (for example an excluded one) is not part of it.
    """
    start = start.resolve()
    root = find_workspace_root(start)
    if root is None:
        return None
    workspace = load_workspace(root)
    nearest = _nearest_project(start)
    if nearest is None:
        return None
    nearest = nearest.resolve()
    if nearest != workspace.root and workspace.member_at(nearest) is None:
        return None
    return workspace
