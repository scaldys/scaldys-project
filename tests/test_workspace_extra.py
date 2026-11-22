"""Additional unit and integration tests for uv workspace support."""

import logging
import shutil
import zipfile
from pathlib import Path
from unittest.mock import patch

import pytest
import typer
from typer.testing import CliRunner

from scaldys_project.cli.cli import app
from scaldys_project.cli.commands.cmd_publish import _publish_one
from scaldys_project.cli.utils import resolve_targets, run_for_targets
from scaldys_project.common.compile_runner import _load_cython_config
from scaldys_project.common.workspace import find_workspace
from scaldys_project.windows.builder import Compiler, WindowsBuildEnvironment, WindowsBuilder
from tests.conftest import make_member

runner = CliRunner()


def _ok_process(run):
    run.return_value.returncode = 0
    run.return_value.stdout = ""
    run.return_value.stderr = ""


# ---------------------------------------------------------------------------
# Discovery edge cases
# ---------------------------------------------------------------------------


def test_folder_without_pyproject_under_root_belongs_to_workspace(tmp_workspace):
    """A plain folder below a virtual root (e.g. docs/) resolves to the workspace."""
    docs = tmp_workspace.root / "docs"
    docs.mkdir()
    ws = find_workspace(docs)
    assert ws is not None
    assert ws.root == tmp_workspace.root


def test_non_virtual_root_is_default_target(tmp_workspace, monkeypatch):
    """At a non-virtual root, the root project itself is the default target."""
    root = tmp_workspace.root
    (root / "pyproject.toml").write_text(
        '[project]\nname = "ws-root"\nversion = "1.0"\n\n'
        '[tool.uv.workspace]\nmembers = ["packages/*"]\n'
    )
    monkeypatch.chdir(root)
    assert resolve_targets(None, False) == [root]
    # The root has no internal dependencies and is discovered first.
    assert resolve_targets(None, True) == [root, tmp_workspace.lib, tmp_workspace.app]


def test_standalone_environment_has_no_member(tmp_path):
    """workspace_member is None outside a workspace."""
    (tmp_path / "pyproject.toml").write_text('[project]\nname = "solo"\nversion = "1.0"\n')
    assert WindowsBuildEnvironment(tmp_path).workspace_member is None


# ---------------------------------------------------------------------------
# run_for_targets
# ---------------------------------------------------------------------------


def test_run_for_targets_single_target_has_summary_no_header(tmp_path):
    """One target: no header, but the summary table is still printed."""
    (tmp_path / "pyproject.toml").write_text('[project]\nname = "solo"\nversion = "0.1.0"\n')
    calls = []
    with patch("scaldys_project.cli.utils.console.print") as printed:
        run_for_targets([tmp_path], calls.append, title="Build")
    assert calls == [tmp_path]
    assert len(printed.call_args_list) == 1  # the table only, no Rule header
    table = printed.call_args_list[0].args[0]
    cells = [list(col.cells) for col in table.columns]
    assert cells == [[tmp_path.name], ["0.1.0"], ["[green]ok[/green]"]]


def test_run_for_targets_summary_and_failure(tmp_path):
    """Several targets: stop at the failure, report 'not run', re-raise the error."""
    a, b, c = (tmp_path / n for n in ("alpha", "beta", "gamma"))
    a.mkdir()
    (a / "pyproject.toml").write_text('[project]\nname = "alpha"\nversion = "1.2.3"\n')
    calls = []

    def action(path: Path) -> None:
        calls.append(path)
        if path == b:
            raise SystemExit(1)

    with (
        patch("scaldys_project.cli.utils.console.print") as printed,
        pytest.raises(SystemExit),
    ):
        run_for_targets([a, b, c], action, title="Build")
    assert calls == [a, b]
    table = printed.call_args_list[-1].args[0]
    cells = [list(col.cells) for col in table.columns]
    assert cells[0] == ["alpha", "beta", "gamma"]
    assert cells[1] == ["1.2.3", "-", "-"]
    assert cells[2] == ["[green]ok[/green]", "[red]failed[/red]", "[dim]not run[/dim]"]


def test_project_version_fallbacks(tmp_path):
    """Version is '-' without pyproject.toml, with a dynamic version, or invalid TOML."""
    from scaldys_project.cli.utils import _project_version

    assert _project_version(tmp_path) == "-"
    (tmp_path / "pyproject.toml").write_text('[project]\nname = "x"\ndynamic = ["version"]\n')
    assert _project_version(tmp_path) == "-"
    (tmp_path / "pyproject.toml").write_text("not = [valid")
    assert _project_version(tmp_path) == "-"
    (tmp_path / "pyproject.toml").write_text('[project]\nname = "x"\nversion = "2.0"\n')
    assert _project_version(tmp_path) == "2.0"


def test_run_for_targets_single_target_failure_still_summarises(tmp_path):
    """One failing target: the summary shows 'failed' and the error is re-raised."""

    def action(_: Path) -> None:
        raise RuntimeError("boom")

    with (
        patch("scaldys_project.cli.utils.console.print") as printed,
        pytest.raises(RuntimeError),
    ):
        run_for_targets([tmp_path], action, title="Build")
    table = printed.call_args_list[-1].args[0]
    assert [list(col.cells) for col in table.columns][2] == ["[red]failed[/red]"]


def test_run_for_targets_exit_zero_counts_as_success(tmp_path):
    """typer.Exit(0) from an action is a success, not a failure."""
    a, b = tmp_path / "a", tmp_path / "b"
    calls = []

    def action(path: Path) -> None:
        calls.append(path)
        raise typer.Exit(0)

    with patch("scaldys_project.cli.utils.console.print"):
        run_for_targets([a, b], action, title="Check")
    assert calls == [a, b]


# ---------------------------------------------------------------------------
# Config consumers
# ---------------------------------------------------------------------------


def test_compile_runner_uses_root_defaults(tmp_workspace, monkeypatch):
    """The Cython runner reads compiled_modules merged with the workspace root defaults."""
    (tmp_workspace.root / "scaldys-project.toml").write_text(
        '[cython]\ncompiled_modules = ["wslib.fast"]\nsource_root = "src"\n'
    )
    monkeypatch.chdir(tmp_workspace.lib)
    assert _load_cython_config() == (["wslib.fast"], "src")


def test_compile_runner_standalone(tmp_path, monkeypatch):
    """Outside a workspace the runner reads only the project's own file."""
    (tmp_path / "pyproject.toml").write_text('[project]\nname = "solo"\nversion = "1"\n')
    (tmp_path / "scaldys-project.toml").write_text(
        '[cython]\ncompiled_modules = ["solo.x"]\nsource_root = "lib"\n'
    )
    monkeypatch.chdir(tmp_path)
    assert _load_cython_config() == (["solo.x"], "lib")


def test_member_without_config_file_uses_root(tmp_workspace):
    """A member with no scaldys-project.toml takes every setting from the root."""
    (tmp_workspace.lib / "scaldys-project.toml").unlink()
    (tmp_workspace.root / "scaldys-project.toml").write_text(
        '[windows]\ndeployment_mode = "wheel_only"\nscript_dir = "win"\n'
    )
    env = WindowsBuildEnvironment(tmp_workspace.lib)
    assert env.config.windows.script_dir == "win"
    assert env.script_dir_path == (tmp_workspace.lib / "win").resolve()


# ---------------------------------------------------------------------------
# Wheel helpers and compliance
# ---------------------------------------------------------------------------


def test_license_files_legacy_table(tmp_workspace):
    """license = { file = ... } is staged as well as license-files globs."""
    (tmp_workspace.lib / "COPYING.txt").write_text("legal\n")
    env = WindowsBuildEnvironment(tmp_workspace.lib)
    files = Compiler(env)._license_files({"license": {"file": "COPYING.txt"}})
    assert files == [tmp_workspace.lib / "COPYING.txt"]
    assert Compiler(env)._license_files({"license-files": ["NOPE*"]}) == []


def test_find_wheel_normalises_name_and_version(tmp_path):
    """_find_wheel matches the PEP 427 file name of a dotted/hyphenated project."""
    (tmp_path / "pyproject.toml").write_text('[project]\nname = "My.Pkg-Name"\nversion = "1.0"\n')
    env = WindowsBuildEnvironment(tmp_path)
    out = tmp_path / "dist"
    out.mkdir()
    (out / "other-1.0-py3-none-any.whl").write_bytes(b"")
    wheel = out / "my_pkg_name-1.0-cp313-cp313-win_amd64.whl"
    wheel.write_bytes(b"")
    assert Compiler(env)._find_wheel(out) == wheel
    wheel.unlink()
    with pytest.raises(RuntimeError, match="No wheel"):
        Compiler(env)._find_wheel(out)


def test_unmet_constraint_fails_compliance(tmp_workspace, caplog):
    """check_compliance exits when an internal constraint is not met."""
    pyproject = tmp_workspace.app / "pyproject.toml"
    pyproject.write_text(pyproject.read_text().replace("wslib>=0.1", "wslib>=2"))
    env = WindowsBuildEnvironment(tmp_workspace.app)
    with (
        patch("importlib.metadata.distribution"),
        caplog.at_level(logging.ERROR),
        pytest.raises(SystemExit),
    ):
        env.check_compliance(require_exe=True, require_installer=False)
    assert any("wslib>=2" in r.message for r in caplog.records)


def test_app_compliance_passes_when_installed(tmp_workspace):
    """With its dists installed, the app member passes the compliance check."""
    env = WindowsBuildEnvironment(tmp_workspace.app)
    with patch("importlib.metadata.distribution"):
        env.check_compliance(require_exe=True, require_installer=False)


# ---------------------------------------------------------------------------
# CLI: ci / format / test / publish
# ---------------------------------------------------------------------------


def test_format_python_runs_at_workspace_root(tmp_workspace, monkeypatch):
    """format python started inside a member runs ruff at the workspace root."""
    monkeypatch.chdir(tmp_workspace.app / "src")
    with patch("scaldys_project.cli.commands.cmd_format.subprocess.run") as run:
        _ok_process(run)
        result = runner.invoke(app, ["format", "python"])
    assert result.exit_code == 0, result.output
    assert run.call_args.kwargs["cwd"] == tmp_workspace.root


def test_ci_lint_runs_at_project_root_outside_workspace(tmp_path, monkeypatch):
    """Outside a workspace, ci runs at the project root, also from a subfolder."""
    (tmp_path / "pyproject.toml").write_text('[project]\nname = "solo"\nversion = "1"\n')
    (tmp_path / "src").mkdir()
    monkeypatch.chdir(tmp_path / "src")
    with patch("scaldys_project.cli.commands.cmd_ci.subprocess.run") as run:
        _ok_process(run)
        assert runner.invoke(app, ["ci", "lint"]).exit_code == 0
        assert runner.invoke(app, ["ci", "doclint"]).exit_code == 0
        assert runner.invoke(app, ["ci", "typecheck"]).exit_code == 0
    cmds = [c.args[0] for c in run.call_args_list]
    assert cmds == [
        ["uv", "run", "ruff", "check", "."],
        ["uv", "run", "sphinx-lint", "docs/"],
        ["uv", "sync"],
        ["uv", "run", "pyright", "./src", "./tests"],
    ]
    assert {c.kwargs["cwd"] for c in run.call_args_list} == {tmp_path}


def test_ci_markdown_from_member_uses_root_config_and_workflow(tmp_workspace, monkeypatch, caplog):
    """ci markdown in a member reads the root [format] and the root ci.yml (drift check)."""
    root = tmp_workspace.root
    (root / "README.md").write_text("# ws\n")
    wf = root / ".github" / "workflows"
    wf.mkdir(parents=True)
    (wf / "ci.yml").write_text("steps:\n  - run: uv run mdformat --check README.md docs\n")
    monkeypatch.chdir(tmp_workspace.lib)
    with (
        patch("scaldys_project.cli.commands.cmd_ci.subprocess.run") as run,
        caplog.at_level(logging.WARNING),
    ):
        _ok_process(run)
        result = runner.invoke(app, ["ci", "markdown"])
    assert result.exit_code == 0, result.output
    assert run.call_args.args[0] == ["uv", "run", "mdformat", "--check", "README.md"]
    assert run.call_args.kwargs["cwd"] == root
    assert any("differ from configured targets" in r.message for r in caplog.records)


def test_ci_doclint_without_docs_in_workspace(tmp_workspace, monkeypatch):
    """ci doclint in a workspace without any docs/ folder does nothing and succeeds."""
    monkeypatch.chdir(tmp_workspace.root)
    with patch("scaldys_project.cli.commands.cmd_ci.subprocess.run") as run:
        result = runner.invoke(app, ["ci", "doclint"])
    assert result.exit_code == 0, result.output
    run.assert_not_called()


def test_test_outside_workspace(tmp_path, monkeypatch):
    """Outside a workspace, test runs plain pytest in the cwd; --package is an error."""
    (tmp_path / "pyproject.toml").write_text('[project]\nname = "solo"\nversion = "1"\n')
    monkeypatch.chdir(tmp_path)
    with patch("scaldys_project.cli.commands.cmd_test.subprocess.run") as run:
        run.return_value.returncode = 0
        assert runner.invoke(app, ["test"]).exit_code == 0
        assert run.call_args.args[0][:3] == ["uv", "run", "pytest"]
        run.reset_mock()
        assert runner.invoke(app, ["test", "-p", "solo"]).exit_code == 2
        run.assert_not_called()


def test_test_in_member_and_failure_code(tmp_workspace, monkeypatch):
    """test inside a member runs only that member and propagates pytest's exit code."""
    monkeypatch.chdir(tmp_workspace.lib)
    with patch("scaldys_project.cli.commands.cmd_test.subprocess.run") as run:
        run.return_value.returncode = 3
        result = runner.invoke(app, ["test"])
    assert result.exit_code == 3
    assert run.call_args.args[0][:4] == ["uv", "run", "--package", "wslib"]


def test_publish_one_checks(tmp_path):
    """_publish_one keeps its per-project safety checks."""
    with pytest.raises(typer.Exit):
        _publish_one(tmp_path, test=False)  # no dist/
    dist = tmp_path / "dist"
    dist.mkdir()
    with pytest.raises(typer.Exit):
        _publish_one(tmp_path, test=False)  # no wheel
    (dist / "x-1.0-py3-none-any.whl").write_bytes(b"")
    with pytest.raises(typer.Exit):
        _publish_one(tmp_path, test=False)  # pure wheel only
    (dist / "x-1.0-cp313-cp313-win_amd64.whl").write_bytes(b"")
    (dist / "x-1.1-cp313-cp313-win_amd64.whl").write_bytes(b"")
    with pytest.raises(typer.Exit):
        _publish_one(tmp_path, test=False)  # several binary wheels
    (dist / "x-1.1-cp313-cp313-win_amd64.whl").unlink()
    with patch("scaldys_project.cli.commands.cmd_publish.subprocess.run") as run:
        run.return_value.returncode = 0
        _publish_one(tmp_path, test=True)
    cmd = run.call_args.args[0]
    assert cmd[:2] == ["uv", "publish"]
    assert cmd[-2:] == ["--index", "testpypi"]
    assert run.call_args.kwargs["cwd"] == tmp_path


def test_publish_outside_workspace(tmp_path, monkeypatch):
    """Outside a workspace, publish acts on the project root."""
    (tmp_path / "pyproject.toml").write_text('[project]\nname = "solo"\nversion = "1"\n')
    monkeypatch.chdir(tmp_path)
    with patch("scaldys_project.cli.commands.cmd_publish._publish_one") as publish_one:
        assert runner.invoke(app, ["publish"]).exit_code == 0
    assert publish_one.call_args.args == (tmp_path, False)


# ---------------------------------------------------------------------------
# Pipeline wiring
# ---------------------------------------------------------------------------


def test_build_distribution_step_order_for_app(tmp_workspace):
    """build windows on an app: clean, then internal deps, then the executable."""
    builder = WindowsBuilder(tmp_workspace.app)
    with patch.object(builder, "_run_steps") as run_steps:
        builder.build_distribution()
    names = [name for name, _ in run_steps.call_args.args[0]]
    assert names == [
        "Checking project compliance",
        "Pre-flight checks",
        "Cleaning build directories",
        "Building internal dependencies",
        "Building executable",
        "Building installer",
    ]


def test_main_step_order_with_docs(tmp_workspace):
    """build all on an app with docs/: docs come before internal deps."""
    (tmp_workspace.app / "docs").mkdir()
    builder = WindowsBuilder(tmp_workspace.app)
    with patch.object(builder, "_run_steps") as run_steps:
        builder.main()
    names = [name for name, _ in run_steps.call_args.args[0]]
    assert names.index("Building documentation") < names.index("Building internal dependencies")


def test_internal_deps_rebuilt_when_cached_wheel_deleted(tmp_workspace):
    """A cached wheel that no longer exists is rebuilt."""
    calls = []

    def fake_build_wheel(self):
        calls.append(self.env.project_path)
        self.env.dist_dir_path.mkdir(parents=True, exist_ok=True)
        wheel = self.env.dist_dir_path / "wslib-0.1.0-py3-none-any.whl"
        wheel.write_bytes(b"")
        return wheel

    with (
        patch.object(WindowsBuilder, "clean"),
        patch.object(Compiler, "run_cython"),
        patch.object(Compiler, "_build_wheel", autospec=True, side_effect=fake_build_wheel),
    ):
        WindowsBuilder(tmp_workspace.app).build_internal_deps()
        (tmp_workspace.lib / "dist" / "wslib-0.1.0-py3-none-any.whl").unlink()
        WindowsBuilder(tmp_workspace.app).build_internal_deps()
    assert calls == [tmp_workspace.lib, tmp_workspace.lib]


# ---------------------------------------------------------------------------
# Integration (slow): real CLI build of a whole workspace
# ---------------------------------------------------------------------------


@pytest.mark.slow
@pytest.mark.skipif(shutil.which("uv") is None, reason="uv not on PATH")
def test_cli_build_windows_all_packages_real(tmp_workspace, monkeypatch):
    """'build windows --all-packages' really builds every member's wheel in order."""
    root = tmp_workspace.root
    make_member(
        root,
        "wsplugin",
        version="0.5.0",
        mode="wheel_only",
        dependencies=["wslib>=0.1"],
        workspace_sources=["wslib"],
        extra_project='license-files = ["LICENSE"]\n',
    )
    (root / "packages" / "wsplugin" / "LICENSE").write_text("MIT\n")
    # The app is a library here too, so no PyInstaller / Inno Setup is needed.
    (tmp_workspace.app / "scaldys-project.toml").write_text(
        '[windows]\ndeployment_mode = "wheel_only"\n'
    )
    monkeypatch.chdir(root)
    result = runner.invoke(app, ["build", "windows", "--all-packages"])
    assert result.exit_code == 0, result.output

    plugin_wheel = root / "packages" / "wsplugin" / "dist" / "wsplugin-0.5.0-py3-none-any.whl"
    assert (tmp_workspace.lib / "dist" / "wslib-0.1.0-py3-none-any.whl").is_file()
    assert (tmp_workspace.app / "dist" / "wsapp-0.2.0-py3-none-any.whl").is_file()
    assert plugin_wheel.is_file()
    with zipfile.ZipFile(plugin_wheel) as zf:
        metadata = zf.read("wsplugin-0.5.0.dist-info/METADATA").decode()
        names = zf.namelist()
    assert "Requires-Dist: wslib>=0.1" in metadata
    assert "wsplugin-0.5.0.dist-info/licenses/LICENSE" in names
    # The staged pyproject has no workspace sources left.
    staged = (root / "packages" / "wsplugin" / "build" / "compiled" / "pyproject.toml").read_text()
    assert "workspace = true" not in staged
