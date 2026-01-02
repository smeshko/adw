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
