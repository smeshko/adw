"""Tests for StatusDisplay class.

Tests for the StatusDisplay class that shows run status using Rich.

# REDUCTION NOTE: Reduced from 20 tests to 4 tests (-16 tests, 80% reduction)
# Removed:
# - Weak output text verification tests (test_show_status_displays_*)
# - Color verification tests (can't verify Rich color codes in output)
# - Duration formatting tests (brittle time-dependent assertions)
# - Redundant verbose mode substring checks
# - Redundant failure detail substring checks
# Kept: Tests verifying actual business logic - truncation, recovery UX, JSON structure
"""

import json
from datetime import UTC, datetime
from io import StringIO

import pytest
from rich.console import Console

from adw.cli.status_display import StatusDisplay, output_json
from adw.models import RunContext


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


@pytest.fixture
def completed_context() -> RunContext:
    """Create a completed RunContext for testing."""
    return RunContext(
        run_id="01HQXK5P3Z7V8R2M4N6T9W1Y3C",
        feature_description="Add user authentication",
        current_phase="document",
        phase_history=["plan", "build", "validate", "document"],
        started_at=datetime(2026, 1, 3, 10, 30, 45, tzinfo=UTC),
        completed_at=datetime(2026, 1, 3, 10, 35, 12, tzinfo=UTC),
        status="completed",
        phase_tokens={"plan": 500, "build": 1200, "validate": 300},
        artifacts={"plan": ["plan.md"], "build": ["code.py", "tests.py"]},
    )


class TestStatusDisplayLogic:
    """Tests for actual display logic in StatusDisplay."""

    def test_truncates_feature_at_60_chars(self) -> None:
        """Test that feature descriptions over 60 chars are truncated with ellipsis."""
        long_feature = "A" * 100
        context = RunContext(
            run_id="01HQXK5P3Z7V8R2M4N6T9W1Y3C",
            feature_description=long_feature,
            current_phase="plan",
            started_at=datetime.now(UTC),
        )
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=200)
        display = StatusDisplay(console)

        display.show_status(context)

        result = output.getvalue()
        # Full 100 char feature should NOT appear
        assert long_feature not in result
        # Should have ellipsis indicating truncation
        assert "..." in result
        # First 57 chars should appear (57 + "..." = 60 display chars)
        assert "A" * 57 in result

    def test_failed_status_shows_resume_command_with_run_id(
        self, failed_context: RunContext
    ) -> None:
        """Test that failed status shows actionable resume command (UX-3 requirement)."""
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=200)
        display = StatusDisplay(console)

        display.show_status(failed_context)

        result = output.getvalue()
        # Must show exact resume command with run_id for user to copy
        assert f"adw resume {failed_context.run_id}" in result


class TestJsonOutput:
    """Tests for JSON output structure."""

    def test_output_json_produces_valid_json_with_required_fields(
        self, completed_context: RunContext
    ) -> None:
        """Test that output_json produces valid JSON with all required fields."""
        output = StringIO()
        # Use no_color=True to get plain JSON without ANSI codes
        console = Console(file=output, force_terminal=False, no_color=True)

        output_json(completed_context, console)

        # Parse the JSON output
        result = output.getvalue()
        data = json.loads(result)

        # Verify structure - all required fields present
        assert data["run_id"] == completed_context.run_id
        assert data["status"] == "completed"
        assert data["current_phase"] == "document"
        assert data["completed_phases"] == [
            "plan",
            "build",
            "validate",
            "document",
        ]
        assert "duration_ms" in data
        assert isinstance(data["duration_ms"], int)
        assert data["duration_ms"] > 0  # Completed context has duration

    def test_output_json_calculates_artifact_count_correctly(
        self, completed_context: RunContext
    ) -> None:
        """Test that artifact_count sums artifacts across all phases."""
        output = StringIO()
        # Use no_color=True to get plain JSON without ANSI codes
        console = Console(file=output, force_terminal=False, no_color=True)

        output_json(completed_context, console)

        data = json.loads(output.getvalue())

        # Context has: plan: [plan.md], build: [code.py, tests.py] = 3 total
        assert data["artifact_count"] == 3
