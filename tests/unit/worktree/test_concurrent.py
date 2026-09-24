"""Tests for ConcurrentRunManager.

Tests for managing concurrent ADW run tracking, lock files,
and maximum concurrent run limits.
"""

import json
import os
from datetime import UTC, datetime
from pathlib import Path

import pytest

from adw.exceptions import WorktreeError
from adw.worktree.concurrent import ActiveRun, ConcurrentRunManager


class TestActiveRun:
    """Tests for ActiveRun model."""

    def test_active_run_creation(self, tmp_path: Path) -> None:
        """ActiveRun can be created with required fields."""
        run = ActiveRun(
            run_id="01HQXK5P3Z7V8R2M4N6T9W1Y3C",
            pid=12345,
            start_time=datetime.now(UTC),
            worktree_path=tmp_path / "trees" / "01HQXK5P3Z7V8R2M4N6T9W1Y3C",
        )

        assert run.run_id == "01HQXK5P3Z7V8R2M4N6T9W1Y3C"
        assert run.pid == 12345
        assert run.worktree_path == tmp_path / "trees" / "01HQXK5P3Z7V8R2M4N6T9W1Y3C"

    def test_is_pid_running_for_current_process(self, tmp_path: Path) -> None:
        """is_pid_running returns True for current process."""
        run = ActiveRun(
            run_id="01HQXK5P3Z7V8R2M4N6T9W1Y3C",
            pid=os.getpid(),  # Current process PID
            start_time=datetime.now(UTC),
            worktree_path=tmp_path / "trees" / "01HQXK5P3Z7V8R2M4N6T9W1Y3C",
        )

        assert run.is_pid_running() is True

    def test_is_pid_running_for_invalid_pid(self, tmp_path: Path) -> None:
        """is_pid_running returns False for non-existent PID."""
        # Use a PID that almost certainly doesn't exist
        run = ActiveRun(
            run_id="01HQXK5P3Z7V8R2M4N6T9W1Y3C",
            pid=999999999,  # Very unlikely to be a real PID
            start_time=datetime.now(UTC),
            worktree_path=tmp_path / "trees" / "01HQXK5P3Z7V8R2M4N6T9W1Y3C",
        )

        assert run.is_pid_running() is False


class TestConcurrentRunManager:
    """Tests for ConcurrentRunManager."""

    @pytest.fixture
    def manager(self, tmp_path: Path) -> ConcurrentRunManager:
        """Create a ConcurrentRunManager for testing."""
        return ConcurrentRunManager(tmp_path, max_concurrent=15)

    def test_initialization(self, tmp_path: Path) -> None:
        """ConcurrentRunManager initializes with correct defaults."""
        manager = ConcurrentRunManager(tmp_path)

        assert manager.project_root == tmp_path
        assert manager.max_concurrent == 15
        assert manager.locks_dir == tmp_path / "trees" / ".locks"

    def test_initialization_with_custom_values(self, tmp_path: Path) -> None:
        """ConcurrentRunManager respects custom initialization values."""
        manager = ConcurrentRunManager(
            tmp_path,
            max_concurrent=10,
            base_dir="worktrees",
        )

        assert manager.max_concurrent == 10
        assert manager.locks_dir == tmp_path / "worktrees" / ".locks"

    def test_get_active_runs_empty(self, manager: ConcurrentRunManager) -> None:
        """get_active_runs returns empty list when no locks exist."""
        runs = manager.get_active_runs()
        assert runs == []

    def test_register_run_creates_lock_file(
        self, manager: ConcurrentRunManager, tmp_path: Path
    ) -> None:
        """register_run creates a lock file with correct content."""
        run_id = "01HQXK5P3Z7V8R2M4N6T9W1Y3C"
        worktree_path = tmp_path / "trees" / run_id

        manager.register_run(
            run_id=run_id,
            worktree_path=worktree_path,
        )

        lock_file = manager.locks_dir / f"{run_id}.lock"
        assert lock_file.exists()

        data = json.loads(lock_file.read_text())
        assert data["run_id"] == run_id
        assert data["pid"] == os.getpid()
        assert data["worktree_path"] == str(worktree_path)
        assert "start_time" in data

    def test_register_run_creates_locks_directory(
        self, manager: ConcurrentRunManager, tmp_path: Path
    ) -> None:
        """register_run creates the locks directory if it doesn't exist."""
        assert not manager.locks_dir.exists()

        manager.register_run(
            run_id="01HQTEST123456789ABCD",
            worktree_path=tmp_path / "trees" / "01HQTEST123456789ABCD",
        )

        assert manager.locks_dir.exists()

    def test_get_active_runs_returns_active_runs(
        self, manager: ConcurrentRunManager, tmp_path: Path
    ) -> None:
        """get_active_runs returns runs with live PIDs."""
        run_id = "01HQXK5P3Z7V8R2M4N6T9W1Y3C"
        worktree_path = tmp_path / "trees" / run_id

        # Register run with current PID (which is alive)
        manager.register_run(
            run_id=run_id,
            worktree_path=worktree_path,
        )

        runs = manager.get_active_runs()

        assert len(runs) == 1
        assert runs[0].run_id == run_id
        assert runs[0].pid == os.getpid()

    def test_get_active_runs_reads_legacy_lock_with_ports(
        self, manager: ConcurrentRunManager, tmp_path: Path
    ) -> None:
        """A lock file written with the old port keys still lists as active."""
        run_id = "01HQXK5P3Z7V8R2M4N6T9W1Y3C"
        manager.locks_dir.mkdir(parents=True, exist_ok=True)
        lock_file = manager.locks_dir / f"{run_id}.lock"
        lock_file.write_text(
            json.dumps(
                {
                    "run_id": run_id,
                    "pid": os.getpid(),
                    "start_time": datetime.now(UTC).isoformat(),
                    "worktree_path": str(tmp_path / "trees" / run_id),
                    "backend_port": 9100,
                    "frontend_port": 9200,
                }
            )
        )

        runs = manager.get_active_runs()

        assert [run.run_id for run in runs] == [run_id]
        assert lock_file.exists()

    def test_get_active_runs_cleans_stale_locks(
        self, manager: ConcurrentRunManager
    ) -> None:
        """get_active_runs removes locks with dead PIDs."""
        # Create a lock file with a dead PID
        manager.locks_dir.mkdir(parents=True, exist_ok=True)
        lock_file = manager.locks_dir / "stale_run.lock"
        lock_data = {
            "run_id": "stale_run",
            "pid": 999999999,  # Non-existent PID
            "start_time": datetime.now(UTC).isoformat(),
            "worktree_path": "/fake/path",
        }
        lock_file.write_text(json.dumps(lock_data))

        # get_active_runs should clean up the stale lock
        runs = manager.get_active_runs()

        assert len(runs) == 0
        assert not lock_file.exists()

    def test_get_active_runs_removes_corrupt_locks(
        self, manager: ConcurrentRunManager
    ) -> None:
        """get_active_runs removes corrupt lock files."""
        manager.locks_dir.mkdir(parents=True, exist_ok=True)
        lock_file = manager.locks_dir / "corrupt.lock"
        lock_file.write_text("not valid json")

        runs = manager.get_active_runs()

        assert len(runs) == 0
        assert not lock_file.exists()

    def test_check_can_start_or_raise_passes_under_limit(
        self, manager: ConcurrentRunManager
    ) -> None:
        """check_can_start_or_raise doesn't raise when under limit."""
        # Should not raise
        manager.check_can_start_or_raise()

    def test_check_can_start_or_raise_raises_at_limit(self, tmp_path: Path) -> None:
        """check_can_start_or_raise raises WorktreeError at limit."""
        manager = ConcurrentRunManager(tmp_path, max_concurrent=1)

        manager.register_run(
            run_id="01HQTEST123456789ABCD",
            worktree_path=tmp_path / "trees" / "01HQTEST123456789ABCD",
        )

        with pytest.raises(WorktreeError) as exc_info:
            manager.check_can_start_or_raise()

        assert exc_info.value.code == "MAX_CONCURRENT_REACHED"
        assert "1" in exc_info.value.message  # max_concurrent value

    def test_multiple_concurrent_runs(
        self, manager: ConcurrentRunManager, tmp_path: Path
    ) -> None:
        """Multiple runs can be registered and tracked."""
        run_ids = [
            "01HQTEST1111111111111111",
            "01HQTEST2222222222222222",
            "01HQTEST3333333333333333",
        ]

        for run_id in run_ids:
            manager.register_run(
                run_id=run_id,
                worktree_path=tmp_path / "trees" / run_id,
            )

        runs = manager.get_active_runs()

        assert len(runs) == 3
        assert {r.run_id for r in runs} == set(run_ids)


class TestOrphanedWorktrees:
    """Tests for orphaned worktree detection."""

    @pytest.fixture
    def manager(self, tmp_path: Path) -> ConcurrentRunManager:
        """Create a ConcurrentRunManager for testing."""
        return ConcurrentRunManager(tmp_path, max_concurrent=15)

    def test_get_orphaned_worktrees_empty(self, manager: ConcurrentRunManager) -> None:
        """Returns empty list when no worktrees exist."""
        orphaned = manager.get_orphaned_worktrees()
        assert orphaned == []

    def test_get_orphaned_worktrees_finds_orphans(
        self, manager: ConcurrentRunManager, tmp_path: Path
    ) -> None:
        """Detects worktrees without active locks."""
        # Create a fake worktree directory with .git
        worktree_dir = tmp_path / "trees" / "orphaned_run"
        worktree_dir.mkdir(parents=True)
        (worktree_dir / ".git").touch()  # Marker for git worktree

        orphaned = manager.get_orphaned_worktrees()

        assert len(orphaned) == 1
        assert orphaned[0] == worktree_dir

    def test_get_orphaned_worktrees_ignores_active_runs(
        self, manager: ConcurrentRunManager, tmp_path: Path
    ) -> None:
        """Does not report worktrees with active locks."""
        run_id = "01HQTEST123456789ABCD"
        worktree_dir = tmp_path / "trees" / run_id
        worktree_dir.mkdir(parents=True)
        (worktree_dir / ".git").touch()

        # Register the run (creates lock with current PID)
        manager.register_run(
            run_id=run_id,
            worktree_path=worktree_dir,
        )

        orphaned = manager.get_orphaned_worktrees()

        # Worktree is not orphaned because it has an active lock
        assert len(orphaned) == 0

    def test_get_orphaned_worktrees_ignores_non_git_directories(
        self, manager: ConcurrentRunManager, tmp_path: Path
    ) -> None:
        """Ignores directories without .git marker."""
        # Create a directory without .git
        non_git_dir = tmp_path / "trees" / "not_a_worktree"
        non_git_dir.mkdir(parents=True)

        orphaned = manager.get_orphaned_worktrees()

        assert len(orphaned) == 0

    def test_get_orphaned_worktrees_ignores_hidden_directories(
        self, manager: ConcurrentRunManager, tmp_path: Path
    ) -> None:
        """Ignores hidden directories like .locks."""
        locks_dir = tmp_path / "trees" / ".locks"
        locks_dir.mkdir(parents=True)
        (locks_dir / ".git").touch()  # Even if it has .git

        orphaned = manager.get_orphaned_worktrees()

        assert len(orphaned) == 0

    def test_get_orphaned_worktrees_multiple(
        self, manager: ConcurrentRunManager, tmp_path: Path
    ) -> None:
        """Detects multiple orphaned worktrees."""
        run_ids = ["orphan1", "orphan2", "orphan3"]

        for run_id in run_ids:
            worktree_dir = tmp_path / "trees" / run_id
            worktree_dir.mkdir(parents=True)
            (worktree_dir / ".git").touch()

        orphaned = manager.get_orphaned_worktrees()

        assert len(orphaned) == 3
        orphaned_names = {p.name for p in orphaned}
        assert orphaned_names == set(run_ids)
