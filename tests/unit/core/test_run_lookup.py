"""Tests for RunLookup class.

Tests for finding runs by ID and finding the most recent incomplete run.
"""

from datetime import UTC, datetime
from pathlib import Path

import pytest

from adw.core.run_lookup import RunLookup
from adw.models import RunContext


@pytest.fixture
def runs_dir(tmp_path: Path) -> Path:
    """Create a runs directory for testing."""
    runs_dir = tmp_path / ".adw" / "runs"
    runs_dir.mkdir(parents=True)
    return runs_dir


def create_test_run(
    runs_dir: Path,
    run_id: str,
    status: str = "running",
    current_phase: str = "plan",
    phase_history: list[str] | None = None,
) -> RunContext:
    """Create a test run in the runs directory.

    Args:
        runs_dir: Path to runs directory.
        run_id: Run ID to use.
        status: Run status.
        current_phase: Current phase.
        phase_history: List of completed phases.

    Returns:
        Created RunContext.
    """
    run_dir = runs_dir / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    context = RunContext(
        run_id=run_id,
        feature_description="Test feature",
        current_phase=current_phase,
        phase_history=phase_history or [],
        started_at=datetime.now(UTC),
        status=status,
    )

    context_path = run_dir / "context.json"
    context_path.write_text(context.model_dump_json(indent=2))

    return context


class TestRunLookupInit:
    """Tests for RunLookup initialization."""

    def test_init_with_path(self, runs_dir: Path) -> None:
        """Test that RunLookup can be initialized with a path."""
        lookup = RunLookup(runs_dir)
        assert lookup.runs_dir == runs_dir

    def test_init_creates_context_manager(self, runs_dir: Path) -> None:
        """Test that RunLookup creates a ContextManager."""
        lookup = RunLookup(runs_dir)
        assert lookup.context_manager is not None


class TestFindById:
    """Tests for find_by_id method."""

    def test_find_existing_run(self, runs_dir: Path) -> None:
        """Test finding an existing run by ID."""
        run_id = "01HQXK5P3Z7V8R2M4N6T9W1Y3C"
        create_test_run(runs_dir, run_id)

        lookup = RunLookup(runs_dir)
        context = lookup.find_by_id(run_id)

        assert context is not None
        assert context.run_id == run_id

    def test_find_nonexistent_run_returns_none(self, runs_dir: Path) -> None:
        """Test that finding a non-existent run returns None."""
        lookup = RunLookup(runs_dir)
        context = lookup.find_by_id("01HQXK5P3Z7V8R2M4N6T9W1Y3C")

        assert context is None

    def test_find_run_with_corrupted_context_returns_none(self, runs_dir: Path) -> None:
        """Test that corrupted context files return None instead of raising."""
        run_id = "01HQXK5P3Z7V8R2M4N6T9W1Y3C"
        run_dir = runs_dir / run_id
        run_dir.mkdir(parents=True)

        # Write invalid JSON
        context_path = run_dir / "context.json"
        context_path.write_text("{ invalid json }")

        lookup = RunLookup(runs_dir)
        context = lookup.find_by_id(run_id)

        assert context is None


class TestFindMostRecentIncomplete:
    """Tests for find_most_recent_incomplete method."""

    def test_find_most_recent_when_no_runs(self, runs_dir: Path) -> None:
        """Test that None is returned when no runs exist."""
        lookup = RunLookup(runs_dir)
        context = lookup.find_most_recent_incomplete()

        assert context is None

    def test_find_most_recent_failed_run(self, runs_dir: Path) -> None:
        """Test finding the most recent failed run."""
        # Create runs with different statuses
        create_test_run(runs_dir, "01HQXK5P3Z7V8R2M4N6T9W1Y3A", status="completed")
        create_test_run(runs_dir, "01HQXK5P3Z7V8R2M4N6T9W1Y3B", status="failed")
        create_test_run(runs_dir, "01HQXK5P3Z7V8R2M4N6T9W1Y3C", status="completed")

        lookup = RunLookup(runs_dir)
        context = lookup.find_most_recent_incomplete()

        assert context is not None
        assert context.run_id == "01HQXK5P3Z7V8R2M4N6T9W1Y3B"
        assert context.status == "failed"

    def test_find_most_recent_interrupted_run(self, runs_dir: Path) -> None:
        """Test finding an interrupted run."""
        create_test_run(runs_dir, "01HQXK5P3Z7V8R2M4N6T9W1Y3A", status="completed")
        create_test_run(runs_dir, "01HQXK5P3Z7V8R2M4N6T9W1Y3B", status="interrupted")

        lookup = RunLookup(runs_dir)
        context = lookup.find_most_recent_incomplete()

        assert context is not None
        assert context.status == "interrupted"

    def test_find_most_recent_running_run(self, runs_dir: Path) -> None:
        """Test finding a run with status 'running'."""
        create_test_run(runs_dir, "01HQXK5P3Z7V8R2M4N6T9W1Y3A", status="running")

        lookup = RunLookup(runs_dir)
        context = lookup.find_most_recent_incomplete()

        assert context is not None
        assert context.status == "running"

    def test_returns_none_when_all_completed(self, runs_dir: Path) -> None:
        """Test that None is returned when all runs are completed."""
        create_test_run(runs_dir, "01HQXK5P3Z7V8R2M4N6T9W1Y3A", status="completed")
        create_test_run(runs_dir, "01HQXK5P3Z7V8R2M4N6T9W1Y3B", status="completed")

        lookup = RunLookup(runs_dir)
        context = lookup.find_most_recent_incomplete()

        assert context is None

    def test_most_recent_by_ulid_order(self, runs_dir: Path) -> None:
        """Test that the most recent by ULID is returned.

        ULIDs are lexicographically sortable by creation time.
        Later ULIDs sort after earlier ones.
        """
        # Create runs with ULIDs in specific order
        # Older ULID (should NOT be returned)
        create_test_run(runs_dir, "01HQXK5P3Z7V8R2M4N6T9W1Y3A", status="failed")
        # Newer ULID (SHOULD be returned)
        create_test_run(runs_dir, "01HQXK5P3Z7V8R2M4N6T9W1Y3Z", status="failed")
        # Even older ULID
        create_test_run(runs_dir, "01HQXK5P3Z7V8R2M4N6T9W1Y30", status="failed")

        lookup = RunLookup(runs_dir)
        context = lookup.find_most_recent_incomplete()

        assert context is not None
        # Z > A > 0 in ULID sorting
        assert context.run_id == "01HQXK5P3Z7V8R2M4N6T9W1Y3Z"

    def test_skips_corrupted_runs(self, runs_dir: Path) -> None:
        """Test that corrupted runs are skipped when finding incomplete runs."""
        # Create a valid failed run
        create_test_run(runs_dir, "01HQXK5P3Z7V8R2M4N6T9W1Y3A", status="failed")

        # Create a corrupted run directory
        corrupted_dir = runs_dir / "01HQXK5P3Z7V8R2M4N6T9W1Y3B"
        corrupted_dir.mkdir(parents=True)
        (corrupted_dir / "context.json").write_text("{ invalid }")

        lookup = RunLookup(runs_dir)
        context = lookup.find_most_recent_incomplete()

        # Should find the valid run despite corrupted one
        assert context is not None
        assert context.run_id == "01HQXK5P3Z7V8R2M4N6T9W1Y3A"

    def test_ignores_non_directory_entries(self, runs_dir: Path) -> None:
        """Test that non-directory entries in runs_dir are ignored."""
        # Create a valid run
        create_test_run(runs_dir, "01HQXK5P3Z7V8R2M4N6T9W1Y3A", status="failed")

        # Create a file (not a directory) in runs_dir
        (runs_dir / "somefile.txt").write_text("not a run")

        lookup = RunLookup(runs_dir)
        context = lookup.find_most_recent_incomplete()

        assert context is not None
        assert context.run_id == "01HQXK5P3Z7V8R2M4N6T9W1Y3A"

    def test_handles_missing_runs_dir(self, tmp_path: Path) -> None:
        """Test that missing runs_dir returns None instead of raising."""
        nonexistent = tmp_path / "nonexistent" / "runs"
        lookup = RunLookup(nonexistent)

        context = lookup.find_most_recent_incomplete()
        assert context is None


class TestListRuns:
    """Tests for list_runs method (Story 6.4)."""

    def test_list_returns_empty_when_no_runs(self, runs_dir: Path) -> None:
        """Test that list returns empty list when no runs exist."""
        lookup = RunLookup(runs_dir)
        runs = lookup.list_runs()

        assert runs == []

    def test_list_returns_default_limit(self, runs_dir: Path) -> None:
        """Test that list returns default 10 runs when more exist."""
        # Create 15 runs
        for i in range(15):
            run_id = f"01HQXK5P3Z7V8R2M4N6T9W{i:04d}"
            create_test_run(runs_dir, run_id, status="completed")

        lookup = RunLookup(runs_dir)
        runs = lookup.list_runs()

        assert len(runs) == 10

    def test_list_respects_custom_limit(self, runs_dir: Path) -> None:
        """Test that list respects custom limit parameter."""
        # Create 10 runs
        for i in range(10):
            run_id = f"01HQXK5P3Z7V8R2M4N6T9W{i:04d}"
            create_test_run(runs_dir, run_id, status="completed")

        lookup = RunLookup(runs_dir)
        runs = lookup.list_runs(limit=5)

        assert len(runs) == 5

    def test_list_sorted_newest_first(self, runs_dir: Path) -> None:
        """Test that runs are sorted newest first by ULID."""
        # Create runs with specific ULIDs (lexicographic order)
        create_test_run(runs_dir, "01HQXK5P3Z7V8R2M4N6T9W1Y3A", status="completed")
        create_test_run(runs_dir, "01HQXK5P3Z7V8R2M4N6T9W1Y3Z", status="completed")
        create_test_run(runs_dir, "01HQXK5P3Z7V8R2M4N6T9W1Y30", status="completed")

        lookup = RunLookup(runs_dir)
        runs = lookup.list_runs()

        # Z > A > 0 in ULID sorting (newest first)
        assert runs[0].run_id == "01HQXK5P3Z7V8R2M4N6T9W1Y3Z"
        assert runs[1].run_id == "01HQXK5P3Z7V8R2M4N6T9W1Y3A"
        assert runs[2].run_id == "01HQXK5P3Z7V8R2M4N6T9W1Y30"

    def test_list_filters_by_status(self, runs_dir: Path) -> None:
        """Test that status filter works correctly."""
        create_test_run(runs_dir, "01HQXK5P3Z7V8R2M4N6T9W1Y3A", status="completed")
        create_test_run(runs_dir, "01HQXK5P3Z7V8R2M4N6T9W1Y3B", status="failed")
        create_test_run(runs_dir, "01HQXK5P3Z7V8R2M4N6T9W1Y3C", status="completed")
        create_test_run(runs_dir, "01HQXK5P3Z7V8R2M4N6T9W1Y3D", status="failed")

        lookup = RunLookup(runs_dir)
        failed_runs = lookup.list_runs(status="failed")

        assert len(failed_runs) == 2
        assert all(r.status == "failed" for r in failed_runs)

    def test_list_filters_by_running_status(self, runs_dir: Path) -> None:
        """Test filtering by running status."""
        create_test_run(runs_dir, "01HQXK5P3Z7V8R2M4N6T9W1Y3A", status="completed")
        create_test_run(runs_dir, "01HQXK5P3Z7V8R2M4N6T9W1Y3B", status="running")

        lookup = RunLookup(runs_dir)
        running_runs = lookup.list_runs(status="running")

        assert len(running_runs) == 1
        assert running_runs[0].status == "running"

    def test_list_filters_by_interrupted_status(self, runs_dir: Path) -> None:
        """Test filtering by interrupted status."""
        create_test_run(runs_dir, "01HQXK5P3Z7V8R2M4N6T9W1Y3A", status="completed")
        create_test_run(runs_dir, "01HQXK5P3Z7V8R2M4N6T9W1Y3B", status="interrupted")

        lookup = RunLookup(runs_dir)
        interrupted_runs = lookup.list_runs(status="interrupted")

        assert len(interrupted_runs) == 1
        assert interrupted_runs[0].status == "interrupted"

    def test_list_returns_fewer_when_less_exist(self, runs_dir: Path) -> None:
        """Test that list returns all runs when fewer than limit exist."""
        create_test_run(runs_dir, "01HQXK5P3Z7V8R2M4N6T9W1Y3A", status="completed")
        create_test_run(runs_dir, "01HQXK5P3Z7V8R2M4N6T9W1Y3B", status="completed")
        create_test_run(runs_dir, "01HQXK5P3Z7V8R2M4N6T9W1Y3C", status="completed")

        lookup = RunLookup(runs_dir)
        runs = lookup.list_runs(limit=10)

        assert len(runs) == 3

    def test_list_skips_corrupted_runs(self, runs_dir: Path) -> None:
        """Test that corrupted runs are skipped."""
        # Create valid runs
        create_test_run(runs_dir, "01HQXK5P3Z7V8R2M4N6T9W1Y3A", status="completed")
        create_test_run(runs_dir, "01HQXK5P3Z7V8R2M4N6T9W1Y3C", status="completed")

        # Create a corrupted run
        corrupted_dir = runs_dir / "01HQXK5P3Z7V8R2M4N6T9W1Y3B"
        corrupted_dir.mkdir(parents=True)
        (corrupted_dir / "context.json").write_text("{ invalid }")

        lookup = RunLookup(runs_dir)
        runs = lookup.list_runs()

        # Should only get the valid runs
        assert len(runs) == 2

    def test_list_ignores_non_directory_entries(self, runs_dir: Path) -> None:
        """Test that non-directory entries are ignored."""
        create_test_run(runs_dir, "01HQXK5P3Z7V8R2M4N6T9W1Y3A", status="completed")
        (runs_dir / "somefile.txt").write_text("not a run")

        lookup = RunLookup(runs_dir)
        runs = lookup.list_runs()

        assert len(runs) == 1

    def test_list_handles_missing_runs_dir(self, tmp_path: Path) -> None:
        """Test that missing runs_dir returns empty list."""
        nonexistent = tmp_path / "nonexistent" / "runs"
        lookup = RunLookup(nonexistent)

        runs = lookup.list_runs()
        assert runs == []

    def test_list_filter_returns_empty_when_no_match(self, runs_dir: Path) -> None:
        """Test that filter returns empty when no runs match."""
        create_test_run(runs_dir, "01HQXK5P3Z7V8R2M4N6T9W1Y3A", status="completed")
        create_test_run(runs_dir, "01HQXK5P3Z7V8R2M4N6T9W1Y3B", status="completed")

        lookup = RunLookup(runs_dir)
        failed_runs = lookup.list_runs(status="failed")

        assert failed_runs == []
