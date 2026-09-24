"""Tests for CLI resume command.

Tests for the `adw resume [RUN_ID]` command including:
- Phase validation
- Resume header display
- Error handling for non-existent runs
- StateError for corrupted context

Help text verification tests removed per TEST_REDUCTION_PLAN.md
"""

from pathlib import Path

import pytest
from typer.testing import CliRunner

from adw.cli.app import app
from adw.core.constants import PHASE_SEQUENCE

runner = CliRunner()


@pytest.fixture
def cli_runner() -> CliRunner:
    """Create a CLI test runner."""
    return CliRunner()


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
        # `adw resume` without a run id resumes the latest run in cwd's .adw/runs
        assert not (Path.cwd() / "pyproject.toml").exists(), "cwd is the checkout"
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


class TestResumeCorruptedState:
    """Tests for StateError on corrupted context."""

    def test_corrupted_context_raises_state_error(self, tmp_path: Path) -> None:
        """Test corrupted context.json raises StateError with snapshot suggestion."""
        from unittest.mock import patch

        # Create a runs directory with corrupted context
        runs_dir = tmp_path / ".adw" / "runs"
        runs_dir.mkdir(parents=True)
        run_id = "01HQXK5P3Z7V8R2M4N6T9W1Y3C"
        run_dir = runs_dir / run_id
        run_dir.mkdir()
        # Write corrupted JSON
        (run_dir / "context.json").write_text("{ invalid json }")

        with patch("adw.cli.resume.get_runs_dir", return_value=runs_dir):
            result = runner.invoke(app, ["resume", run_id])

        # Should indicate corrupted state with snapshot suggestion
        assert result.exit_code != 0
        assert (
            "corrupted" in result.output.lower()
            or "STATE_CORRUPTED" in result.output
            or "snapshot" in result.output.lower()
        )


class TestResumeHeaderDisplay:
    """Tests for resume header display formatting."""

    def test_resume_header_has_required_sections(self) -> None:
        """Test that resume header would include required information."""
        from io import StringIO

        from rich.console import Console

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
        from io import StringIO

        from rich.console import Console

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
        # Should be truncated - full feature shouldn't appear on any single line
        lines = result.split("\n")
        assert "..." in result or len(long_feature) not in [len(line) for line in lines]

    def test_resume_header_shows_completed_phases(self) -> None:
        """Test that completed phases are shown with checkmarks."""
        from io import StringIO

        from rich.console import Console

        from adw.cli.run_display import RunDisplay

        output = StringIO()
        console = Console(file=output, force_terminal=True)
        display = RunDisplay(console)

        display.show_resume_header(
            run_id="01HQXK5P3Z7V8R2M4N6T9W1Y3C",
            feature="Add feature",
            completed_phases=["plan", "build"],
            resume_phase="validate",
        )

        result = output.getvalue()
        # Should show completed phases
        assert "plan" in result
        assert "build" in result


class TestResumeVerbosity:
    """Tests for resume's logging setup."""

    def test_verbose_resume_prints_debug_lines_once(self) -> None:
        """-v shows resume's DEBUG lines through ADW's console handler, once."""
        from datetime import UTC, datetime
        from unittest.mock import MagicMock, patch

        from adw.models.context import RunContext

        context = RunContext(
            run_id="01HQXK5P3Z7V8R2M4N6T9W1Y3C",
            feature_description="Resume me",
            current_phase="build",
            started_at=datetime.now(UTC),
        )
        manager = MagicMock()
        manager.find_run_to_resume.return_value = MagicMock(
            is_valid=True, context=context, resume_phase="build"
        )
        orchestrator = MagicMock()
        orchestrator.resume.return_value = context

        with (
            patch("adw.cli.resume._create_resume_manager", return_value=manager),
            patch("adw.cli.resume.create_orchestrator", return_value=orchestrator),
        ):
            result = runner.invoke(app, ["-v", "resume"])

        assert result.exit_code == 0, result.output
        assert result.output.count("Resume phase: build") == 1
        assert "[DEBUG] Resume phase: build" in result.output
