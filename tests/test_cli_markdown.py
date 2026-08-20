from pathlib import Path
from unittest.mock import patch

from typer.testing import CliRunner

from scaldys_project.cli.commands.cmd_ci import ci_app
from scaldys_project.cli.commands.cmd_format import format_app

runner = CliRunner()


def test_ci_markdown_no_files():
    """ci markdown exits cleanly when no markdown files match."""
    with (
        patch("scaldys_project.cli.commands.cmd_ci.get_markdown_target_files", return_value=[]),
        patch("scaldys_project.cli.commands.cmd_ci._run") as mock_run,
    ):
        result = runner.invoke(ci_app, ["markdown"])
        assert result.exit_code == 0
        mock_run.assert_not_called()


def test_ci_markdown_with_files():
    """ci markdown calls mdformat --check on target files."""
    targets = [Path("README.md"), Path("docs/site/index.md")]
    with (
        patch(
            "scaldys_project.cli.commands.cmd_ci.get_markdown_target_files", return_value=targets
        ),
        patch("scaldys_project.cli.commands.cmd_ci._run") as mock_run,
    ):
        result = runner.invoke(ci_app, ["markdown"])
        assert result.exit_code == 0
        mock_run.assert_called_once_with(
            ["uv", "run", "mdformat", "--check", "README.md", str(Path("docs/site/index.md"))]
        )


def test_format_markdown_no_files():
    """format markdown exits cleanly when no markdown files match."""
    with (
        patch("scaldys_project.cli.commands.cmd_format.get_markdown_target_files", return_value=[]),
        patch("scaldys_project.cli.commands.cmd_format._run") as mock_run,
    ):
        result = runner.invoke(format_app, ["markdown"])
        assert result.exit_code == 0
        mock_run.assert_not_called()


def test_format_markdown_with_files():
    """format markdown calls mdformat on target files."""
    targets = [Path("README.md"), Path("docs/site/index.md")]
    with (
        patch(
            "scaldys_project.cli.commands.cmd_format.get_markdown_target_files",
            return_value=targets,
        ),
        patch("scaldys_project.cli.commands.cmd_format._run") as mock_run,
    ):
        result = runner.invoke(format_app, ["markdown"])
        assert result.exit_code == 0
        mock_run.assert_called_once_with(
            ["uv", "run", "mdformat", "README.md", str(Path("docs/site/index.md"))]
        )
