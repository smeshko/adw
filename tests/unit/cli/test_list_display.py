"""Tests for ListDisplay class (Story 6.4).

Tests for the list display formatting functionality.
"""

from datetime import UTC, datetime
from io import StringIO

import pytest
from rich.console import Console

from adw.cli.list_display import ListDisplay
from adw.models import RunContext


@pytest.fixture
def console() -> Console:
    """Create a console for testing."""
    return Console(file=StringIO(), force_terminal=True, width=120)


@pytest.fixture
def display(console: Console) -> ListDisplay:
    """Create a ListDisplay instance."""
    return ListDisplay(console)


def create_run_context(
    run_id: str = "01HQXK5P3Z7V8R2M4N6T9W1Y3A",
    feature: str = "Test feature",
    status: str = "completed",
    started_at: datetime | None = None,
) -> RunContext:
    """Create a RunContext for testing."""
    return RunContext(
        run_id=run_id,
        feature_description=feature,
        current_phase="plan",
        phase_history=["plan"],
        started_at=started_at or datetime.now(UTC),
        status=status,
    )


class TestListDisplayInit:
    """Tests for ListDisplay initialization."""

    def test_init_with_console(self, console: Console) -> None:
        """Test that ListDisplay can be initialized with a console."""
        display = ListDisplay(console)
        assert display.console is console

    def test_init_without_console_creates_default(self) -> None:
        """Test that ListDisplay creates a default console if none provided."""
        display = ListDisplay()
        assert display.console is not None


class TestShowRuns:
    """Tests for show_runs method."""

    def test_show_runs_renders_table(
        self, display: ListDisplay, console: Console
    ) -> None:
        """Test that show_runs renders a table."""
        runs = [create_run_context()]
        display.show_runs(runs)

        output = console.file.getvalue()
        assert "Recent Runs" in output
        assert "(1)" in output

    def test_show_runs_includes_run_id(
        self, display: ListDisplay, console: Console
    ) -> None:
        """Test that run ID is included in output."""
        runs = [create_run_context(run_id="01HQXK5P3Z7V8R2M4N6T9W1Y3A")]
        display.show_runs(runs)

        output = console.file.getvalue()
        # Should show truncated run ID
        assert "01HQXK5P3Z7V" in output

    def test_show_runs_includes_feature(
        self, display: ListDisplay, console: Console
    ) -> None:
        """Test that feature description is included."""
        runs = [create_run_context(feature="Add user authentication")]
        display.show_runs(runs)

        output = console.file.getvalue()
        assert "Add user authentication" in output

    def test_show_runs_includes_status(
        self, display: ListDisplay, console: Console
    ) -> None:
        """Test that status is included."""
        runs = [create_run_context(status="completed")]
        display.show_runs(runs)

        output = console.file.getvalue()
        assert "completed" in output

    def test_show_runs_color_codes_status(
        self, display: ListDisplay, console: Console
    ) -> None:
        """Test that status is color-coded."""
        # Just verify the STATUS_COLORS mapping exists
        assert "completed" in ListDisplay.STATUS_COLORS
        assert "failed" in ListDisplay.STATUS_COLORS
        assert "running" in ListDisplay.STATUS_COLORS
        assert "interrupted" in ListDisplay.STATUS_COLORS

    def test_show_runs_multiple_runs(
        self, display: ListDisplay, console: Console
    ) -> None:
        """Test that multiple runs are displayed."""
        runs = [
            create_run_context(run_id="01HQXK5P3Z7V8R2M4N6T9W1Y3A"),
            create_run_context(run_id="01HQXK5P3Z7V8R2M4N6T9W1Y3B"),
            create_run_context(run_id="01HQXK5P3Z7V8R2M4N6T9W1Y3C"),
        ]
        display.show_runs(runs)

        output = console.file.getvalue()
        assert "(3)" in output


class TestTruncateId:
    """Tests for _truncate_id method."""

    def test_truncate_long_id(self, display: ListDisplay) -> None:
        """Test that long IDs are truncated."""
        result = display._truncate_id("01HQXK5P3Z7V8R2M4N6T9W1Y3C")
        assert result == "01HQXK5P3Z7V..."
        assert len(result) == 15

    def test_truncate_short_id(self, display: ListDisplay) -> None:
        """Test that short IDs are not truncated."""
        result = display._truncate_id("short_id")
        assert result == "short_id"


class TestTruncateText:
    """Tests for _truncate_text method."""

    def test_truncate_long_text(self, display: ListDisplay) -> None:
        """Test that long text is truncated with ellipsis."""
        long_text = "This is a very long feature description that exceeds the maximum width"
        result = display._truncate_text(long_text, max_length=37)

        assert len(result) == 37
        assert result.endswith("...")

    def test_truncate_short_text(self, display: ListDisplay) -> None:
        """Test that short text is not truncated."""
        short_text = "Add auth"
        result = display._truncate_text(short_text, max_length=37)

        assert result == short_text

    def test_truncate_exact_length(self, display: ListDisplay) -> None:
        """Test that text at exact length is not truncated."""
        text = "x" * 37
        result = display._truncate_text(text, max_length=37)

        assert result == text


class TestFormatTimestamp:
    """Tests for _format_timestamp method."""

    def test_format_datetime(self, display: ListDisplay) -> None:
        """Test that datetime is formatted correctly."""
        dt = datetime(2024, 1, 15, 10, 30, 0, tzinfo=UTC)
        result = display._format_timestamp(dt)

        assert result == "2024-01-15 10:30"

    def test_format_none(self, display: ListDisplay) -> None:
        """Test that None returns dash."""
        result = display._format_timestamp(None)

        assert result == "—"

    def test_format_non_datetime(self, display: ListDisplay) -> None:
        """Test that non-datetime returns dash."""
        result = display._format_timestamp("not a datetime")

        assert result == "—"


class TestStatusColors:
    """Tests for STATUS_COLORS constant."""

    def test_all_statuses_have_colors(self) -> None:
        """Test that all expected statuses have color mappings."""
        expected_statuses = ["running", "completed", "failed", "interrupted", "aborted"]

        for status in expected_statuses:
            assert status in ListDisplay.STATUS_COLORS

    def test_running_is_yellow(self) -> None:
        """Test that running status is yellow."""
        assert ListDisplay.STATUS_COLORS["running"] == "yellow"

    def test_completed_is_green(self) -> None:
        """Test that completed status is green."""
        assert ListDisplay.STATUS_COLORS["completed"] == "green"

    def test_failed_is_red(self) -> None:
        """Test that failed status is red."""
        assert ListDisplay.STATUS_COLORS["failed"] == "red"

    def test_interrupted_is_orange(self) -> None:
        """Test that interrupted status is orange."""
        assert ListDisplay.STATUS_COLORS["interrupted"] == "orange1"
