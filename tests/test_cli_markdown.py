import logging
import tempfile
from pathlib import Path
from unittest.mock import patch

from typer.testing import CliRunner

from scaldys_project.cli.commands.cmd_ci import ci_app
from scaldys_project.cli.commands.cmd_format import format_app
from scaldys_project.common.config import FormatConfig
from scaldys_project.common.docs import check_ci_markdown_drift

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


def test_check_ci_markdown_drift_no_workflow_file():
    """Returns None when .github/workflows/ci.yml does not exist."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        assert check_ci_markdown_drift(root) is None


def test_check_ci_markdown_drift_in_sync():
    """Returns None when CI workflow targets match config."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        wf_dir = root / ".github" / "workflows"
        wf_dir.mkdir(parents=True)
        (wf_dir / "ci.yml").write_text(
            "jobs:\n  code_quality:\n    steps:\n      - name: Markdown format check\n        run: uv run mdformat --check README.md\n"
        )
        (root / "README.md").touch()

        # Unconfigured (defaults to README.md) -> matches ci.yml
        assert check_ci_markdown_drift(root) is None

        # Explicit config matching ci.yml
        config = FormatConfig(markdown_targets=["README.md"])
        assert check_ci_markdown_drift(root, config=config) is None


def test_check_ci_markdown_drift_mismatch():
    """Returns descriptive warning when CI workflow targets differ from config."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        wf_dir = root / ".github" / "workflows"
        wf_dir.mkdir(parents=True)
        (wf_dir / "ci.yml").write_text(
            "jobs:\n  code_quality:\n    steps:\n      - name: Markdown format check\n        run: uv run mdformat --check README.md\n"
        )
        config = FormatConfig(markdown_targets=["README.md", "docs/guide.md"])

        drift = check_ci_markdown_drift(root, config=config)
        assert drift is not None
        assert "README.md" in drift
        assert "docs/guide.md" in drift


def test_ci_markdown_logs_drift_warning(caplog):
    """ci markdown logs a warning when CI workflow drift is detected."""
    with (
        patch(
            "scaldys_project.cli.commands.cmd_ci.check_ci_markdown_drift",
            return_value="Workflow drift warning",
        ),
        patch(
            "scaldys_project.cli.commands.cmd_ci.get_markdown_target_files",
            return_value=[Path("README.md")],
        ),
        patch("scaldys_project.cli.commands.cmd_ci._run"),
        caplog.at_level(logging.WARNING),
    ):
        result = runner.invoke(ci_app, ["markdown"])
        assert result.exit_code == 0
        assert any("Workflow drift warning" in r.message for r in caplog.records)
