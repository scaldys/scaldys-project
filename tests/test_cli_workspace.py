"""CLI tests: --package / --all-packages run once per target, libraries first."""

from pathlib import Path
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from scaldys_project.cli.cli import app
from tests.conftest import make_member

runner = CliRunner()


def _builder_paths(mock_builder: MagicMock) -> list[Path]:
    return [c.args[0] for c in mock_builder.call_args_list]


def test_build_clean_all_packages(tmp_workspace, monkeypatch):
    """build clean --all-packages creates one builder per member, libraries first."""
    monkeypatch.chdir(tmp_workspace.root)
    with patch("scaldys_project.cli.commands.cmd_build.WindowsBuilder") as builder:
        result = runner.invoke(app, ["build", "clean", "--all-packages"])
    assert result.exit_code == 0, result.output
    assert _builder_paths(builder) == [tmp_workspace.lib, tmp_workspace.app]
    assert builder.return_value.clean.call_count == 2


def test_build_all_package_selection_order(tmp_workspace, monkeypatch):
    """-p is repeatable and is reordered topologically."""
    monkeypatch.chdir(tmp_workspace.root)
    with patch("scaldys_project.cli.commands.cmd_build.WindowsBuilder") as builder:
        result = runner.invoke(app, ["build", "all", "-p", "wsapp", "-p", "wslib"])
    assert result.exit_code == 0, result.output
    assert _builder_paths(builder) == [tmp_workspace.lib, tmp_workspace.app]
    assert builder.return_value.main.call_count == 2


def test_build_stops_on_first_failure(tmp_workspace, monkeypatch):
    """A failing member stops the loop; later members are not built."""
    monkeypatch.chdir(tmp_workspace.root)
    with patch("scaldys_project.cli.commands.cmd_build.WindowsBuilder") as builder:
        builder.return_value.build_distribution.side_effect = RuntimeError("boom")
        result = runner.invoke(app, ["build", "windows", "--all-packages"])
    assert result.exit_code != 0
    assert _builder_paths(builder) == [tmp_workspace.lib]


def test_build_at_virtual_root_without_selection_fails(tmp_workspace, monkeypatch):
    """At a virtual root, no selection exits with code 2 before building anything."""
    monkeypatch.chdir(tmp_workspace.root)
    with patch("scaldys_project.cli.commands.cmd_build.WindowsBuilder") as builder:
        result = runner.invoke(app, ["build", "all"])
    assert result.exit_code == 2
    builder.assert_not_called()


def test_build_in_member_uses_that_member(tmp_workspace, monkeypatch):
    """Without a selection, the member at the cwd is built."""
    monkeypatch.chdir(tmp_workspace.lib)
    with patch("scaldys_project.cli.commands.cmd_build.WindowsBuilder") as builder:
        result = runner.invoke(app, ["build", "docs"])
    assert result.exit_code == 0, result.output
    assert _builder_paths(builder) == [tmp_workspace.lib]


def test_check_all_packages(tmp_workspace, monkeypatch):
    """check --all-packages checks each member in order."""
    monkeypatch.chdir(tmp_workspace.root)
    with patch("scaldys_project.cli.commands.cmd_check.WindowsBuilder") as builder:
        builder.return_value.env.config.windows.deployment_mode = "wheel_only"
        result = runner.invoke(app, ["check", "--all-packages"])
    assert result.exit_code == 0, result.output
    assert _builder_paths(builder) == [tmp_workspace.lib, tmp_workspace.app]


def test_test_per_member_and_virtual_root(tmp_workspace, monkeypatch):
    """test runs 'uv run --package' per member, or plain pytest at a virtual root."""
    monkeypatch.chdir(tmp_workspace.root)
    with patch("scaldys_project.cli.commands.cmd_test.subprocess.run") as run:
        run.return_value.returncode = 0
        result = runner.invoke(app, ["test", "--all-packages"])
        assert result.exit_code == 0, result.output
        cmds = [c.args[0] for c in run.call_args_list]
        cwds = {c.kwargs["cwd"] for c in run.call_args_list}
        assert cmds[0][:6] == ["uv", "run", "--package", "wslib", "pytest", "packages/wslib/tests"]
        assert cmds[1][:6] == ["uv", "run", "--package", "wsapp", "pytest", "packages/wsapp/tests"]
        assert cwds == {tmp_workspace.root}

        run.reset_mock()
        result = runner.invoke(app, ["test"])
        assert result.exit_code == 0, result.output
        assert run.call_args.args[0][:3] == ["uv", "run", "pytest"]
        assert run.call_args.kwargs["cwd"] == tmp_workspace.root


def test_publish_skips_private_members(tmp_workspace, monkeypatch):
    """publish --all-packages skips members with the Private classifier."""
    make_member(
        tmp_workspace.root,
        "wsprivate",
        version="1.0",
        mode="pyinstaller",
        extra_project='classifiers = ["Private :: Do Not Upload"]\n',
    )
    monkeypatch.chdir(tmp_workspace.root)
    with patch("scaldys_project.cli.commands.cmd_publish._publish_one") as publish_one:
        result = runner.invoke(app, ["publish", "--all-packages"])
    assert result.exit_code == 0, result.output
    published = [c.args[0] for c in publish_one.call_args_list]
    assert published == [tmp_workspace.lib, tmp_workspace.app]


def test_ci_typecheck_in_workspace(tmp_workspace, monkeypatch):
    """ci typecheck syncs all packages and lets the root [tool.pyright] pick the paths."""
    root_pyproject = tmp_workspace.root / "pyproject.toml"
    root_pyproject.write_text(
        root_pyproject.read_text() + '\n[tool.pyright]\ninclude = ["packages"]\n'
    )
    monkeypatch.chdir(tmp_workspace.lib)
    with patch("scaldys_project.cli.commands.cmd_ci.subprocess.run") as run:
        run.return_value.returncode = 0
        run.return_value.stdout = ""
        run.return_value.stderr = ""
        result = runner.invoke(app, ["ci", "typecheck"])
    assert result.exit_code == 0, result.output
    cmds = [c.args[0] for c in run.call_args_list]
    assert cmds == [["uv", "sync", "--all-packages"], ["uv", "run", "pyright"]]
    assert {c.kwargs["cwd"] for c in run.call_args_list} == {tmp_workspace.root}


def test_ci_doclint_lints_every_member_docs(tmp_workspace, monkeypatch):
    """ci doclint passes the root and every member docs/ folder to sphinx-lint."""
    (tmp_workspace.root / "docs").mkdir()
    (tmp_workspace.app / "docs").mkdir()
    monkeypatch.chdir(tmp_workspace.root)
    with patch("scaldys_project.cli.commands.cmd_ci.subprocess.run") as run:
        run.return_value.returncode = 0
        run.return_value.stdout = ""
        run.return_value.stderr = ""
        result = runner.invoke(app, ["ci", "doclint"])
    assert result.exit_code == 0, result.output
    assert run.call_args.args[0] == ["uv", "run", "sphinx-lint", "docs/", "packages/wsapp/docs/"]


def test_init_refuses_inside_workspace(tmp_workspace, monkeypatch):
    """init refuses to run inside an existing uv workspace."""
    monkeypatch.chdir(tmp_workspace.lib)
    with patch("scaldys_project.cli.commands.cmd_init._collect_params") as collect:
        result = runner.invoke(app, ["init"])
    assert result.exit_code == 1
    collect.assert_not_called()


def test_ci_typecheck_without_root_pyright_config(tmp_workspace, monkeypatch):
    """Without a root [tool.pyright], every member's source root and tests/ are checked."""
    monkeypatch.chdir(tmp_workspace.root)
    with patch("scaldys_project.cli.commands.cmd_ci.subprocess.run") as run:
        run.return_value.returncode = 0
        run.return_value.stdout = ""
        run.return_value.stderr = ""
        result = runner.invoke(app, ["ci", "typecheck"])
    assert result.exit_code == 0, result.output
    assert run.call_args.args[0] == [
        "uv",
        "run",
        "pyright",
        "packages/wsapp/src",
        "packages/wsapp/tests",
        "packages/wslib/src",
        "packages/wslib/tests",
    ]


# ---------------------------------------------------------------------------
# Summary table (package, version, result)
# ---------------------------------------------------------------------------


def _summary_rows(output: str) -> list[list[str]]:
    """Return the body rows of the Rich summary table as lists of cell texts."""
    rows = []
    for line in output.splitlines():
        if line.startswith("│"):
            rows.append([cell.strip() for cell in line.strip("│").split("│")])
    assert rows and rows[0] == ["Package", "Version", "Result"], output
    return rows[1:]


def test_summary_all_packages_shows_versions(tmp_workspace, monkeypatch):
    """build all --all-packages: one header per member and a summary with versions."""
    monkeypatch.chdir(tmp_workspace.root)
    with patch("scaldys_project.cli.commands.cmd_build.WindowsBuilder"):
        result = runner.invoke(app, ["build", "all", "--all-packages"])
    assert result.exit_code == 0, result.output
    assert "Build: wslib" in result.output
    assert "Build: wsapp" in result.output
    assert "Build summary" in result.output
    assert "Version" in result.output
    assert _summary_rows(result.output) == [["wslib", "0.1.0", "ok"], ["wsapp", "0.2.0", "ok"]]


def test_summary_after_failure_shows_not_run(tmp_workspace, monkeypatch):
    """A failure still prints the summary: failed member and the ones not run."""
    monkeypatch.chdir(tmp_workspace.root)
    with patch("scaldys_project.cli.commands.cmd_build.WindowsBuilder") as builder:
        builder.return_value.main.side_effect = SystemExit(1)
        result = runner.invoke(app, ["build", "all", "--all-packages"])
    assert result.exit_code == 1
    assert _summary_rows(result.output) == [
        ["wslib", "0.1.0", "failed"],
        ["wsapp", "0.2.0", "not run"],
    ]


def test_summary_single_package(tmp_workspace, monkeypatch):
    """-p NAME (one member): summary table printed, but no per-target header."""
    monkeypatch.chdir(tmp_workspace.root)
    with patch("scaldys_project.cli.commands.cmd_build.WindowsBuilder"):
        result = runner.invoke(app, ["build", "all", "-p", "wsapp"])
    assert result.exit_code == 0, result.output
    assert "Build: wsapp" not in result.output
    assert "Build summary" in result.output
    assert _summary_rows(result.output) == [["wsapp", "0.2.0", "ok"]]


def test_summary_member_at_cwd(tmp_workspace, monkeypatch):
    """No selection inside a member: summary for that member."""
    monkeypatch.chdir(tmp_workspace.lib)
    with patch("scaldys_project.cli.commands.cmd_check.WindowsBuilder") as builder:
        builder.return_value.env.config.windows.deployment_mode = "wheel_only"
        result = runner.invoke(app, ["check"])
    assert result.exit_code == 0, result.output
    assert "Check summary" in result.output
    assert _summary_rows(result.output) == [["wslib", "0.1.0", "ok"]]


def test_summary_standalone_project(tmp_path, monkeypatch):
    """A plain uv project (no workspace) also gets the summary table."""
    project = tmp_path / "solo"
    project.mkdir()
    (project / "pyproject.toml").write_text(
        '[project]\nname = "solo"\nversion = "3.4.5"\n', encoding="utf-8"
    )
    monkeypatch.chdir(project)
    with patch("scaldys_project.cli.commands.cmd_build.WindowsBuilder"):
        result = runner.invoke(app, ["build", "clean"])
    assert result.exit_code == 0, result.output
    assert "Clean: solo" not in result.output
    assert "Clean summary" in result.output
    assert _summary_rows(result.output) == [["solo", "3.4.5", "ok"]]
