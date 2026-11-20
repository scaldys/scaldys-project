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
