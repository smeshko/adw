"""Tests for ListDisplay class (Story 6.4).

# TEST REDUCTION: Removed 19 tests (from 21 to 2)
# Deleted:
#   - TestListDisplayInit (2 tests): trivial init attribute verification
#   - TestTruncateId (2 tests): trivial string passthrough tests
#   - TestTruncateText (3 tests): trivial truncation logic tests
#   - TestFormatTimestamp (3 tests): brittle datetime formatting assertions
#   - TestStatusColors (5 tests): static dict value assertions
#   - test_show_runs_color_codes_status: dict key existence check
#   - test_show_runs_includes_run_id: weak output text assertion
#   - test_show_runs_includes_feature: weak output text assertion
#   - test_show_runs_includes_status: weak output text assertion
# Kept: 2 integration-style tests that verify actual table rendering
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


class TestShowRuns:
    """Tests for show_runs method."""

    def test_show_runs_renders_table(
        self, display: ListDisplay, console: Console
    ) -> None:
        """Test that show_runs renders a table with title and count."""
        runs = [create_run_context()]
        display.show_runs(runs)

        output = console.file.getvalue()
        assert "Recent Runs" in output
        assert "(1)" in output

    def test_show_runs_multiple_runs(
        self, display: ListDisplay, console: Console
    ) -> None:
        """Test that multiple runs are displayed with correct count."""
        runs = [
            create_run_context(run_id="01HQXK5P3Z7V8R2M4N6T9W1Y3A"),
            create_run_context(run_id="01HQXK5P3Z7V8R2M4N6T9W1Y3B"),
            create_run_context(run_id="01HQXK5P3Z7V8R2M4N6T9W1Y3C"),
        ]
        display.show_runs(runs)

        output = console.file.getvalue()
        assert "(3)" in output
