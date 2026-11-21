"""Tests for building uv workspace members with ``scaldys_project.windows.builder``."""

import logging
import shutil
import zipfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from scaldys_project.common.config import load_config
from scaldys_project.windows.builder import (
    Compiler,
    Packager,
    WindowsBuildEnvironment,
    WindowsBuilder,
    _remove_toml_sections,
)

FAKE_UV = "C:\\fake\\uv.exe"


# ---------------------------------------------------------------------------
# Config and environment
# ---------------------------------------------------------------------------


def test_config_root_defaults_merge(tmp_workspace):
    """Root scaldys-project.toml gives defaults; member keys win, section by section."""
    (tmp_workspace.app / "scaldys-project.toml").write_text(
        '[windows]\ndeployment_mode = "pyinstaller"\nexe_name = "wa"\n\n'
        '[format]\nmarkdown_targets = ["ignored.md"]\n'
    )
    (tmp_workspace.root / "scaldys-project.toml").write_text(
        '[cython]\ncompiled_modules = ["wsapp.core"]\n\n'
        '[windows]\nscript_dir = "pkg/win"\ndeployment_mode = "wheel_only"\n\n'
        '[format]\nmarkdown_targets = ["README.md"]\n'
    )
    config = load_config(tmp_workspace.app, tmp_workspace.root)
    assert config.cython.compiled_modules == ["wsapp.core"]  # from the root
    assert config.windows.script_dir == "pkg/win"  # from the root
    assert config.windows.deployment_mode == "pyinstaller"  # member wins
    assert config.windows.exe_name == "wa"
    assert config.format.markdown_targets == ["README.md"]  # root only

    # Without a workspace root, only the member file is read (as before).
    alone = load_config(tmp_workspace.app)
    assert alone.cython.compiled_modules == []
    assert alone.format.markdown_targets == ["ignored.md"]


def test_config_merged_value_is_validated(tmp_workspace):
    """A bad value inherited from the root is still rejected."""
    (tmp_workspace.lib / "scaldys-project.toml").unlink()
    (tmp_workspace.root / "scaldys-project.toml").write_text(
        '[windows]\ndeployment_mode = "bogus"\n'
    )
    with pytest.raises(RuntimeError, match="deployment_mode"):
        load_config(tmp_workspace.lib, tmp_workspace.root)


def test_environment_workspace_attributes(tmp_workspace):
    """The environment knows its workspace, and .python-version falls back to the root."""
    env = WindowsBuildEnvironment(tmp_workspace.app)
    assert env.workspace is not None
    assert env.workspace_root_path == tmp_workspace.root
    assert env.python_version_file_path == tmp_workspace.root / ".python-version"
    assert env.config.docs.public_doc_dirs == ["manual"]  # root default
    assert [m.name for m in env.internal_closure()] == ["wslib"]

    (tmp_workspace.app / ".python-version").write_text("3.14\n")
    env = WindowsBuildEnvironment(tmp_workspace.app)
    assert env.python_version_file_path == tmp_workspace.app / ".python-version"


def test_standalone_environment_unchanged(tmp_path):
    """Outside a workspace the environment behaves as before."""
    (tmp_path / "pyproject.toml").write_text('[project]\nname = "solo"\nversion = "1.0"\n')
    env = WindowsBuildEnvironment(tmp_path)
    assert env.workspace is None
    assert env.workspace_root_path == env.project_path
    assert env.python_version_file_path == env.project_path / ".python-version"
    assert env.internal_closure() == []


# ---------------------------------------------------------------------------
# Compliance
# ---------------------------------------------------------------------------


def test_library_without_main_is_compliant(tmp_workspace):
    """A wheel_only member needs no __main__.py and uses the root .python-version."""
    env = WindowsBuildEnvironment(tmp_workspace.lib)
    env.check_compliance(require_exe=True, require_installer=False)  # no SystemExit


def test_app_without_main_is_not_compliant(tmp_workspace):
    """An app member (not wheel_only) still requires __main__.py."""
    (tmp_workspace.app / "src" / "wsapp" / "__main__.py").unlink()
    env = WindowsBuildEnvironment(tmp_workspace.app)
    with (
        patch("importlib.metadata.distribution"),
        pytest.raises(SystemExit),
    ):
        env.check_compliance(require_exe=True, require_installer=False)


def test_internal_constraint_met(tmp_workspace):
    """wslib>=0.1 is satisfied by wslib 0.1.0."""
    env = WindowsBuildEnvironment(tmp_workspace.app)
    assert env._check_internal_constraints() == []


def test_internal_constraint_not_met(tmp_workspace):
    """A constraint the dependency's current version does not meet is an issue."""
    pyproject = tmp_workspace.app / "pyproject.toml"
    pyproject.write_text(pyproject.read_text().replace("wslib>=0.1", "wslib>=1.0"))
    env = WindowsBuildEnvironment(tmp_workspace.app)
    issues = env._check_internal_constraints()
    assert len(issues) == 1
    assert "wslib>=1.0" in issues[0]
    assert "0.1.0" in issues[0]


def test_internal_constraint_missing_warns(tmp_workspace, caplog):
    """An internal dependency without a version constraint logs a warning only."""
    pyproject = tmp_workspace.app / "pyproject.toml"
    pyproject.write_text(pyproject.read_text().replace('"wslib>=0.1"', '"wslib"'))
    env = WindowsBuildEnvironment(tmp_workspace.app)
    with caplog.at_level(logging.WARNING):
        assert env._check_internal_constraints() == []
    assert any("no version" in r.message for r in caplog.records)


def test_missing_dist_hint_mentions_all_packages(tmp_workspace, caplog):
    """In a workspace, a missing dist-info points at 'uv sync --all-packages'."""
    env = WindowsBuildEnvironment(tmp_workspace.app)
    with caplog.at_level(logging.ERROR), pytest.raises(SystemExit):
        env.check_compliance(require_exe=True, require_installer=False)
    assert any("uv sync --all-packages" in r.message for r in caplog.records)


# ---------------------------------------------------------------------------
# _remove_toml_sections
# ---------------------------------------------------------------------------


def test_remove_toml_sections_sub_tables_and_arrays():
    """Dotted sub-tables and arrays of tables are removed; other tables stay."""
    text = (
        "[project]\n"
        'name = "x"\n'
        "\n"
        "[tool.uv.sources]\n"
        "a = { workspace = true }\n"
        "\n"
        '[tool.uv.sources."b-c"]\n'
        'git = "https://example.invalid/b"\n'
        "\n"
        "[[tool.uv.index]]\n"
        'name = "internal"\n'
        "\n"
        "[tool.uv]\n"
        "package = true\n"
        "\n"
        "[tool.uv.sourcesish]\n"
        "keep = 1\n"
    )
    out = _remove_toml_sections(text, "tool.uv.sources", "tool.uv.index")
    assert "workspace = true" not in out
    assert "example.invalid" not in out
    assert "internal" not in out
    assert "[tool.uv]\npackage = true" in out
    assert "[tool.uv.sourcesish]\nkeep = 1" in out
    assert '[project]\nname = "x"' in out


def test_remove_toml_sections_bracket_continuation_lines():
    """A multi-line array line starting with '[' does not end the section early."""
    text = (
        "[tool.uv.workspace]\n"
        "members = [\n"
        '["nested", "array"],\n'
        '"packages/*",\n'
        "]\n"
        "\n"
        "[project]\n"
        'name = "x"\n'
    )
    out = _remove_toml_sections(text, "tool.uv.workspace")
    assert out == '[project]\nname = "x"\n'


def test_remove_toml_sections_header_with_comment():
    """A header followed by a comment is still recognised."""
    text = "[tool.uv.sources]  # local\na = { workspace = true }\n[project]\nname = 'x'\n"
    assert _remove_toml_sections(text, "tool.uv.sources") == "[project]\nname = 'x'\n"


# ---------------------------------------------------------------------------
# Wheel build staging
# ---------------------------------------------------------------------------


def _fake_uv_build(env: WindowsBuildEnvironment):
    """Return a run_command side effect that writes the expected wheel file."""

    def side_effect(cmd, err_msg, cwd=None):
        out_dir = Path(cmd[cmd.index("--out-dir") + 1])
        out_dir.mkdir(parents=True, exist_ok=True)
        name = env.project_name.replace("-", "_")
        (out_dir / f"{name}-{env.version}-py3-none-any.whl").write_bytes(b"")
        return "", ""

    return side_effect


def test_build_wheel_stages_member_pyproject(tmp_workspace):
    """The staged pyproject has no uv tables, license files are copied, --no-sources is used."""
    app = tmp_workspace.app
    (app / "LICENSE").write_text("MIT\n")
    (app / "licenses").mkdir()
    (app / "licenses" / "THIRD_PARTY.txt").write_text("3rd\n")
    pyproject = app / "pyproject.toml"
    pyproject.write_text(
        pyproject.read_text().replace(
            "dependencies = [",
            'license-files = ["LICEN[CS]E*", "licenses/*.txt"]\ndependencies = [',
        )
    )
    env = WindowsBuildEnvironment(app)
    compiler = Compiler(env)
    compiler.run_cython()

    with (
        patch("scaldys_project.windows.builder.shutil.which", return_value=FAKE_UV),
        patch.object(env, "run_command", side_effect=_fake_uv_build(env)) as run_command,
    ):
        wheel = compiler._build_wheel()

    cmd = run_command.call_args.args[0]
    assert "--no-sources" in cmd
    assert wheel == env.dist_dir_path / "wsapp-0.2.0-py3-none-any.whl"
    staged = env.src_compiled_dir_path
    text = (staged / "pyproject.toml").read_text()
    assert "tool.uv.sources" not in text
    assert "workspace = true" not in text
    assert (staged / "LICENSE").read_text() == "MIT\n"
    assert (staged / "licenses" / "THIRD_PARTY.txt").exists()


# ---------------------------------------------------------------------------
# Internal dependencies
# ---------------------------------------------------------------------------


def test_pyinstaller_args_include_internal_closure(tmp_workspace):
    """The app's PyInstaller command bundles its internal dependencies."""
    (tmp_workspace.lib / "packaging" / "hooks").mkdir(parents=True)
    env = WindowsBuildEnvironment(tmp_workspace.app)
    with patch.object(env, "run_command", return_value=("", "")) as run_command:
        Compiler(env).run_pyinstaller()

    cmd = run_command.call_args.args[0]
    lib_compiled = str(tmp_workspace.lib / "build" / "compiled")
    app_compiled = str(env.src_compiled_dir_path)
    paths = [cmd[i + 1] for i, a in enumerate(cmd) if a == "--paths"]
    assert paths == [lib_compiled, app_compiled]
    assert cmd[cmd.index("--copy-metadata") + 1] == "wslib"
    collected = [cmd[i + 1] for i, a in enumerate(cmd) if a == "--collect-submodules"]
    assert collected == ["wsapp", "wslib"]
    hooks = [cmd[i + 1] for i, a in enumerate(cmd) if a == "--additional-hooks-dir"]
    assert str(tmp_workspace.lib / "packaging" / "hooks") in hooks


def test_pyinstaller_args_standalone_unchanged(tmp_workspace):
    """A member without internal dependencies gets no extra PyInstaller arguments."""
    env = WindowsBuildEnvironment(tmp_workspace.lib)
    with patch.object(env, "run_command", return_value=("", "")) as run_command:
        Compiler(env).run_pyinstaller()
    cmd = run_command.call_args.args[0]
    assert "--copy-metadata" not in cmd
    assert cmd.count("--paths") == 1


def _patch_dep_build(calls: list[Path]):
    """Patch the per-member build steps; _build_wheel writes a fake wheel."""

    def fake_build_wheel(self):
        calls.append(self.env.project_path)
        self.env.dist_dir_path.mkdir(parents=True, exist_ok=True)
        wheel = (
            self.env.dist_dir_path
            / f"{self.env.project_package_name}-{self.env.version}-py3-none-any.whl"
        )
        wheel.write_bytes(b"")
        return wheel

    return (
        patch.object(WindowsBuilder, "clean"),
        patch.object(Compiler, "run_cython"),
        patch.object(Compiler, "_build_wheel", autospec=True, side_effect=fake_build_wheel),
    )


def test_build_internal_deps_collects_and_caches(tmp_workspace):
    """Internal wheels land in build/internal_wheels; each member is built once per run."""
    calls: list[Path] = []
    p1, p2, p3 = _patch_dep_build(calls)
    with p1, p2, p3:
        builder = WindowsBuilder(tmp_workspace.app)
        wheels = builder.build_internal_deps()
        WindowsBuilder(tmp_workspace.app).build_internal_deps()

    assert calls == [tmp_workspace.lib]
    internal = tmp_workspace.app / "build" / "internal_wheels"
    assert wheels == [internal / "wslib-0.1.0-py3-none-any.whl"]
    assert wheels[0].exists()
    assert not (tmp_workspace.app / "dist").exists()


def test_member_own_build_is_reused_by_app(tmp_workspace):
    """A library built as its own target earlier in the run is not rebuilt for the app."""
    calls: list[Path] = []
    p1, p2, p3 = _patch_dep_build(calls)
    with p1, p2, p3:
        WindowsBuilder(tmp_workspace.lib).compiler.build()  # the library's own build
        WindowsBuilder(tmp_workspace.app).build_internal_deps()
    assert calls == [tmp_workspace.lib]


def test_distribution_steps_include_internal_deps_for_apps_only(tmp_workspace):
    """Only non-wheel_only members with a closure get the internal-deps step."""
    app_steps = [name for name, _ in WindowsBuilder(tmp_workspace.app)._distribution_steps()]
    lib_steps = [name for name, _ in WindowsBuilder(tmp_workspace.lib)._distribution_steps()]
    assert "Building internal dependencies" in app_steps
    assert app_steps.index("Building internal dependencies") < app_steps.index(
        "Building executable"
    )
    assert "Building internal dependencies" not in lib_steps


def test_pyruntime_offline_finds_internal_wheels(tmp_workspace):
    """The offline PythonRuntime install also looks in build/internal_wheels."""
    (tmp_workspace.app / "scaldys-project.toml").write_text(
        '[windows]\ndeployment_mode = "pyruntime"\nbundle_pyruntime = true\n'
    )
    env = WindowsBuildEnvironment(tmp_workspace.app)
    env.internal_wheels_dir_path.mkdir(parents=True)
    (env.internal_wheels_dir_path / "wslib-0.1.0-py3-none-any.whl").write_bytes(b"")

    with (
        patch.object(env, "run_command", return_value=("", "")) as run_command,
        patch("scaldys_project.windows.builder.shutil.which", return_value=FAKE_UV),
    ):
        Packager(env)._build_pyruntime()

    cmd = run_command.call_args_list[-1].args[0]
    links = [cmd[i + 1] for i, a in enumerate(cmd) if a == "--find-links"]
    assert links == [str(env.dist_dir_path), str(env.internal_wheels_dir_path)]
    assert cmd[-2:] == ["wsapp", "pyyaml"]


def test_pyruntime_stages_internal_wheels(tmp_workspace):
    """prepare_windows_files copies internal wheels next to the app wheel."""
    (tmp_workspace.app / "scaldys-project.toml").write_text(
        '[windows]\ndeployment_mode = "pyruntime"\n'
    )
    env = WindowsBuildEnvironment(tmp_workspace.app)
    env.dist_dir_path.mkdir(parents=True)
    (env.dist_dir_path / "wsapp-0.2.0-py3-none-any.whl").write_bytes(b"")
    env.internal_wheels_dir_path.mkdir(parents=True)
    (env.internal_wheels_dir_path / "wslib-0.1.0-py3-none-any.whl").write_bytes(b"")

    with patch("scaldys_project.windows.builder.shutil.which", return_value=None):
        Packager(env).prepare_windows_files()

    staged = sorted(p.name for p in (env.dist_exe_dir_path / "wheels").iterdir())
    assert staged == ["wsapp-0.2.0-py3-none-any.whl", "wslib-0.1.0-py3-none-any.whl"]


def test_main_skips_docs_step_without_docs_dir(tmp_workspace):
    """build all on a member without docs/ has no documentation step."""
    builder = WindowsBuilder(tmp_workspace.lib)
    with patch.object(builder, "_run_steps") as run_steps:
        builder.main()
    names = [name for name, _ in run_steps.call_args.args[0]]
    assert "Building documentation" not in names


# ---------------------------------------------------------------------------
# Real build (slow)
# ---------------------------------------------------------------------------


@pytest.mark.slow
@pytest.mark.skipif(shutil.which("uv") is None, reason="uv not on PATH")
def test_real_uv_build_of_workspace_members(tmp_workspace):
    """A real 'uv build' of both members works from the staged build/compiled tree."""
    (tmp_workspace.app / "LICENSE").write_text("MIT\n")
    pyproject = tmp_workspace.app / "pyproject.toml"
    pyproject.write_text(
        pyproject.read_text().replace(
            "dependencies = [", 'license-files = ["LICENSE"]\ndependencies = ['
        )
    )
    with patch("importlib.metadata.distribution"):
        wheels = WindowsBuilder(tmp_workspace.app).build_internal_deps()
        app = WindowsBuilder(tmp_workspace.app)
        app.compiler.run_cython()
        app_wheel = app.compiler._build_wheel()

    assert [w.name for w in wheels] == ["wslib-0.1.0-py3-none-any.whl"]
    with zipfile.ZipFile(app_wheel) as zf:
        metadata = zf.read("wsapp-0.2.0.dist-info/METADATA").decode()
        names = zf.namelist()
    assert "Requires-Dist: wslib>=0.1" in metadata
    assert "wsapp-0.2.0.dist-info/licenses/LICENSE" in names


def test_mock_env_without_internal_wheels_unchanged(tmp_path):
    """A MagicMock environment (as in older tests) gets no extra --find-links."""
    (tmp_path / ".python-version").write_text("3.13\n")
    env = MagicMock()
    env.project_name = "my-app"
    env.python_version_file_path = tmp_path / ".python-version"
    env.artifacts_dir_path = tmp_path / "artifacts"
    env.dist_wheels_dir_path = tmp_path / "dist"
    env.internal_wheels_dir_path = tmp_path / "build" / "internal_wheels"
    with patch("scaldys_project.windows.builder.shutil.which", return_value=FAKE_UV):
        Packager(env)._build_pyruntime()
    cmd = env.run_command.call_args_list[-1].args[0]
    assert cmd.count("--find-links") == 1
