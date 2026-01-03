"""Unit tests for IndexManager.

Tests cover:
- register_run() - creates file if not exists, appends entry
- update_run() - finds and updates entry by run_id
- get_recent_runs() - returns correct entries with filters
- _archive_old_entries() - moves old entries to archive
- Edge cases: empty file, corrupted lines, missing file
"""

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from adw.core.index_manager import IndexManager
from adw.models import RunContext
from adw.models.index import IndexEntry


class TestIndexManagerInit:
    """Tests for IndexManager initialization."""

    def test_default_index_path_uses_home_directory(self) -> None:
        """Test that default index path is ~/.adw/index.jsonl."""
        manager = IndexManager()
        expected = Path.home() / ".adw" / "index.jsonl"
        assert manager.index_path == expected

    def test_custom_index_path(self, tmp_path: Path) -> None:
        """Test that custom index path can be provided."""
        custom_path = tmp_path / "custom" / "index.jsonl"
        manager = IndexManager(index_path=custom_path)
        assert manager.index_path == custom_path

    def test_archive_dir_derived_from_index_path(self, tmp_path: Path) -> None:
        """Test that archive directory is sibling to index file."""
        custom_path = tmp_path / "adw" / "index.jsonl"
        manager = IndexManager(index_path=custom_path)
        expected_archive = tmp_path / "adw" / "index-archive"
        assert manager.archive_dir == expected_archive


class TestRegisterRun:
    """Tests for IndexManager.register_run()."""

    def test_creates_index_file_if_not_exists(self, tmp_path: Path) -> None:
        """Test that register_run creates index file if it doesn't exist."""
        index_path = tmp_path / "index.jsonl"
        manager = IndexManager(index_path=index_path)

        context = _create_test_context()
        manager.register_run(context, Path("/test/project"))

        assert index_path.exists()

    def test_creates_parent_directories(self, tmp_path: Path) -> None:
        """Test that register_run creates parent directories."""
        index_path = tmp_path / "nested" / "dirs" / "index.jsonl"
        manager = IndexManager(index_path=index_path)

        context = _create_test_context()
        manager.register_run(context, Path("/test/project"))

        assert index_path.exists()
        assert index_path.parent.exists()

    def test_appends_entry_to_index(self, tmp_path: Path) -> None:
        """Test that register_run appends entry to index file."""
        index_path = tmp_path / "index.jsonl"
        manager = IndexManager(index_path=index_path)

        context = _create_test_context()
        manager.register_run(context, Path("/test/project"))

        content = index_path.read_text()
        assert context.run_id in content
        assert context.feature_description in content

    def test_multiple_entries_on_separate_lines(self, tmp_path: Path) -> None:
        """Test that multiple entries are stored on separate lines (JSONL)."""
        index_path = tmp_path / "index.jsonl"
        manager = IndexManager(index_path=index_path)

        context1 = _create_test_context(run_id="01KDSG2VDHNK0W4HSCZWJZXWS1")
        context2 = _create_test_context(run_id="01KDSG2VDHNK0W4HSCZWJZXWS2")

        manager.register_run(context1, Path("/test/project1"))
        manager.register_run(context2, Path("/test/project2"))

        lines = index_path.read_text().strip().split("\n")
        assert len(lines) == 2

    def test_entry_has_correct_initial_status(self, tmp_path: Path) -> None:
        """Test that new entry has status='running'."""
        index_path = tmp_path / "index.jsonl"
        manager = IndexManager(index_path=index_path)

        context = _create_test_context()
        manager.register_run(context, Path("/test/project"))

        entries = manager.get_recent_runs(limit=10)
        assert len(entries) == 1
        assert entries[0].status == "running"

    def test_entry_includes_project_name_from_path(self, tmp_path: Path) -> None:
        """Test that entry extracts project_name from project_path."""
        index_path = tmp_path / "index.jsonl"
        manager = IndexManager(index_path=index_path)

        context = _create_test_context()
        manager.register_run(context, Path("/path/to/my-awesome-project"))

        entries = manager.get_recent_runs(limit=10)
        assert entries[0].project_name == "my-awesome-project"


class TestUpdateRun:
    """Tests for IndexManager.update_run()."""

    def test_updates_status_field(self, tmp_path: Path) -> None:
        """Test updating run status."""
        index_path = tmp_path / "index.jsonl"
        manager = IndexManager(index_path=index_path)

        context = _create_test_context()
        manager.register_run(context, Path("/test/project"))

        manager.update_run(context.run_id, status="completed")

        entries = manager.get_recent_runs(limit=10)
        assert entries[0].status == "completed"

    def test_updates_completed_at(self, tmp_path: Path) -> None:
        """Test updating completed_at timestamp."""
        index_path = tmp_path / "index.jsonl"
        manager = IndexManager(index_path=index_path)

        context = _create_test_context()
        manager.register_run(context, Path("/test/project"))

        completed_at = datetime.now(UTC)
        manager.update_run(context.run_id, completed_at=completed_at)

        entries = manager.get_recent_runs(limit=10)
        assert entries[0].completed_at is not None

    def test_updates_phase_reached(self, tmp_path: Path) -> None:
        """Test updating phase_reached."""
        index_path = tmp_path / "index.jsonl"
        manager = IndexManager(index_path=index_path)

        context = _create_test_context()
        manager.register_run(context, Path("/test/project"))

        manager.update_run(context.run_id, phase_reached="build")

        entries = manager.get_recent_runs(limit=10)
        assert entries[0].phase_reached == "build"

    def test_updates_phases_completed(self, tmp_path: Path) -> None:
        """Test updating phases_completed list."""
        index_path = tmp_path / "index.jsonl"
        manager = IndexManager(index_path=index_path)

        context = _create_test_context()
        manager.register_run(context, Path("/test/project"))

        manager.update_run(context.run_id, phases_completed=["plan", "code"])

        entries = manager.get_recent_runs(limit=10)
        assert entries[0].phases_completed == ["plan", "code"]

    def test_update_nonexistent_run_id_raises_error(self, tmp_path: Path) -> None:
        """Test that updating nonexistent run_id raises StateError."""
        from adw.exceptions import StateError

        index_path = tmp_path / "index.jsonl"
        manager = IndexManager(index_path=index_path)

        # Empty index
        index_path.parent.mkdir(parents=True, exist_ok=True)
        index_path.touch()

        with pytest.raises(StateError, match="INDEX_ENTRY_NOT_FOUND"):
            manager.update_run("01KDSG2VDHNK0W4HSCZWJZXWSQ", status="completed")

    def test_update_multiple_fields_at_once(self, tmp_path: Path) -> None:
        """Test updating multiple fields in single call."""
        index_path = tmp_path / "index.jsonl"
        manager = IndexManager(index_path=index_path)

        context = _create_test_context()
        manager.register_run(context, Path("/test/project"))

        completed_at = datetime.now(UTC)
        manager.update_run(
            context.run_id,
            status="completed",
            completed_at=completed_at,
            phase_reached="verify",
            phases_completed=["plan", "code", "test", "verify"],
        )

        entries = manager.get_recent_runs(limit=10)
        assert entries[0].status == "completed"
        assert entries[0].completed_at is not None
        assert entries[0].phase_reached == "verify"
        assert entries[0].phases_completed == ["plan", "code", "test", "verify"]


class TestGetRecentRuns:
    """Tests for IndexManager.get_recent_runs()."""

    def test_returns_empty_list_when_no_entries(self, tmp_path: Path) -> None:
        """Test that empty index returns empty list."""
        index_path = tmp_path / "index.jsonl"
        manager = IndexManager(index_path=index_path)

        # Create empty index file
        index_path.parent.mkdir(parents=True, exist_ok=True)
        index_path.touch()

        entries = manager.get_recent_runs(limit=10)
        assert entries == []

    def test_returns_empty_list_when_file_not_exists(self, tmp_path: Path) -> None:
        """Test that missing index file returns empty list."""
        index_path = tmp_path / "nonexistent" / "index.jsonl"
        manager = IndexManager(index_path=index_path)

        entries = manager.get_recent_runs(limit=10)
        assert entries == []

    def test_respects_limit_parameter(self, tmp_path: Path) -> None:
        """Test that limit parameter is respected."""
        index_path = tmp_path / "index.jsonl"
        manager = IndexManager(index_path=index_path)

        # Register 5 runs
        for i in range(5):
            context = _create_test_context(run_id=f"01KDSG2VDHNK0W4HSCZWJZXWS{i}")
            manager.register_run(context, Path(f"/test/project{i}"))

        entries = manager.get_recent_runs(limit=3)
        assert len(entries) == 3

    def test_returns_most_recent_first(self, tmp_path: Path) -> None:
        """Test that entries are returned most recent first."""
        index_path = tmp_path / "index.jsonl"
        manager = IndexManager(index_path=index_path)

        # Register runs with different timestamps
        context1 = _create_test_context(
            run_id="01KDSG2VDHNK0W4HSCZWJZXWS1",
            started_at=datetime(2024, 1, 1, tzinfo=UTC),
        )
        context2 = _create_test_context(
            run_id="01KDSG2VDHNK0W4HSCZWJZXWS2",
            started_at=datetime(2024, 1, 2, tzinfo=UTC),
        )

        manager.register_run(context1, Path("/test/project1"))
        manager.register_run(context2, Path("/test/project2"))

        entries = manager.get_recent_runs(limit=10)
        # Most recent (context2) should be first
        assert entries[0].run_id == "01KDSG2VDHNK0W4HSCZWJZXWS2"
        assert entries[1].run_id == "01KDSG2VDHNK0W4HSCZWJZXWS1"

    def test_filter_by_project_path(self, tmp_path: Path) -> None:
        """Test filtering by project_path."""
        index_path = tmp_path / "index.jsonl"
        manager = IndexManager(index_path=index_path)

        context1 = _create_test_context(run_id="01KDSG2VDHNK0W4HSCZWJZXWS1")
        context2 = _create_test_context(run_id="01KDSG2VDHNK0W4HSCZWJZXWS2")

        manager.register_run(context1, Path("/project/alpha"))
        manager.register_run(context2, Path("/project/beta"))

        entries = manager.get_recent_runs(limit=10, project_path=Path("/project/alpha"))
        assert len(entries) == 1
        assert entries[0].run_id == "01KDSG2VDHNK0W4HSCZWJZXWS1"

    def test_filter_by_status(self, tmp_path: Path) -> None:
        """Test filtering by status."""
        index_path = tmp_path / "index.jsonl"
        manager = IndexManager(index_path=index_path)

        context1 = _create_test_context(run_id="01KDSG2VDHNK0W4HSCZWJZXWS1")
        context2 = _create_test_context(run_id="01KDSG2VDHNK0W4HSCZWJZXWS2")

        manager.register_run(context1, Path("/project/a"))
        manager.register_run(context2, Path("/project/b"))
        manager.update_run(context1.run_id, status="completed")

        entries = manager.get_recent_runs(limit=10, status="completed")
        assert len(entries) == 1
        assert entries[0].run_id == "01KDSG2VDHNK0W4HSCZWJZXWS1"

    def test_skips_corrupted_lines(self, tmp_path: Path) -> None:
        """Test that corrupted JSONL lines are skipped."""
        index_path = tmp_path / "index.jsonl"
        manager = IndexManager(index_path=index_path)

        # Write valid entry
        context = _create_test_context()
        manager.register_run(context, Path("/test/project"))

        # Append corrupted line
        with open(index_path, "a") as f:
            f.write("this is not valid json\n")

        # Should still return the valid entry
        entries = manager.get_recent_runs(limit=10)
        assert len(entries) == 1


class TestArchiveOldEntries:
    """Tests for IndexManager._archive_old_entries()."""

    def test_no_archive_when_under_threshold(self, tmp_path: Path) -> None:
        """Test that no archive happens when under 10,000 entries."""
        index_path = tmp_path / "index.jsonl"
        manager = IndexManager(index_path=index_path)

        # Add a few entries
        for i in range(10):
            # Use valid 26-char ULIDs: base (24 chars) + 2 digit index
            context = _create_test_context(run_id=f"01KDSG2VDHNK0W4HSCZWJZXW{i:02d}")
            manager.register_run(context, Path("/test/project"))

        # Archive should not be created
        assert not manager.archive_dir.exists()

    def test_archive_creates_monthly_file(self, tmp_path: Path) -> None:
        """Test that archive creates YYYY-MM.jsonl files."""
        index_path = tmp_path / "index.jsonl"
        # Use lower threshold for testing
        manager = IndexManager(index_path=index_path, archive_threshold=5)

        # Add entries to trigger archive
        for i in range(10):
            # Use valid 26-char ULIDs: base (24 chars) + 2 digit index
            context = _create_test_context(
                run_id=f"01KDSG2VDHNK0W4HSCZWJZXW{i:02d}",
                started_at=datetime(2024, 1, 15, tzinfo=UTC),
            )
            manager.register_run(context, Path("/test/project"))

        # Manually trigger archive
        manager._archive_old_entries()

        # Archive directory should exist with monthly file
        assert manager.archive_dir.exists()
        archive_files = list(manager.archive_dir.glob("*.jsonl"))
        assert len(archive_files) >= 1

    def test_archive_keeps_newest_entries(self, tmp_path: Path) -> None:
        """Test that archive keeps the newest entries in main index."""
        index_path = tmp_path / "index.jsonl"
        # Use lower threshold for testing
        manager = IndexManager(index_path=index_path, archive_threshold=5)

        # Add 10 entries (threshold is 5)
        for i in range(10):
            # Use valid 26-char ULIDs: base (24 chars) + 2 digit index
            context = _create_test_context(
                run_id=f"01KDSG2VDHNK0W4HSCZWJZXW{i:02d}",
                started_at=datetime(2024, 1, i + 1, tzinfo=UTC),
            )
            manager.register_run(context, Path("/test/project"))

        manager._archive_old_entries()

        # Main index should have threshold/2 (2) newest entries
        entries = manager.get_recent_runs(limit=100)
        assert len(entries) == 2  # 5 // 2 = 2 (keeps newest half after archive)


# Helper functions


def _create_test_context(
    run_id: str = "01KDSG2VDHNK0W4HSCZWJZXWSQ",
    feature_description: str = "Test feature",
    started_at: datetime | None = None,
) -> RunContext:
    """Create a test RunContext with sensible defaults."""
    return RunContext(
        run_id=run_id,
        feature_description=feature_description,
        current_phase="plan",
        started_at=started_at or datetime.now(UTC),
        status="running",
    )
