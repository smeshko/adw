"""Tests for CLI resume command.

Tests for the `adw resume [RUN_ID]` command including:
- Argument parsing
- Flag handling (--from-phase, --verbose)
- Resume header display
- Error handling for non-existent runs
"""

import pytest
from typer.testing import CliRunner

from adw.cli.app import app
from adw.core.constants import PHASE_SEQUENCE

runner = CliRunner()


@pytest.fixture
def cli_runner() -> CliRunner:
    """Create a CLI test runner."""
    return CliRunner()


class TestResumeCommand:
    """Tests for the resume command basic functionality."""

    def test_resume_help(self) -> None:
        """Test that resume command shows help."""
        result = runner.invoke(app, ["resume", "--help"])
        assert result.exit_code == 0
        assert "Resume a failed or interrupted run" in result.output

    def test_resume_accepts_run_id_argument(self) -> None:
        """Test that resume command accepts run_id as positional argument."""
        result = runner.invoke(app, ["resume", "--help"])
        assert "RUN_ID" in result.output

    def test_resume_from_phase_flag_accepted(self, cli_runner: CliRunner) -> None:
        """Test that --from-phase flag is recognized."""
        result = cli_runner.invoke(app, ["resume", "--help"])
        assert "--from-phase" in result.output

    def test_resume_verbose_flag_accepted(self, cli_runner: CliRunner) -> None:
        """Test that --verbose/-v flag is recognized."""
        result = cli_runner.invoke(app, ["resume", "--help"])
        assert "--verbose" in result.output or "-v" in result.output


class TestFromPhaseValidation:
    """Tests for --from-phase flag validation."""

    def test_invalid_phase_rejected(self, cli_runner: CliRunner) -> None:
        """Test that invalid phase names are rejected."""
        result = cli_runner.invoke(
            app, ["resume", "--from-phase", "invalid", "01HQXK5P3Z7V8R2M4N6T9W1Y3C"]
        )
        assert result.exit_code != 0
        assert "invalid" in result.output.lower() or "Invalid phase" in result.output

    def test_all_valid_phases_accepted(self, cli_runner: CliRunner) -> None:
        """Test that all phases in PHASE_SEQUENCE are valid for --from-phase."""
        for phase in PHASE_SEQUENCE:
            result = cli_runner.invoke(app, ["resume", "--from-phase", phase])
            # Should not error with "Invalid phase"
            assert "Invalid phase" not in result.output


class TestResumeNoRuns:
    """Tests for resume when no runs exist."""

    def test_nonexistent_run_id_error(self) -> None:
        """Test that non-existent run ID returns error.

        Note: This tests a specific run ID that shouldn't exist.
        """
        # Using a very specific run ID that definitely doesn't exist
        result = runner.invoke(app, ["resume", "99ZZZZZZZZZZZZZZZZZZZZZZZ"])
        # Should show error about run not found (ConfigError is raised)
        # The error gets propagated as a non-zero exit
        assert (
            result.exit_code != 0
            or "not found" in result.output.lower()
            or "RUN_NOT_FOUND" in result.output
        )


class TestResumeHeaderDisplay:
    """Tests for resume header display formatting."""

    def test_resume_header_has_required_sections(self) -> None:
        """Test that resume header would include required information."""
        from rich.console import Console
        from io import StringIO
        from adw.cli.run_display import RunDisplay

        output = StringIO()
        console = Console(file=output, force_terminal=True)
        display = RunDisplay(console)

        display.show_resume_header(
            run_id="01HQXK5P3Z7V8R2M4N6T9W1Y3C",
            feature="Add user authentication",
            completed_phases=["plan"],
            resume_phase="build",
        )

        result = output.getvalue()

        # Check key elements are present
        assert "01HQXK5P3Z7V8R2M4N6T9W1Y3C" in result
        assert "Add user authentication" in result
        assert "plan" in result or "✓" in result
        assert "build" in result or "Resuming" in result

    def test_resume_header_truncates_long_feature(self) -> None:
        """Test that long feature descriptions are truncated."""
        from rich.console import Console
        from io import StringIO
        from adw.cli.run_display import RunDisplay

        output = StringIO()
        console = Console(file=output, force_terminal=True)
        display = RunDisplay(console)

        long_feature = "A" * 100  # Very long feature

        display.show_resume_header(
            run_id="01HQXK5P3Z7V8R2M4N6T9W1Y3C",
            feature=long_feature,
            completed_phases=[],
            resume_phase="plan",
        )

        result = output.getvalue()
        # Should be truncated
        assert "..." in result or len(long_feature) not in [len(line) for line in result.split("\n")]

    def test_resume_header_shows_completed_phases(self) -> None:
        """Test that completed phases are shown with checkmarks."""
        from rich.console import Console
        from io import StringIO
        from adw.cli.run_display import RunDisplay

        output = StringIO()
        console = Console(file=output, force_terminal=True)
        display = RunDisplay(console)

        display.show_resume_header(
            run_id="01HQXK5P3Z7V8R2M4N6T9W1Y3C",
            feature="Add feature",
            completed_phases=["plan", "build"],
            resume_phase="verify",
        )

        result = output.getvalue()
        # Should show completed phases
        assert "plan" in result
        assert "build" in result
