"""Unit tests for RunDisplay class.

Tests for the run header display functionality (UX-12).
"""

from datetime import UTC, datetime

from rich.console import Console

from adw.cli.run_display import RunDisplay


class TestRunDisplay:
    """Tests for RunDisplay class."""

    def test_init_with_console(self) -> None:
        """Test RunDisplay initialization with custom console."""
        console = Console()
        display = RunDisplay(console)
        assert display.console is console

    def test_init_without_console(self) -> None:
        """Test RunDisplay initialization without console creates one."""
        display = RunDisplay()
        assert display.console is not None
        assert isinstance(display.console, Console)

    def test_show_run_header_displays_run_id(self) -> None:
        """Test that show_run_header displays run ID."""
        console = Console(force_terminal=True, width=80)
        display = RunDisplay(console)

        # Capture output
        with console.capture() as capture:
            display.show_run_header(
                run_id="01HQXK5P3Z7V8R2M4N6T9W1Y3C",
                feature="Add user authentication",
                started_at=datetime(2026, 1, 3, 10, 30, 45, tzinfo=UTC),
            )

        output = capture.get()
        assert "01HQXK5P3Z7V8R2M4N6T9W1Y3C" in output
        assert "Run ID" in output

    def test_show_run_header_displays_feature(self) -> None:
        """Test that show_run_header displays feature description."""
        console = Console(force_terminal=True, width=80)
        display = RunDisplay(console)

        with console.capture() as capture:
            display.show_run_header(
                run_id="01HQXK5P3Z7V8R2M4N6T9W1Y3C",
                feature="Add user authentication",
                started_at=datetime(2026, 1, 3, 10, 30, 45, tzinfo=UTC),
            )

        output = capture.get()
        assert "Add user authentication" in output
        assert "Feature" in output

    def test_show_run_header_displays_timestamp(self) -> None:
        """Test that show_run_header displays timestamp."""
        console = Console(force_terminal=True, width=80)
        display = RunDisplay(console)

        with console.capture() as capture:
            display.show_run_header(
                run_id="01HQXK5P3Z7V8R2M4N6T9W1Y3C",
                feature="Add feature",
                started_at=datetime(2026, 1, 3, 10, 30, 45, tzinfo=UTC),
            )

        output = capture.get()
        assert "2026-01-03" in output
        assert "10:30:45" in output

    def test_show_run_header_truncates_long_feature(self) -> None:
        """Test that long feature descriptions are truncated."""
        console = Console(force_terminal=True, width=80)
        display = RunDisplay(console)

        long_feature = "A" * 100  # 100 characters

        with console.capture() as capture:
            display.show_run_header(
                run_id="01HQXK5P3Z7V8R2M4N6T9W1Y3C",
                feature=long_feature,
                started_at=datetime(2026, 1, 3, 10, 30, 45, tzinfo=UTC),
            )

        output = capture.get()
        # Should contain truncated version with "..."
        assert "..." in output
        # Should not contain the full 100 A's
        assert long_feature not in output

    def test_show_run_header_keeps_short_feature_intact(self) -> None:
        """Test that short feature descriptions are not truncated."""
        console = Console(force_terminal=True, width=80)
        display = RunDisplay(console)

        short_feature = "Add login"

        with console.capture() as capture:
            display.show_run_header(
                run_id="01HQXK5P3Z7V8R2M4N6T9W1Y3C",
                feature=short_feature,
                started_at=datetime(2026, 1, 3, 10, 30, 45, tzinfo=UTC),
            )

        output = capture.get()
        assert short_feature in output

    def test_show_run_header_uses_panel(self) -> None:
        """Test that show_run_header uses Rich Panel for formatting (UX-12)."""
        console = Console(force_terminal=True, width=80)
        display = RunDisplay(console)

        with console.capture() as capture:
            display.show_run_header(
                run_id="01HQXK5P3Z7V8R2M4N6T9W1Y3C",
                feature="Add feature",
                started_at=datetime(2026, 1, 3, 10, 30, 45, tzinfo=UTC),
            )

        output = capture.get()
        # Panel should have "ADW Run" title
        assert "ADW Run" in output
        # Panel borders are typically represented by box drawing characters
        assert "─" in output or "╭" in output or "│" in output
