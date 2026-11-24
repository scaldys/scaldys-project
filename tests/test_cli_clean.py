from unittest.mock import patch

from typer.testing import CliRunner

from scaldys_project.cli.cli import app

runner = CliRunner()


def test_clean_help():
    """clean command displays help with subcommands docs, windows, all."""
    result = runner.invoke(app, ["clean", "--help"])
    assert result.exit_code == 0
    assert "all" in result.output
    assert "docs" in result.output
    assert "windows" in result.output


def test_clean_docs_standalone(tmp_path, monkeypatch):
    """clean docs invokes clean_docs on WindowsBuilder for standalone project."""
    project = tmp_path / "solo"
    project.mkdir()
    (project / "pyproject.toml").write_text(
        '[project]\nname = "solo"\nversion = "1.0.0"\n', encoding="utf-8"
    )
    monkeypatch.chdir(project)

    with patch("scaldys_project.cli.commands.cmd_clean.WindowsBuilder") as mock_builder:
        result = runner.invoke(app, ["clean", "docs"])
    assert result.exit_code == 0, result.output
    assert mock_builder.call_args[0][0] == project
    mock_builder.return_value.clean_docs.assert_called_once()
    assert "Clean docs summary" in result.output


def test_clean_windows_standalone(tmp_path, monkeypatch):
    """clean windows invokes clean_windows on WindowsBuilder for standalone project."""
    project = tmp_path / "solo"
    project.mkdir()
    (project / "pyproject.toml").write_text(
        '[project]\nname = "solo"\nversion = "1.0.0"\n', encoding="utf-8"
    )
    monkeypatch.chdir(project)

    with patch("scaldys_project.cli.commands.cmd_clean.WindowsBuilder") as mock_builder:
        result = runner.invoke(app, ["clean", "windows", "-v"])
    assert result.exit_code == 0, result.output
    assert mock_builder.call_args[0][0] == project
    assert mock_builder.call_args[1]["verbose"] is True
    mock_builder.return_value.clean_windows.assert_called_once()
    assert "Clean windows summary" in result.output


def test_clean_all_standalone(tmp_path, monkeypatch):
    """clean all invokes clean_all on WindowsBuilder for standalone project."""
    project = tmp_path / "solo"
    project.mkdir()
    (project / "pyproject.toml").write_text(
        '[project]\nname = "solo"\nversion = "1.0.0"\n', encoding="utf-8"
    )
    monkeypatch.chdir(project)

    with patch("scaldys_project.cli.commands.cmd_clean.WindowsBuilder") as mock_builder:
        result = runner.invoke(app, ["clean", "all"])
    assert result.exit_code == 0, result.output
    assert mock_builder.call_args[0][0] == project
    mock_builder.return_value.clean_all.assert_called_once()
    assert "Clean all summary" in result.output


def test_clean_workspace_package_selection(tmp_workspace, monkeypatch):
    """clean docs -p wsapp targets only wsapp."""
    monkeypatch.chdir(tmp_workspace.root)
    with patch("scaldys_project.cli.commands.cmd_clean.WindowsBuilder") as mock_builder:
        result = runner.invoke(app, ["clean", "docs", "-p", "wsapp"])
    assert result.exit_code == 0, result.output
    mock_builder.assert_called_once_with(tmp_workspace.app, verbose=False)
    mock_builder.return_value.clean_docs.assert_called_once()


def test_clean_workspace_all_packages(tmp_workspace, monkeypatch):
    """clean windows --all-packages targets all workspace members in topological order."""
    monkeypatch.chdir(tmp_workspace.root)
    with patch("scaldys_project.cli.commands.cmd_clean.WindowsBuilder") as mock_builder:
        result = runner.invoke(app, ["clean", "windows", "--all-packages"])
    assert result.exit_code == 0, result.output
    paths = [c.args[0] for c in mock_builder.call_args_list]
    assert paths == [tmp_workspace.lib, tmp_workspace.app]
    assert mock_builder.return_value.clean_windows.call_count == 2


def test_clean_invalid_target_error(tmp_path, monkeypatch):
    """Using --package on a non-workspace project produces an exit code of 2."""
    project = tmp_path / "solo"
    project.mkdir()
    (project / "pyproject.toml").write_text(
        '[project]\nname = "solo"\nversion = "1.0.0"\n', encoding="utf-8"
    )
    monkeypatch.chdir(project)

    result = runner.invoke(app, ["clean", "all", "--package", "pkg"])
    assert result.exit_code == 2


def test_clean_stops_on_first_failure(tmp_workspace, monkeypatch):
    """Failure in one member halts subsequent members and prints summary table."""
    monkeypatch.chdir(tmp_workspace.root)
    with patch("scaldys_project.cli.commands.cmd_clean.WindowsBuilder") as mock_builder:
        mock_builder.return_value.clean_all.side_effect = RuntimeError("Clean failed")
        result = runner.invoke(app, ["clean", "all", "--all-packages"])
    assert result.exit_code != 0
    assert len(mock_builder.call_args_list) == 1
    assert "Clean all summary" in result.output
