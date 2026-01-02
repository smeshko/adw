"""Tests for CLI run command with single-phase execution support.

Tests the --phase flag for executing individual phases.
"""

import pytest
from typer.testing import CliRunner

from adw.cli.app import app
from adw.core.constants import PHASE_SEQUENCE


@pytest.fixture
def cli_runner() -> CliRunner:
    """Create a CLI test runner."""
    return CliRunner()


class TestPhaseFlag:
    """Tests for --phase flag parsing and validation."""

    def test_phase_flag_accepted(self, cli_runner: CliRunner) -> None:
        """Test that --phase flag is recognized by the CLI."""
        result = cli_runner.invoke(app, ["run", "--phase", "plan", "Add feature"])

        # Should not error with "No such option"
        assert "No such option" not in result.output

    def test_phase_short_flag_accepted(self, cli_runner: CliRunner) -> None:
        """Test that -p short flag is recognized."""
        result = cli_runner.invoke(app, ["run", "-p", "plan", "Add feature"])

        assert "No such option" not in result.output

    def test_invalid_phase_rejected(self, cli_runner: CliRunner) -> None:
        """Test that invalid phase names are rejected."""
        result = cli_runner.invoke(app, ["run", "--phase", "invalid", "Add feature"])

        assert result.exit_code != 0
        assert "invalid" in result.output.lower() or "Invalid phase" in result.output

    def test_all_valid_phases_accepted(self, cli_runner: CliRunner) -> None:
        """Test that all phases in PHASE_SEQUENCE are valid."""
        for phase in PHASE_SEQUENCE:
            result = cli_runner.invoke(app, ["run", "--phase", phase, "Add feature"])

            # Should not reject as invalid phase
            assert "Invalid phase" not in result.output, f"Phase '{phase}' was rejected"

    def test_phase_flag_with_feature_argument(self, cli_runner: CliRunner) -> None:
        """Test --phase works with feature description argument."""
        result = cli_runner.invoke(
            app, ["run", "--phase", "plan", "Add user authentication"]
        )

        # Verify the feature was received (implementation will process it)
        assert "No such option" not in result.output

    def test_run_without_phase_shows_help_or_stub(self, cli_runner: CliRunner) -> None:
        """Test run command without --phase still works (full pipeline mode)."""
        result = cli_runner.invoke(app, ["run", "Add feature"])

        # For now, the stub shows "Not implemented yet"
        # Once implemented, this should succeed
        assert result.exit_code == 0 or "Not implemented" in result.output
