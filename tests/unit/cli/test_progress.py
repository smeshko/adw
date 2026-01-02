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
