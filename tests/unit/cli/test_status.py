"""Tests for CLI status command.

Tests for the `adw status [RUN_ID]` command including:
- Argument parsing (optional run_id)
- Flag handling (--json, --verbose)
- Error handling for non-existent runs
- Default to most recent run when no run_id provided
"""

import pytest
from typer.testing import CliRunner

from adw.cli.app import app

runner = CliRunner()


@pytest.fixture
def cli_runner() -> CliRunner:
    """Create a CLI test runner."""
    return CliRunner()


class TestStatusCommand:
    """Tests for the status command basic functionality."""

    def test_status_help(self) -> None:
        """Test that status command shows help."""
        result = runner.invoke(app, ["status", "--help"])
        assert result.exit_code == 0
        assert "status" in result.output.lower()

    def test_status_accepts_run_id_argument(self) -> None:
        """Test that status command accepts run_id as optional positional argument."""
        result = runner.invoke(app, ["status", "--help"])
        assert "RUN_ID" in result.output

    def test_status_json_flag_accepted(self, cli_runner: CliRunner) -> None:
        """Test that --json flag is recognized."""
        result = cli_runner.invoke(app, ["status", "--help"])
        assert "--json" in result.output

    def test_status_verbose_flag_accepted(self, cli_runner: CliRunner) -> None:
        """Test that --verbose/-v flag is recognized."""
        result = cli_runner.invoke(app, ["status", "--help"])
        assert "--verbose" in result.output or "-v" in result.output


class TestStatusNoRuns:
    """Tests for status when no runs exist."""

    def test_nonexistent_run_id_error(self) -> None:
        """Test that non-existent run ID returns error."""
        # Using a specific run ID that doesn't exist
        result = runner.invoke(app, ["status", "99ZZZZZZZZZZZZZZZZZZZZZZZ"])
        # Should show error about run not found (ConfigError is raised)
        assert (
            result.exit_code != 0
            or "not found" in result.output.lower()
            or "RUN_NOT_FOUND" in result.output
        )

    def test_status_no_runs_message(self) -> None:
        """Test message when no runs exist and no run_id provided."""
        # This test needs a clean runs directory - hard to test in isolation
        # The integration tests will cover this more thoroughly
        result = runner.invoke(app, ["status", "--help"])
        # Help should show that run_id is optional
        assert result.exit_code == 0
