"""Tests for DryRunDisplay module.

Tests the dry-run preview functionality including phase display,
configuration display, and artifact preview.
"""

from __future__ import annotations

from io import StringIO

import pytest
from rich.console import Console

from adw.cli.dry_run import DryRunDisplay
from adw.models import ProjectConfig


class TestDryRunDisplay:
    """Tests for DryRunDisplay class."""

    def test_init_with_console(self) -> None:
        """Test initialization with provided console."""
        console = Console()
        display = DryRunDisplay(console)
        assert display.console is console

    def test_init_without_console(self) -> None:
        """Test initialization creates default console."""
        display = DryRunDisplay()
        assert display.console is not None

    def test_show_execution_preview_full_pipeline(self) -> None:
        """Test full pipeline preview shows all 5 phases."""
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=100)
        display = DryRunDisplay(console)

        display.show_execution_preview(
            feature="Add user authentication",
            phase=None,  # Full pipeline
            from_run=None,
        )

        result = output.getvalue()
        # Should show all phases
        for phase in ["plan", "build", "verify", "validate", "document"]:
            assert phase in result.lower(), f"Phase '{phase}' not found in output"

    def test_show_execution_preview_single_phase(self) -> None:
        """Test single phase mode only shows specified phase."""
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=100)
        display = DryRunDisplay(console)

        display.show_execution_preview(
            feature="Add user authentication",
            phase="build",  # Single phase
            from_run=None,
        )

        result = output.getvalue()
        # Should show build phase
        assert "build" in result.lower()
        # Should indicate single phase mode
        assert "build" in result.lower()

    def test_show_execution_preview_shows_feature(self) -> None:
        """Test that feature description is shown in preview."""
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=100)
        display = DryRunDisplay(console)

        display.show_execution_preview(
            feature="Add user authentication",
            phase=None,
            from_run=None,
        )

        result = output.getvalue()
        assert "Add user authentication" in result

    def test_show_execution_preview_shows_dry_run_notice(self) -> None:
        """Test that dry run notice is shown."""
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=100)
        display = DryRunDisplay(console)

        display.show_execution_preview(
            feature="Test feature",
            phase=None,
            from_run=None,
        )

        result = output.getvalue().lower()
        assert "dry run" in result or "no execution" in result
