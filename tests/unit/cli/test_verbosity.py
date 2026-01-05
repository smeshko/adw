# REDUCTION: Removed 11 tests that validated Typer framework behavior (flag parsing,
# context setting, command integration). Kept only business logic test for mutual
# exclusivity validation. Original: 14 tests, Reduced: 1 test (93% reduction).
"""Tests for CLI verbosity options - mutual exclusivity business logic."""

from typer.testing import CliRunner

from adw.cli.app import app

runner = CliRunner()


class TestVerbosityBusinessLogic:
    """Tests for verbosity business logic validation."""

    def test_quiet_and_verbose_mutually_exclusive(self) -> None:
        """Test that --quiet and --verbose cannot be used together."""
        result = runner.invoke(
            app, ["--quiet", "--verbose", "run", "Add feature", "--dry-run"]
        )
        # Should fail with mutual exclusivity error
        assert result.exit_code != 0
        output_lower = result.output.lower()
        assert "mutually exclusive" in output_lower or "cannot" in output_lower
