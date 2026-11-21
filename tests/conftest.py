"""Shared fixtures for the scaldys-project test suite."""

from pathlib import Path
from types import SimpleNamespace

import pytest

from scaldys_project.windows.builder import reset_built_wheels


@pytest.fixture(autouse=True)
def _fresh_wheel_cache():
    """Each test starts with an empty per-process internal-wheel cache."""
    reset_built_wheels()
    yield
    reset_built_wheels()


def _write(path: Path, text: str = "") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def make_member(
    root: Path,
    name: str,
    *,
    version: str,
    mode: str,
    dependencies: list[str] | None = None,
    workspace_sources: list[str] | None = None,
    main: bool = False,
    extra_project: str = "",
) -> Path:
    """Create a workspace member under ``root/packages/<name>`` and return its path."""
    path = root / "packages" / name
    pkg = name.replace("-", "_")
    deps = ", ".join(f'"{d}"' for d in dependencies or [])
    text = (
        "[project]\n"
        f'name = "{name}"\n'
        f'version = "{version}"\n'
        'requires-python = ">=3.13"\n'
        f"dependencies = [{deps}]\n"
        f"{extra_project}"
        "\n[build-system]\n"
        'requires = ["setuptools"]\n'
        'build-backend = "setuptools.build_meta"\n'
    )
    if workspace_sources:
        text += "\n[tool.uv.sources]\n" + "".join(
            f"{s} = {{ workspace = true }}\n" for s in workspace_sources
        )
    _write(path / "pyproject.toml", text)
    _write(path / "src" / pkg / "__init__.py", "")
    if main:
        _write(path / "src" / pkg / "__main__.py", "print('hello')\n")
    _write(path / "tests" / "test_dummy.py", "def test_ok():\n    pass\n")
    _write(path / "scaldys-project.toml", f'[windows]\ndeployment_mode = "{mode}"\n')
    return path


@pytest.fixture
def tmp_workspace(tmp_path: Path) -> SimpleNamespace:
    """
    A virtual uv workspace with two members.

    - ``packages/wslib`` — library (``wheel_only``), no ``__main__``.
    - ``packages/wsapp`` — app (``pyinstaller``), depends on ``wslib>=0.1``
      through a ``{ workspace = true }`` source.

    The root holds ``.python-version`` and a ``scaldys-project.toml`` with
    workspace defaults.
    """
    root = tmp_path / "ws"
    _write(
        root / "pyproject.toml",
        '[tool.uv.workspace]\nmembers = ["packages/*"]\n',
    )
    _write(root / ".python-version", "3.13\n")
    _write(
        root / "scaldys-project.toml",
        '[cython]\nsource_root = "src"\n\n'
        '[docs]\npublic_doc_dirs = ["manual"]\n\n'
        '[format]\nmarkdown_targets = ["README.md"]\n',
    )
    lib = make_member(root, "wslib", version="0.1.0", mode="wheel_only")
    app = make_member(
        root,
        "wsapp",
        version="0.2.0",
        mode="pyinstaller",
        dependencies=["wslib>=0.1"],
        workspace_sources=["wslib"],
        main=True,
    )
    return SimpleNamespace(root=root.resolve(), lib=lib.resolve(), app=app.resolve())
