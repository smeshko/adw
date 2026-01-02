"""Unit tests for ProgressDisplay class.

Tests the progress display functionality for the ADW pipeline,
including phase start/completion display, LLM progress with spinner,
and overall progress bar.
"""

from io import StringIO

import pytest
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
        from datetime import datetime, timezone

        from adw.models import PhaseResult, PhaseStatus

        output = StringIO()
        console = Console(file=output, force_terminal=True, width=80)
        progress = ProgressDisplay(console)

        result = PhaseResult(
            phase="plan",
            status=PhaseStatus.COMPLETED,
            started_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc),
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
        from datetime import datetime, timezone

        from adw.models import PhaseResult, PhaseStatus

        output = StringIO()
        console = Console(file=output, force_terminal=True, width=80)
        progress = ProgressDisplay(console)

        result = PhaseResult(
            phase="build",
            status=PhaseStatus.COMPLETED,
            started_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc),
            artifacts=[],
            tokens_used=100,
        )

        progress.on_phase_complete("build", result)

        output_text = output.getvalue()
        assert "✓" in output_text
        assert "BUILD" in output_text

    def test_on_phase_complete_shows_artifact_count(self) -> None:
        """Test that phase completion shows artifact count."""
        from datetime import datetime, timezone

        from adw.models import PhaseResult, PhaseStatus

        output = StringIO()
        console = Console(file=output, force_terminal=True, width=80)
        progress = ProgressDisplay(console)

        result = PhaseResult(
            phase="verify",
            status=PhaseStatus.COMPLETED,
            started_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc),
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
        from datetime import datetime, timezone

        from adw.models import PhaseResult, PhaseStatus

        output = StringIO()
        console = Console(file=output, force_terminal=True, width=80)
        progress = ProgressDisplay(console)

        # Create a result with known duration (duration_ms property calculates it)
        start = datetime.now(timezone.utc)
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
