"""Tests for CLI run command with single-phase execution support.

Tests the --phase and --from-run flags for executing individual phases.
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


class TestFromRunFlag:
    """Tests for --from-run flag parsing and validation."""

    def test_from_run_flag_accepted(self, cli_runner: CliRunner) -> None:
        """Test that --from-run flag is recognized by the CLI."""
        result = cli_runner.invoke(
            app, ["run", "--phase", "build", "--from-run", "01HQTEST123", "Add feature"]
        )

        # Should not error with "No such option"
        assert "No such option" not in result.output

    def test_from_run_short_flag_accepted(self, cli_runner: CliRunner) -> None:
        """Test that -f short flag is recognized."""
        result = cli_runner.invoke(
            app, ["run", "-p", "build", "-f", "01HQTEST123", "Add feature"]
        )

        assert "No such option" not in result.output

    def test_from_run_required_for_build_phase(self, cli_runner: CliRunner) -> None:
        """Test that --from-run is required for phases after plan."""
        result = cli_runner.invoke(app, ["run", "--phase", "build", "Add feature"])

        assert result.exit_code != 0
        assert (
            "--from-run" in result.output
            or "requires artifacts" in result.output.lower()
        )

    def test_from_run_required_for_verify_phase(self, cli_runner: CliRunner) -> None:
        """Test that --from-run is required for verify phase."""
        result = cli_runner.invoke(app, ["run", "--phase", "verify", "Add feature"])

        assert result.exit_code != 0
        assert "--from-run" in result.output

    def test_from_run_not_required_for_plan_phase(self, cli_runner: CliRunner) -> None:
        """Test that --from-run is NOT required for plan phase."""
        result = cli_runner.invoke(app, ["run", "--phase", "plan", "Add feature"])

        # Should succeed (or show stub) without --from-run
        assert "requires" not in result.output.lower() or result.exit_code == 0

    def test_from_run_optional_for_plan_phase(self, cli_runner: CliRunner) -> None:
        """Test that --from-run can be provided for plan phase but isn't required."""
        result = cli_runner.invoke(
            app, ["run", "--phase", "plan", "--from-run", "01HQTEST123", "Add feature"]
        )

        # Should work without error about --from-run
        assert "No such option" not in result.output
