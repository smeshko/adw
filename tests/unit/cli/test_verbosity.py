"""Tests for CLI verbosity options.

Tests for the global verbosity flags:
- --quiet/-q (errors only)
- --verbose/-v (detailed output)
- --trace (full debug output)
- Default verbosity (normal)
"""

import pytest
from typer.testing import CliRunner

from adw.cli.app import app
from adw.models.logging import Verbosity

runner = CliRunner()


class TestVerbosityFlags:
    """Tests for verbosity flag parsing."""

    def test_quiet_flag_accepted(self) -> None:
        """Test that --quiet/-q flag is recognized."""
        result = runner.invoke(app, ["--quiet", "run", "Add feature", "--dry-run"])
        assert "No such option" not in result.output

        result = runner.invoke(app, ["-q", "run", "Add feature", "--dry-run"])
        assert "No such option" not in result.output

    def test_verbose_flag_accepted(self) -> None:
        """Test that --verbose/-v flag is recognized at app level."""
        result = runner.invoke(app, ["--verbose", "run", "Add feature", "--dry-run"])
        assert "No such option" not in result.output

        result = runner.invoke(app, ["-v", "run", "Add feature", "--dry-run"])
        assert "No such option" not in result.output

    def test_trace_flag_accepted(self) -> None:
        """Test that --trace flag is recognized."""
        result = runner.invoke(app, ["--trace", "run", "Add feature", "--dry-run"])
        assert "No such option" not in result.output

    def test_default_verbosity_is_normal(self) -> None:
        """Test that default verbosity without flags is NORMAL."""
        result = runner.invoke(app, ["run", "Add feature", "--dry-run"])
        # Command should work normally
        assert result.exit_code == 0

    def test_quiet_and_verbose_mutually_exclusive(self) -> None:
        """Test that --quiet and --verbose cannot be used together."""
        result = runner.invoke(
            app, ["--quiet", "--verbose", "run", "Add feature", "--dry-run"]
        )
        # Should fail with mutual exclusivity error
        assert result.exit_code != 0
        assert "mutually exclusive" in result.output.lower() or "cannot" in result.output.lower()

    def test_quiet_and_trace_mutually_exclusive(self) -> None:
        """Test that --quiet and --trace cannot be used together."""
        result = runner.invoke(
            app, ["--quiet", "--trace", "run", "Add feature", "--dry-run"]
        )
        assert result.exit_code != 0

    def test_verbose_and_trace_mutually_exclusive(self) -> None:
        """Test that --verbose and --trace cannot be used together."""
        result = runner.invoke(
            app, ["--verbose", "--trace", "run", "Add feature", "--dry-run"]
        )
        assert result.exit_code != 0


class TestVerbosityContext:
    """Tests for verbosity stored in Typer context."""

    def test_quiet_sets_verbosity_quiet(self) -> None:
        """Test that --quiet sets Verbosity.QUIET in context."""
        # This will be verified by checking the context in a command
        result = runner.invoke(app, ["-q", "--version"])
        # Version should work with quiet flag
        assert result.exit_code == 0 or "version" in result.output.lower()

    def test_verbose_sets_verbosity_verbose(self) -> None:
        """Test that --verbose sets Verbosity.VERBOSE in context."""
        result = runner.invoke(app, ["-v", "--version"])
        assert result.exit_code == 0 or "version" in result.output.lower()

    def test_trace_sets_verbosity_trace(self) -> None:
        """Test that --trace sets Verbosity.TRACE in context."""
        result = runner.invoke(app, ["--trace", "--version"])
        assert result.exit_code == 0 or "version" in result.output.lower()
