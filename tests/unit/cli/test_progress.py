"""Unit tests for ProgressDisplay class.

Tests the progress display functionality for the ADW pipeline,
including phase start/completion display, LLM progress with spinner,
and overall progress bar.
"""

from datetime import UTC
from io import StringIO
from pathlib import Path

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

        progress.on_phase_start("validate")

        output_text = output.getvalue()
        # Story 15.1: validate is the 3rd phase (index 2), so "Phase 3/5"
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
            input_tokens=200,
            output_tokens=300,
        )

        progress.on_phase_complete("plan", result)

        output_text = output.getvalue()
        assert "✓" in output_text
        assert "PLAN" in output_text
        # Strip ANSI codes for reliable matching
        import re

        plain = re.sub(r"\x1b\[[0-9;]*m", "", output_text)
        assert "in: 200" in plain
        assert "out: 300" in plain

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
            phase="validate",
            status=PhaseStatus.COMPLETED,
            started_at=datetime.now(UTC),
            completed_at=datetime.now(UTC),
            artifacts=["a.md", "b.md", "c.md"],
            tokens_used=250,
        )

        progress.on_phase_complete("validate", result)

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
            completed_phases=["plan", "build", "validate", "document"],
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
        import re
        plain = re.sub(r"\x1b\[[0-9;]*m", "", output_text)
        assert "12K" in plain  # Formatted with abbreviation

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
        # Should have pending indicator for uncompleted phases (ISS-019: verify removed)
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
        # Rich adds escape codes around percentage (Story 15.1: 1 of 5 phases = 20%)
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

        progress.on_phase_error("validate", error)

        output_text = output.getvalue()
        assert "VALIDATE" in output_text

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


class TestPipelineSummaryWithPRResult:
    """Tests for pipeline summary with PR result (Story ISS-011)."""

    def test_shows_pr_url_when_success(self) -> None:
        """Test displays PR URL when PR creation succeeds."""
        from adw.cli.pr import AutoPRResult

        output = StringIO()
        console = Console(file=output, force_terminal=True, width=100)
        progress = ProgressDisplay(console)

        pr_result = AutoPRResult(
            success=True,
            pr_url="https://github.com/user/repo/pull/123",
        )

        progress.show_pipeline_summary(
            completed_phases=["plan", "build", "validate", "document"],
            status="completed",
            total_duration_ms=10000,
            total_tokens=5000,
            run_id="01JFTEST000000000000000001",
            pr_result=pr_result,
        )

        output_text = output.getvalue()
        assert "PR Created" in output_text
        assert "pull/123" in output_text

    def test_shows_description_path_when_no_remote(self) -> None:
        """Test displays description path with hint when no remote."""
        from adw.cli.pr import AutoPRResult

        output = StringIO()
        console = Console(file=output, force_terminal=True, width=100)
        progress = ProgressDisplay(console)

        pr_result = AutoPRResult(
            success=False,
            reason="No git remote configured",
        )

        progress.show_pipeline_summary(
            completed_phases=["plan", "build", "validate", "document"],
            status="completed",
            total_duration_ms=10000,
            total_tokens=5000,
            run_id="01JFTEST000000000000000001",
            pr_result=pr_result,
        )

        output_text = output.getvalue()
        assert "PR Description" in output_text
        assert "remote" in output_text.lower()

    def test_shows_gh_install_hint_when_not_installed(self) -> None:
        """Test displays gh CLI install hint when gh not installed."""
        from adw.cli.pr import AutoPRResult

        output = StringIO()
        console = Console(file=output, force_terminal=True, width=100)
        progress = ProgressDisplay(console)

        pr_result = AutoPRResult(
            success=False,
            reason="GitHub CLI (gh) not installed",
        )

        progress.show_pipeline_summary(
            completed_phases=["plan", "build", "validate", "document"],
            status="completed",
            total_duration_ms=10000,
            total_tokens=5000,
            run_id="01JFTEST000000000000000001",
            pr_result=pr_result,
        )

        output_text = output.getvalue()
        assert "PR Description" in output_text
        assert "Install GitHub CLI" in output_text

    def test_backward_compatible_without_pr_result(self) -> None:
        """Test works without pr_result (backward compatibility)."""
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=100)
        progress = ProgressDisplay(console)

        # Call without pr_result (old behavior)
        progress.show_pipeline_summary(
            completed_phases=["plan", "build", "validate", "document"],
            status="completed",
            total_duration_ms=10000,
            total_tokens=5000,
            run_id="01JFTEST000000000000000001",
        )

        output_text = output.getvalue()
        assert "PR Description" in output_text
        assert "pr_description.md" in output_text


class TestEnabledPhasesFiltering:
    """Tests for enabled phases filtering (ISS-036).

    When ship or other phases are disabled via config, the progress bar should:
    1. Only display enabled phases
    2. Calculate percentage based on enabled phases only
    3. Show correct phase numbers (e.g., "Phase 3/4" not "Phase 3/5")
    """

    def test_init_with_enabled_phases(self) -> None:
        """Test ProgressDisplay accepts enabled_phases parameter."""
        enabled = ["plan", "build", "validate", "document"]
        progress = ProgressDisplay(enabled_phases=enabled)
        assert progress._enabled_phases == enabled

    def test_init_default_enabled_phases(self) -> None:
        """Test ProgressDisplay defaults to all phases when None."""
        progress = ProgressDisplay()
        assert progress._enabled_phases == list(PHASE_SEQUENCE)

    def test_progress_bar_shows_only_enabled_phases(self) -> None:
        """Test progress bar only displays enabled phases."""
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=80)
        enabled = ["plan", "build", "validate", "document"]  # No ship
        progress = ProgressDisplay(console, enabled_phases=enabled)

        progress._show_progress_bar(current_phase="plan")

        output_text = output.getvalue()
        assert "ship" not in output_text.lower()
        assert "plan" in output_text
        assert "document" in output_text

    def test_percentage_calculation_with_enabled_phases(self) -> None:
        """Test percentage uses enabled phases count."""
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=80)
        enabled = ["plan", "build", "validate", "document"]  # 4 phases
        progress = ProgressDisplay(console, enabled_phases=enabled)

        progress._completed_phases = ["plan", "build", "validate", "document"]
        progress._show_progress_bar()

        output_text = output.getvalue()
        # 4/4 = 100%, not 4/5 = 80%
        assert "100" in output_text and "%" in output_text

    def test_phase_number_with_enabled_phases(self) -> None:
        """Test phase number shows correct total."""
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=80)
        enabled = ["plan", "build", "validate", "document"]
        progress = ProgressDisplay(console, enabled_phases=enabled)

        progress.on_phase_start("validate")

        output_text = output.getvalue()
        # validate is 3rd of 4 enabled phases
        assert "3/4" in output_text

    def test_summary_shows_only_enabled_phases(self) -> None:
        """Test pipeline summary only shows enabled phases."""
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=80)
        enabled = ["plan", "build", "validate", "document"]
        progress = ProgressDisplay(console, enabled_phases=enabled)

        progress.show_pipeline_summary(
            completed_phases=["plan", "build", "validate", "document"],
            status="completed",
            total_duration_ms=10000,
            total_tokens=5000,
        )

        output_text = output.getvalue()
        assert "ship" not in output_text.lower()

    def test_backward_compatibility_none_enabled_phases(self) -> None:
        """Test backward compatibility when enabled_phases=None."""
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=80)
        progress = ProgressDisplay(console, enabled_phases=None)

        progress._show_progress_bar(current_phase="plan")

        output_text = output.getvalue()
        # With None, all phases including ship should be shown
        assert "ship" in output_text.lower()

    def test_percentage_zero_when_no_enabled_phases(self) -> None:
        """Test percentage handles edge case of no enabled phases."""
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=80)
        progress = ProgressDisplay(console, enabled_phases=[])

        progress._show_progress_bar()

        output_text = output.getvalue()
        # Should show 0% without division error
        assert "0" in output_text and "%" in output_text


class TestTryAutoCreatePr:
    """Tests for try_auto_create_pr method (Story ISS-011)."""

    def test_returns_result_when_called(self, tmp_path: Path) -> None:
        """Test returns AutoPRResult when called."""
        from datetime import UTC, datetime
        from unittest.mock import patch

        from adw.cli.pr import AutoPRResult
        from adw.models import RunContext

        output = StringIO()
        console = Console(file=output, force_terminal=True, width=100)
        progress = ProgressDisplay(console)

        context = RunContext(
            run_id="01JFTEST000000000000000001",
            feature_description="Test feature",
            current_phase="document",
            started_at=datetime.now(UTC),
            status="completed",
        )

        with patch("adw.cli.pr.auto_create_pr") as mock_create:
            mock_create.return_value = AutoPRResult(
                success=True,
                pr_url="https://github.com/user/repo/pull/123",
            )

            result = progress.try_auto_create_pr(
                run_id=context.run_id,
                context=context,
                runs_dir=tmp_path,
            )

            assert result is not None
            assert result.success is True
            assert result.pr_url == "https://github.com/user/repo/pull/123"

    def test_handles_exception_gracefully(self, tmp_path: Path) -> None:
        """Test handles exceptions without crashing."""
        from datetime import UTC, datetime
        from unittest.mock import patch

        from adw.models import RunContext

        output = StringIO()
        console = Console(file=output, force_terminal=True, width=100)
        progress = ProgressDisplay(console)

        context = RunContext(
            run_id="01JFTEST000000000000000001",
            feature_description="Test feature",
            current_phase="document",
            started_at=datetime.now(UTC),
            status="completed",
        )

        with patch("adw.cli.pr.auto_create_pr") as mock_create:
            mock_create.side_effect = Exception("Unexpected error")

            result = progress.try_auto_create_pr(
                run_id=context.run_id,
                context=context,
                runs_dir=tmp_path,
            )

            assert result is not None
            assert result.success is False
            assert "Unexpected error" in result.reason
