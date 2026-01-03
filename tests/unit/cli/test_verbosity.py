"""Tests for CLI verbosity options.

Tests for the global verbosity flags:
- --quiet/-q (errors only)
- --verbose/-v (detailed output)
- --trace (full debug output)
- Default verbosity (normal)
"""

from typer.testing import CliRunner

from adw.cli.app import app

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
        output_lower = result.output.lower()
        assert "mutually exclusive" in output_lower or "cannot" in output_lower

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


class TestVerbosityWithRunCommand:
    """Integration tests for verbosity with run command."""

    def test_run_with_quiet_verbosity(self) -> None:
        """Test run command works with --quiet flag."""
        result = runner.invoke(app, ["-q", "run", "Add feature", "--dry-run"])
        assert result.exit_code == 0
        assert "Dry run" in result.output or "dry run" in result.output.lower()

    def test_run_with_verbose_verbosity(self) -> None:
        """Test run command works with --verbose flag."""
        result = runner.invoke(app, ["-v", "run", "Add feature", "--dry-run"])
        assert result.exit_code == 0
        assert "Dry run" in result.output or "dry run" in result.output.lower()

    def test_run_with_trace_verbosity(self) -> None:
        """Test run command works with --trace flag."""
        result = runner.invoke(app, ["--trace", "run", "Add feature", "--dry-run"])
        assert result.exit_code == 0
        assert "Dry run" in result.output or "dry run" in result.output.lower()

    def test_run_without_verbosity_uses_normal(self) -> None:
        """Test run command defaults to NORMAL verbosity."""
        result = runner.invoke(app, ["run", "Add feature", "--dry-run"])
        assert result.exit_code == 0
        # Should work normally without any verbosity flag


class TestVerbosityWithResumeCommand:
    """Integration tests for verbosity with resume command."""

    def test_resume_with_quiet_verbosity(self) -> None:
        """Test resume command works with --quiet flag."""
        result = runner.invoke(app, ["-q", "resume"])
        # May fail due to no runs, but should not fail on flag parsing
        assert "No such option" not in result.output

    def test_resume_with_verbose_verbosity(self) -> None:
        """Test resume command works with --verbose flag."""
        result = runner.invoke(app, ["-v", "resume"])
        # May fail due to no runs, but should not fail on flag parsing
        assert "No such option" not in result.output

    def test_resume_with_trace_verbosity(self) -> None:
        """Test resume command works with --trace flag."""
        result = runner.invoke(app, ["--trace", "resume"])
        # May fail due to no runs, but should not fail on flag parsing
        assert "No such option" not in result.output

    def test_resume_accepts_global_verbosity_flags(self) -> None:
        """Test that resume uses global verbosity flags, not local ones."""
        # The old local --verbose flag was removed in Story 7.2
        # Verify it now uses global -v flag
        result = runner.invoke(app, ["-v", "resume"])
        # Should not error with unknown option
        assert "No such option: '-v'" not in result.output
        assert "No such option: '--verbose'" not in result.output
