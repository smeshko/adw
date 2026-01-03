"""Unit tests for logs CLI commands."""

import pytest
from typer.testing import CliRunner

from adw.cli.app import app


@pytest.fixture
def runner() -> CliRunner:
    """Create CLI test runner."""
    return CliRunner()


class TestLogsCLIStructure:
    """Tests for logs CLI subcommand structure."""

    def test_logs_help_shows_subcommands(self, runner: CliRunner) -> None:
        """Verify logs --help shows available subcommands."""
        result = runner.invoke(app, ["logs", "--help"])
        assert result.exit_code == 0
        assert "snapshots" in result.output
        assert "state" in result.output
        assert "diff" in result.output

    def test_logs_snapshots_requires_run_id(self, runner: CliRunner) -> None:
        """Verify snapshots command requires run_id argument."""
        result = runner.invoke(app, ["logs", "snapshots"])
        assert result.exit_code != 0
        assert "Missing argument" in result.output or "RUN_ID" in result.output

    def test_logs_state_requires_run_id(self, runner: CliRunner) -> None:
        """Verify state command requires run_id argument."""
        result = runner.invoke(app, ["logs", "state"])
        assert result.exit_code != 0
        assert "Missing argument" in result.output or "RUN_ID" in result.output

    def test_logs_diff_requires_run_id(self, runner: CliRunner) -> None:
        """Verify diff command requires run_id argument."""
        result = runner.invoke(app, ["logs", "diff"])
        assert result.exit_code != 0
        assert "Missing argument" in result.output or "RUN_ID" in result.output

    def test_logs_diff_requires_comparison_targets(self, runner: CliRunner) -> None:
        """Verify diff command requires phase or snapshot options."""
        result = runner.invoke(app, ["logs", "diff", "test-run-id"])
        assert result.exit_code == 1
        assert "Must specify comparison targets" in result.output

    def test_logs_diff_rejects_mixed_options(self, runner: CliRunner) -> None:
        """Verify diff command rejects mixing phase and snapshot options."""
        result = runner.invoke(
            app,
            [
                "logs",
                "diff",
                "test-run-id",
                "--from-phase",
                "plan",
                "--from-snapshot",
                "1",
            ],
        )
        assert result.exit_code == 1
        assert "Cannot mix" in result.output
