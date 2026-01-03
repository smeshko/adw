"""Tests for StatusDisplay class.

Tests for the StatusDisplay class that shows run status using Rich.
"""

from datetime import UTC, datetime
from io import StringIO

import pytest
from rich.console import Console

from adw.cli.status_display import StatusDisplay, output_json
from adw.models import RunContext


@pytest.fixture
def sample_context() -> RunContext:
    """Create a sample RunContext for testing."""
    return RunContext(
        run_id="01HQXK5P3Z7V8R2M4N6T9W1Y3C",
        feature_description="Add user authentication",
        current_phase="build",
        phase_history=["plan"],
        started_at=datetime(2026, 1, 3, 10, 30, 45, tzinfo=UTC),
        status="running",
    )


@pytest.fixture
def completed_context() -> RunContext:
    """Create a completed RunContext for testing."""
    return RunContext(
        run_id="01HQXK5P3Z7V8R2M4N6T9W1Y3C",
        feature_description="Add user authentication",
        current_phase="document",
        phase_history=["plan", "build", "verify", "validate", "document"],
        started_at=datetime(2026, 1, 3, 10, 30, 45, tzinfo=UTC),
        completed_at=datetime(2026, 1, 3, 10, 35, 12, tzinfo=UTC),
        status="completed",
        phase_tokens={"plan": 500, "build": 1200, "verify": 300},
        artifacts={"plan": ["plan.md"], "build": ["code.py"]},
    )


@pytest.fixture
def failed_context() -> RunContext:
    """Create a failed RunContext for testing."""
    return RunContext(
        run_id="01HQXK5P3Z7V8R2M4N6T9W1Y3C",
        feature_description="Add user authentication",
        current_phase="build",
        phase_history=["plan"],
        started_at=datetime(2026, 1, 3, 10, 30, 45, tzinfo=UTC),
        status="failed",
    )


class TestStatusDisplay:
    """Tests for StatusDisplay class."""

    def test_show_status_displays_run_id(self, sample_context: RunContext) -> None:
        """Test that status displays run ID."""
        output = StringIO()
        console = Console(file=output, force_terminal=True)
        display = StatusDisplay(console)

        display.show_status(sample_context)

        result = output.getvalue()
        assert sample_context.run_id in result

    def test_show_status_displays_feature(self, sample_context: RunContext) -> None:
        """Test that status displays feature description."""
        output = StringIO()
        console = Console(file=output, force_terminal=True)
        display = StatusDisplay(console)

        display.show_status(sample_context)

        result = output.getvalue()
        assert "Add user authentication" in result

    def test_show_status_displays_status_with_color(
        self, sample_context: RunContext
    ) -> None:
        """Test that status displays status value."""
        output = StringIO()
        console = Console(file=output, force_terminal=True)
        display = StatusDisplay(console)

        display.show_status(sample_context)

        result = output.getvalue()
        assert "running" in result

    def test_show_status_displays_phase(self, sample_context: RunContext) -> None:
        """Test that status displays current phase."""
        output = StringIO()
        console = Console(file=output, force_terminal=True)
        display = StatusDisplay(console)

        display.show_status(sample_context)

        result = output.getvalue()
        assert "build" in result

    def test_show_status_truncates_long_feature(self) -> None:
        """Test that long feature descriptions are truncated."""
        context = RunContext(
            run_id="01HQXK5P3Z7V8R2M4N6T9W1Y3C",
            feature_description="A" * 100,
            current_phase="plan",
            started_at=datetime.now(UTC),
        )
        output = StringIO()
        console = Console(file=output, force_terminal=True)
        display = StatusDisplay(console)

        display.show_status(context)

        result = output.getvalue()
        # Full feature shouldn't appear, should be truncated
        assert "A" * 100 not in result
        assert "..." in result

    def test_show_status_color_for_completed(
        self, completed_context: RunContext
    ) -> None:
        """Test completed status uses green color."""
        output = StringIO()
        console = Console(file=output, force_terminal=True)
        display = StatusDisplay(console)

        display.show_status(completed_context)

        result = output.getvalue()
        assert "completed" in result

    def test_show_status_color_for_failed(self, failed_context: RunContext) -> None:
        """Test failed status uses red color."""
        output = StringIO()
        console = Console(file=output, force_terminal=True)
        display = StatusDisplay(console)

        display.show_status(failed_context)

        result = output.getvalue()
        assert "failed" in result


class TestStatusDisplayVerbose:
    """Tests for verbose mode in StatusDisplay."""

    def test_verbose_shows_phases(self, completed_context: RunContext) -> None:
        """Test verbose mode shows phase progress."""
        output = StringIO()
        console = Console(file=output, force_terminal=True)
        display = StatusDisplay(console)

        display.show_status(completed_context, verbose=True)

        result = output.getvalue()
        # Should show phase info
        assert "plan" in result

    def test_verbose_shows_tokens(self, completed_context: RunContext) -> None:
        """Test verbose mode shows token count."""
        output = StringIO()
        console = Console(file=output, force_terminal=True)
        display = StatusDisplay(console)

        display.show_status(completed_context, verbose=True)

        result = output.getvalue()
        # Should contain token info (total is 2000)
        assert "2,000" in result or "Tokens" in result

    def test_verbose_shows_artifacts(self, completed_context: RunContext) -> None:
        """Test verbose mode shows artifact count."""
        output = StringIO()
        console = Console(file=output, force_terminal=True)
        display = StatusDisplay(console)

        display.show_status(completed_context, verbose=True)

        result = output.getvalue()
        assert "Artifacts" in result


class TestFailedRunDetails:
    """Tests for failed run details (UX-3)."""

    def test_failed_shows_recovery_panel(self, failed_context: RunContext) -> None:
        """Test that failed status shows recovery panel."""
        output = StringIO()
        console = Console(file=output, force_terminal=True)
        display = StatusDisplay(console)

        display.show_status(failed_context)

        result = output.getvalue()
        assert "Recovery" in result or "resume" in result

    def test_failed_shows_resume_command(self, failed_context: RunContext) -> None:
        """Test that failed status shows resume command (UX-3)."""
        output = StringIO()
        console = Console(file=output, force_terminal=True)
        display = StatusDisplay(console)

        display.show_status(failed_context)

        result = output.getvalue()
        assert "adw resume" in result
        assert failed_context.run_id in result

    def test_failed_shows_failed_phase(self, failed_context: RunContext) -> None:
        """Test that failed status shows which phase failed."""
        output = StringIO()
        console = Console(file=output, force_terminal=True)
        display = StatusDisplay(console)

        display.show_status(failed_context)

        result = output.getvalue()
        assert "build" in result  # The failed phase


class TestDurationFormatting:
    """Tests for duration formatting."""

    def test_format_duration_seconds(self) -> None:
        """Test duration formatting for less than a minute."""
        context = RunContext(
            run_id="01HQXK5P3Z7V8R2M4N6T9W1Y3C",
            feature_description="Test",
            current_phase="plan",
            started_at=datetime(2026, 1, 3, 10, 30, 0, tzinfo=UTC),
            completed_at=datetime(2026, 1, 3, 10, 30, 45, tzinfo=UTC),
            status="completed",
        )
        output = StringIO()
        console = Console(file=output, force_terminal=True)
        display = StatusDisplay(console)

        display.show_status(context)

        result = output.getvalue()
        assert "45s" in result

    def test_format_duration_minutes(self) -> None:
        """Test duration formatting for minutes."""
        context = RunContext(
            run_id="01HQXK5P3Z7V8R2M4N6T9W1Y3C",
            feature_description="Test",
            current_phase="plan",
            started_at=datetime(2026, 1, 3, 10, 30, 0, tzinfo=UTC),
            completed_at=datetime(2026, 1, 3, 10, 34, 27, tzinfo=UTC),
            status="completed",
        )
        output = StringIO()
        console = Console(file=output, force_terminal=True)
        display = StatusDisplay(console)

        display.show_status(context)

        result = output.getvalue()
        assert "4m 27s" in result


class TestJsonOutput:
    """Tests for JSON output."""

    def test_json_contains_run_id(self, completed_context: RunContext) -> None:
        """Test JSON output contains run_id."""
        output = StringIO()
        console = Console(file=output, force_terminal=True)

        output_json(completed_context, console)

        result = output.getvalue()
        assert completed_context.run_id in result

    def test_json_contains_status(self, completed_context: RunContext) -> None:
        """Test JSON output contains status."""
        output = StringIO()
        console = Console(file=output, force_terminal=True)

        output_json(completed_context, console)

        result = output.getvalue()
        assert "completed" in result

    def test_json_contains_duration_ms(self, completed_context: RunContext) -> None:
        """Test JSON output contains duration_ms."""
        output = StringIO()
        console = Console(file=output, force_terminal=True)

        output_json(completed_context, console)

        result = output.getvalue()
        assert "duration_ms" in result

    def test_json_contains_artifact_count(self, completed_context: RunContext) -> None:
        """Test JSON output contains artifact_count."""
        output = StringIO()
        console = Console(file=output, force_terminal=True)

        output_json(completed_context, console)

        result = output.getvalue()
        assert "artifact_count" in result
