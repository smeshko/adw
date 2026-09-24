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

    def test_verbose_dry_run_prints_debug_lines(self) -> None:
        """-v shows DEBUG log lines on a dry run (B8)."""
        result = runner.invoke(app, ["-v", "run", "--dry-run", "x"])

        assert result.exit_code == 0, result.output
        assert "[DEBUG] Input treated as feature string" in result.output

    def test_default_dry_run_prints_no_debug_lines(self) -> None:
        """Without -v a dry run prints no DEBUG or resolver lines."""
        result = runner.invoke(app, ["run", "--dry-run", "x"])

        assert result.exit_code == 0, result.output
        assert "[DEBUG]" not in result.output
        assert "Input treated as" not in result.output
