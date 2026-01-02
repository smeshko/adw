"""Unit tests for ProgressDisplay class.

Tests the progress display functionality for the ADW pipeline,
including phase start/completion display, LLM progress with spinner,
and overall progress bar.
"""

from datetime import UTC
from io import StringIO

from rich.console import Console

from adw.cli.progress import ProgressDisplay
from adw.core.constants import PHASE_SEQUENCE


class TestProgressDisplayInit:
    """Tests for ProgressDisplay initialization."""

    def test_init_with_default_console(self) -> None:
        """Test that ProgressDisplay creates its own console if none provided."""
        progress = ProgressDisplay()
        assert progress.console is not None
        assert isinstance(progress.console, Console)

    def test_init_with_custom_console(self) -> None:
        """Test that ProgressDisplay uses provided console."""
        output = StringIO()
        console = Console(file=output, force_terminal=True)
        progress = ProgressDisplay(console=console)
        assert progress.console is console

    def test_init_state(self) -> None:
        """Test that ProgressDisplay initializes with correct state."""
        progress = ProgressDisplay()
        assert progress._current_phase is None
        assert progress._live is None
        assert progress._progress is None


class TestPhaseColors:
    """Tests for phase color configuration."""

    def test_all_phases_have_colors(self) -> None:
        """Test that all phases in PHASE_SEQUENCE have colors defined."""
        progress = ProgressDisplay()
        for phase in PHASE_SEQUENCE:
            assert phase in progress.PHASE_COLORS

    def test_phase_colors_are_strings(self) -> None:
        """Test that all phase colors are valid Rich color strings."""
        progress = ProgressDisplay()
        valid_colors = {"blue", "cyan", "yellow", "magenta", "green", "red", "white"}
        for color in progress.PHASE_COLORS.values():
            assert color in valid_colors


class TestStatusIcons:
    """Tests for status icon configuration."""

    def test_all_status_icons_defined(self) -> None:
        """Test that all required status icons are defined."""
        progress = ProgressDisplay()
        required_statuses = {"pending", "running", "completed", "failed"}
        for status in required_statuses:
            assert status in progress.STATUS_ICONS

    def test_status_icons_are_strings(self) -> None:
        """Test that all status icons are non-empty strings."""
        progress = ProgressDisplay()
        for icon in progress.STATUS_ICONS.values():
            assert isinstance(icon, str)
            assert len(icon) > 0


class TestPhaseStart:
    """Tests for phase start display."""

    def test_on_phase_start_shows_header(self) -> None:
        """Test that phase start shows formatted header."""
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=80)
        progress = ProgressDisplay(console)

        progress.on_phase_start("plan")

        output_text = output.getvalue()
        assert "PLAN" in output_text
        assert "Starting phase" in output_text

    def test_on_phase_start_updates_current_phase(self) -> None:
        """Test that on_phase_start updates internal state."""
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=80)
        progress = ProgressDisplay(console)

        progress.on_phase_start("build")

        assert progress._current_phase == "build"

    def test_on_phase_start_shows_phase_number(self) -> None:
        """Test that phase start shows correct phase number."""
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=80)
        progress = ProgressDisplay(console)

        progress.on_phase_start("verify")

        output_text = output.getvalue()
        # verify is the 3rd phase (index 2), so "Phase 3/5"
        assert "3/5" in output_text

    def test_on_phase_start_uses_phase_color(self) -> None:
        """Test that phase start uses correct color."""
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=80)
        progress = ProgressDisplay(console)

        progress.on_phase_start("plan")

        output_text = output.getvalue()
        # Rich uses escape codes for colors, so just verify the phase name appears
        assert "PLAN" in output_text

    def test_on_phase_start_all_phases(self) -> None:
        """Test that all phases can be started."""
        for phase in PHASE_SEQUENCE:
            output = StringIO()
            console = Console(file=output, force_terminal=True, width=80)
            progress = ProgressDisplay(console)

            progress.on_phase_start(phase)

            output_text = output.getvalue()
            assert phase.upper() in output_text


class TestLLMProgress:
    """Tests for LLM progress display."""

    def test_on_llm_start_creates_progress_bar(self) -> None:
        """Test that on_llm_start creates a progress display."""
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=80)
        progress = ProgressDisplay(console)

        progress.on_llm_start()

        assert progress._progress is not None
        assert progress._live is not None
        assert progress._task_id is not None

        # Cleanup
        progress.on_llm_complete()

    def test_on_llm_progress_updates_token_count(self) -> None:
        """Test that on_llm_progress updates the token display."""
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=80)
        progress = ProgressDisplay(console)

        progress.on_llm_start()
        progress.on_llm_progress(100)

        # Should not raise - just verify it completes
        assert progress._progress is not None
        assert progress._task_id is not None

        # Cleanup
        progress.on_llm_complete()

    def test_on_llm_complete_clears_state(self) -> None:
        """Test that on_llm_complete clears internal state."""
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=80)
        progress = ProgressDisplay(console)

        progress.on_llm_start()
        progress.on_llm_complete()

        assert progress._progress is None
        assert progress._live is None
        assert progress._task_id is None

    def test_on_llm_progress_safe_without_start(self) -> None:
        """Test that on_llm_progress is safe without on_llm_start."""
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=80)
        progress = ProgressDisplay(console)

        # Should not raise
        progress.on_llm_progress(100)

    def test_on_llm_complete_safe_without_start(self) -> None:
        """Test that on_llm_complete is safe without on_llm_start."""
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=80)
        progress = ProgressDisplay(console)

        # Should not raise
        progress.on_llm_complete()


class TestPhaseComplete:
    """Tests for phase completion display."""

    def test_on_phase_complete_shows_metrics(self) -> None:
        """Test that phase completion shows duration and artifacts."""
        from datetime import datetime

        from adw.models import PhaseResult, PhaseStatus

        output = StringIO()
        console = Console(file=output, force_terminal=True, width=80)
        progress = ProgressDisplay(console)

        result = PhaseResult(
            phase="plan",
            status=PhaseStatus.COMPLETED,
            started_at=datetime.now(UTC),
            completed_at=datetime.now(UTC),
            artifacts=["plan.md"],
            tokens_used=500,
        )

        progress.on_phase_complete("plan", result)

        output_text = output.getvalue()
        assert "✓" in output_text
        assert "PLAN" in output_text
        assert "500" in output_text  # tokens

    def test_on_phase_complete_shows_checkmark(self) -> None:
        """Test that phase completion shows green checkmark."""
        from datetime import datetime

        from adw.models import PhaseResult, PhaseStatus

        output = StringIO()
        console = Console(file=output, force_terminal=True, width=80)
        progress = ProgressDisplay(console)

        result = PhaseResult(
            phase="build",
            status=PhaseStatus.COMPLETED,
            started_at=datetime.now(UTC),
            completed_at=datetime.now(UTC),
            artifacts=[],
            tokens_used=100,
        )

        progress.on_phase_complete("build", result)

        output_text = output.getvalue()
        assert "✓" in output_text
        assert "BUILD" in output_text

    def test_on_phase_complete_shows_artifact_count(self) -> None:
        """Test that phase completion shows artifact count."""
        from datetime import datetime

        from adw.models import PhaseResult, PhaseStatus

        output = StringIO()
        console = Console(file=output, force_terminal=True, width=80)
        progress = ProgressDisplay(console)

        result = PhaseResult(
            phase="verify",
            status=PhaseStatus.COMPLETED,
            started_at=datetime.now(UTC),
            completed_at=datetime.now(UTC),
            artifacts=["a.md", "b.md", "c.md"],
            tokens_used=250,
        )

        progress.on_phase_complete("verify", result)

        output_text = output.getvalue()
        # Rich adds escape codes; check that '3' and 'artifacts' are present
        assert "3" in output_text
        assert "artifacts" in output_text

    def test_on_phase_complete_shows_duration(self) -> None:
        """Test that phase completion shows duration."""
        from datetime import datetime

        from adw.models import PhaseResult, PhaseStatus

        output = StringIO()
        console = Console(file=output, force_terminal=True, width=80)
        progress = ProgressDisplay(console)

        # Create a result with known duration (duration_ms property calculates it)
        start = datetime.now(UTC)
        result = PhaseResult(
            phase="validate",
            status=PhaseStatus.COMPLETED,
            started_at=start,
            completed_at=start,  # Same time = 0 duration
            artifacts=[],
            tokens_used=0,
        )

        progress.on_phase_complete("validate", result)

        output_text = output.getvalue()
        # Duration should be formatted (e.g., "0.0s")
        assert "VALIDATE" in output_text


class TestPipelineSummary:
    """Tests for pipeline summary display."""

    def test_show_pipeline_summary_with_completed_phases(self) -> None:
        """Test that pipeline summary shows completed phases with checkmarks."""
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=80)
        progress = ProgressDisplay(console)

        progress.show_pipeline_summary(
            completed_phases=["plan", "build"],
            status="running",
            total_duration_ms=5000,
            total_tokens=1000,
        )

        output_text = output.getvalue()
        assert "✓" in output_text  # Checkmarks for completed
        assert "plan" in output_text
        assert "build" in output_text

    def test_show_pipeline_summary_shows_status(self) -> None:
        """Test that pipeline summary shows final status."""
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=80)
        progress = ProgressDisplay(console)

        progress.show_pipeline_summary(
            completed_phases=["plan", "build", "verify", "validate", "document"],
            status="completed",
            total_duration_ms=10000,
            total_tokens=5000,
        )

        output_text = output.getvalue()
        assert "completed" in output_text

    def test_show_pipeline_summary_shows_duration(self) -> None:
        """Test that pipeline summary shows total duration."""
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=80)
        progress = ProgressDisplay(console)

        progress.show_pipeline_summary(
            completed_phases=["plan"],
            status="completed",
            total_duration_ms=10500,  # 10.5 seconds
            total_tokens=500,
        )

        output_text = output.getvalue()
        assert "10.5s" in output_text

    def test_show_pipeline_summary_shows_token_count(self) -> None:
        """Test that pipeline summary shows total tokens."""
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=80)
        progress = ProgressDisplay(console)

        progress.show_pipeline_summary(
            completed_phases=["plan"],
            status="completed",
            total_duration_ms=1000,
            total_tokens=12345,
        )

        output_text = output.getvalue()
        assert "12,345" in output_text  # Formatted with commas

    def test_show_pipeline_summary_shows_pending_phases(self) -> None:
        """Test that pipeline summary shows pending phases with dots."""
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=80)
        progress = ProgressDisplay(console)

        progress.show_pipeline_summary(
            completed_phases=["plan"],
            status="failed",
            total_duration_ms=2000,
            total_tokens=100,
        )

        output_text = output.getvalue()
        # Should have pending indicator for uncompleted phases
        assert "verify" in output_text
        assert "validate" in output_text
        assert "document" in output_text

    def test_show_pipeline_summary_failed_status(self) -> None:
        """Test that pipeline summary with failed status uses red color."""
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=80)
        progress = ProgressDisplay(console)

        progress.show_pipeline_summary(
            completed_phases=["plan", "build"],
            status="failed",
            total_duration_ms=3000,
            total_tokens=800,
        )

        output_text = output.getvalue()
        assert "failed" in output_text


class TestProgressBar:
    """Tests for live progress bar display."""

    def test_show_progress_bar_shows_percentage(self) -> None:
        """Test that progress bar shows percentage complete."""
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=80)
        progress = ProgressDisplay(console)

        progress._show_progress_bar(current_phase="plan")

        output_text = output.getvalue()
        # Rich adds escape codes, so check for both "0" and "%" separately
        assert "0" in output_text and "%" in output_text  # No phases completed yet

    def test_show_progress_bar_after_completion(self) -> None:
        """Test that progress bar shows updated percentage after phase completes."""
        from datetime import datetime

        from adw.models import PhaseResult, PhaseStatus

        output = StringIO()
        console = Console(file=output, force_terminal=True, width=80)
        progress = ProgressDisplay(console)

        result = PhaseResult(
            phase="plan",
            status=PhaseStatus.COMPLETED,
            started_at=datetime.now(UTC),
            completed_at=datetime.now(UTC),
            artifacts=[],
            tokens_used=100,
        )

        progress.on_phase_complete("plan", result)

        output_text = output.getvalue()
        # Rich adds escape codes around percentage
        assert "20" in output_text and "%" in output_text  # 1 of 5 phases = 20%

    def test_show_progress_bar_shows_current_phase_indicator(self) -> None:
        """Test that progress bar shows ► for current phase."""
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=80)
        progress = ProgressDisplay(console)

        progress._show_progress_bar(current_phase="build")

        output_text = output.getvalue()
        assert "►" in output_text

    def test_show_progress_bar_shows_completed_checkmarks(self) -> None:
        """Test that progress bar shows ✓ for completed phases."""
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=80)
        progress = ProgressDisplay(console)

        progress._completed_phases = ["plan"]
        progress._show_progress_bar(current_phase="build")

        output_text = output.getvalue()
        assert "✓" in output_text

    def test_completed_phases_tracked(self) -> None:
        """Test that completed phases are tracked correctly."""
        from datetime import datetime

        from adw.models import PhaseResult, PhaseStatus

        output = StringIO()
        console = Console(file=output, force_terminal=True, width=80)
        progress = ProgressDisplay(console)

        result = PhaseResult(
            phase="plan",
            status=PhaseStatus.COMPLETED,
            started_at=datetime.now(UTC),
            completed_at=datetime.now(UTC),
            artifacts=[],
            tokens_used=100,
        )

        progress.on_phase_complete("plan", result)

        assert "plan" in progress._completed_phases
        assert progress._total_tokens == 100


class TestErrorDisplay:
    """Tests for error display."""

    def test_on_phase_error_shows_error_message(self) -> None:
        """Test that error display includes error message."""
        from adw.exceptions import HookError

        output = StringIO()
        console = Console(file=output, force_terminal=True, width=80)
        progress = ProgressDisplay(console)

        error = HookError(
            code="HOOK_FAILED",
            message="Pre-hook exited with code 1",
            suggestion="Check hook script for errors",
            recoverable=False,
            phase="build",
        )

        progress.on_phase_error("build", error)

        output_text = output.getvalue()
        assert "Pre-hook exited with code 1" in output_text

    def test_on_phase_error_shows_suggestion(self) -> None:
        """Test that error display includes suggestion."""
        from adw.exceptions import LLMError

        output = StringIO()
        console = Console(file=output, force_terminal=True, width=80)
        progress = ProgressDisplay(console)

        error = LLMError(
            code="LLM_TIMEOUT",
            message="Request timed out",
            suggestion="Increase timeout or try again",
            recoverable=True,
        )

        progress.on_phase_error("plan", error)

        output_text = output.getvalue()
        assert "Increase timeout or try again" in output_text

    def test_on_phase_error_shows_phase_name(self) -> None:
        """Test that error display includes phase name."""
        from adw.exceptions import CommandError

        output = StringIO()
        console = Console(file=output, force_terminal=True, width=80)
        progress = ProgressDisplay(console)

        error = CommandError(
            code="COMMAND_NOT_FOUND",
            message="Command not found",
            suggestion="Check command configuration",
            recoverable=False,
        )

        progress.on_phase_error("verify", error)

        output_text = output.getvalue()
        assert "VERIFY" in output_text

    def test_on_phase_error_stops_live_display(self) -> None:
        """Test that error display stops any active live display."""
        from adw.exceptions import LLMError

        output = StringIO()
        console = Console(file=output, force_terminal=True, width=80)
        progress = ProgressDisplay(console)

        # Start LLM progress
        progress.on_llm_start()
        assert progress._live is not None

        error = LLMError(
            code="LLM_ERROR",
            message="Execution failed",
            suggestion="Try again",
            recoverable=True,
        )

        progress.on_phase_error("plan", error)

        # Live display should be stopped
        assert progress._live is None
        assert progress._progress is None
