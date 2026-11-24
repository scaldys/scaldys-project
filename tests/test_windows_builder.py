"""Tests for the offline PythonRuntime build in ``scaldys_project.windows.builder``."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from scaldys_project.windows.builder import Packager, WindowsBuildEnvironment

FAKE_UV = "C:\\fake\\uv.exe"


def _install_cmd(run_command: MagicMock) -> list[str]:
    """Return the command of the last ``run_command`` call (the package install step)."""
    return run_command.call_args_list[-1].args[0]


# ---------------------------------------------------------------------------
# Unit tests — Packager._build_pyruntime with a mocked environment
# ---------------------------------------------------------------------------


def _mock_env(tmp_path: Path) -> MagicMock:
    """Build a mocked WindowsBuildEnvironment rooted at *tmp_path*."""
    (tmp_path / ".python-version").write_text("3.13\n")
    env = MagicMock()
    env.project_name = "my-app"
    env.python_version_file_path = tmp_path / ".python-version"
    env.artifacts_dir_path = tmp_path / "artifacts"
    env.dist_wheels_dir_path = tmp_path / "dist"
    return env


def test_build_pyruntime_installs_project_wheel(tmp_path):
    """The install step installs the project's own package and pyyaml from dist/."""
    env = _mock_env(tmp_path)
    with patch("scaldys_project.windows.builder.shutil.which", return_value=FAKE_UV):
        Packager(env)._build_pyruntime()

    cmd = _install_cmd(env.run_command)
    python_exe = tmp_path / "artifacts" / "pyruntime" / "Scripts" / "python.exe"
    assert cmd[:3] == [FAKE_UV, "pip", "install"]
    assert cmd[cmd.index("--python") + 1] == str(python_exe)
    assert cmd[cmd.index("--find-links") + 1] == str(tmp_path / "dist")
    assert cmd[-2:] == ["my-app", "pyyaml"]
    assert "softspin" not in cmd


def test_build_pyruntime_without_uv_raises(tmp_path):
    """A missing uv executable raises RuntimeError before any command runs."""
    env = _mock_env(tmp_path)
    with (
        patch("scaldys_project.windows.builder.shutil.which", return_value=None),
        pytest.raises(RuntimeError, match="uv not found"),
    ):
        Packager(env)._build_pyruntime()
    env.run_command.assert_not_called()


# ---------------------------------------------------------------------------
# Integration test — real WindowsBuildEnvironment from a project on disk
# ---------------------------------------------------------------------------


def test_build_pyruntime_uses_name_from_pyproject(tmp_path):
    """The package name flows from pyproject.toml through the environment to uv."""
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "my-app"\nversion = "1.2.3"\n', encoding="utf-8"
    )
    (tmp_path / "scaldys-project.toml").write_text(
        '[windows]\ndeployment_mode = "pyruntime"\nbundle_pyruntime = true\n', encoding="utf-8"
    )
    (tmp_path / ".python-version").write_text("3.13\n")

    env = WindowsBuildEnvironment(tmp_path)
    assert env.config.windows.bundle_pyruntime is True

    with (
        patch.object(env, "run_command", return_value=("", "")) as run_command,
        patch("scaldys_project.windows.builder.shutil.which", return_value=FAKE_UV),
    ):
        Packager(env)._build_pyruntime()

    pyruntime_dir = env.project_path / "artifacts" / "pyruntime"
    commands = [c.args[0] for c in run_command.call_args_list]
    assert commands == [
        [FAKE_UV, "python", "install", "3.13"],
        [FAKE_UV, "venv", str(pyruntime_dir), "--python", "3.13"],
        [
            FAKE_UV,
            "pip",
            "install",
            "--python",
            str(pyruntime_dir / "Scripts" / "python.exe"),
            "--find-links",
            str(env.project_path / "dist"),
            "my-app",
            "pyyaml",
        ],
    ]
    assert pyruntime_dir.is_dir()


# ---------------------------------------------------------------------------
# Unit tests — clean_docs, clean_windows, clean_all
# ---------------------------------------------------------------------------


def _setup_mock_project(tmp_path: Path):
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "my-app"\nversion = "1.0.0"\n', encoding="utf-8"
    )
    (tmp_path / "scaldys-project.toml").write_text(
        '[windows]\ndeployment_mode = "wheel_only"\n', encoding="utf-8"
    )
    # Docs
    (tmp_path / "docs" / "manual" / "source").mkdir(parents=True)
    (tmp_path / "docs" / "manual" / "source" / "conf.py").write_text("", encoding="utf-8")
    (tmp_path / "build" / "manual" / "html").mkdir(parents=True)
    (tmp_path / "build" / "manual" / "html" / "index.html").write_text("docs", encoding="utf-8")

    # Windows compilation & outputs
    (tmp_path / "build" / "compiled").mkdir(parents=True)
    (tmp_path / "build" / "compiled" / "mod.pyd").write_text("binary", encoding="utf-8")
    (tmp_path / "build" / "internal_wheels").mkdir(parents=True)
    (tmp_path / "build" / "internal_wheels" / "dep.whl").write_text("wheel", encoding="utf-8")
    (tmp_path / "build" / "pyinstaller").mkdir(parents=True)
    (tmp_path / "build" / "pyinstaller" / "out.txt").write_text("cache", encoding="utf-8")
    (tmp_path / "build" / "app.spec").write_text("spec", encoding="utf-8")
    (tmp_path / "dist").mkdir(parents=True)
    (tmp_path / "dist" / "my_app-1.0.0-cp313-cp313-win_amd64.whl").write_text(
        "whl", encoding="utf-8"
    )
    (tmp_path / "artifacts").mkdir(parents=True)
    (tmp_path / "artifacts" / "setup.exe").write_text("exe", encoding="utf-8")
    (tmp_path / "src" / "my_app").mkdir(parents=True)
    (tmp_path / "src" / "my_app" / "mod.c").write_text("c source", encoding="utf-8")


def test_clean_docs(tmp_path):
    """clean_docs empties build/<doc_unit> but preserves windows and dist artifacts."""
    _setup_mock_project(tmp_path)
    from scaldys_project.windows.builder import WindowsBuilder

    builder = WindowsBuilder(tmp_path)
    builder.clean_docs()

    # Docs output cleaned
    assert not (tmp_path / "build" / "manual" / "html" / "index.html").exists()

    # Windows outputs preserved
    assert (tmp_path / "build" / "compiled" / "mod.pyd").exists()
    assert (tmp_path / "build" / "internal_wheels" / "dep.whl").exists()
    assert (tmp_path / "build" / "pyinstaller" / "out.txt").exists()
    assert (tmp_path / "build" / "app.spec").exists()
    assert (tmp_path / "dist" / "my_app-1.0.0-cp313-cp313-win_amd64.whl").exists()
    assert (tmp_path / "artifacts" / "setup.exe").exists()
    assert (tmp_path / "src" / "my_app" / "mod.c").exists()


def test_clean_windows(tmp_path):
    """clean_windows empties compiled, dist, artifacts and removes .c files, preserving docs."""
    _setup_mock_project(tmp_path)
    from scaldys_project.windows.builder import WindowsBuilder

    builder = WindowsBuilder(tmp_path)
    builder.clean_windows()

    # Docs preserved
    assert (tmp_path / "build" / "manual" / "html" / "index.html").exists()

    # Windows outputs removed
    assert not (tmp_path / "build" / "compiled" / "mod.pyd").exists()
    assert not (tmp_path / "build" / "internal_wheels" / "dep.whl").exists()
    assert not (tmp_path / "build" / "pyinstaller" / "out.txt").exists()
    assert not (tmp_path / "build" / "app.spec").exists()
    assert not (tmp_path / "dist" / "my_app-1.0.0-cp313-cp313-win_amd64.whl").exists()
    assert not (tmp_path / "artifacts" / "setup.exe").exists()
    assert not (tmp_path / "src" / "my_app" / "mod.c").exists()


def test_clean_all(tmp_path):
    """clean_all removes all build, dist, artifacts and .c files."""
    _setup_mock_project(tmp_path)
    from scaldys_project.windows.builder import WindowsBuilder

    builder = WindowsBuilder(tmp_path)
    builder.clean_all()

    # Everything removed
    assert not (tmp_path / "build" / "manual" / "html" / "index.html").exists()
    assert not (tmp_path / "build" / "compiled" / "mod.pyd").exists()
    assert not (tmp_path / "build" / "internal_wheels" / "dep.whl").exists()
    assert not (tmp_path / "build" / "pyinstaller" / "out.txt").exists()
    assert not (tmp_path / "build" / "app.spec").exists()
    assert not (tmp_path / "dist" / "my_app-1.0.0-cp313-cp313-win_amd64.whl").exists()
    assert not (tmp_path / "artifacts" / "setup.exe").exists()
    assert not (tmp_path / "src" / "my_app" / "mod.c").exists()
