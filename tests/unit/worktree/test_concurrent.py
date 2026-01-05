"""Tests for ConcurrentRunManager.

Tests for managing concurrent ADW run tracking, lock files,
and maximum concurrent run limits.
"""

import json
import os
from datetime import UTC, datetime
from pathlib import Path

import pytest

from adw.exceptions import MaxConcurrentRunsError
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
        assert run.backend_port is None
        assert run.frontend_port is None

    def test_active_run_with_ports(self, tmp_path: Path) -> None:
        """ActiveRun can be created with optional port fields."""
        run = ActiveRun(
            run_id="01HQXK5P3Z7V8R2M4N6T9W1Y3C",
            pid=12345,
            start_time=datetime.now(UTC),
            worktree_path=tmp_path / "trees" / "01HQXK5P3Z7V8R2M4N6T9W1Y3C",
            backend_port=9100,
            frontend_port=9200,
        )

        assert run.backend_port == 9100
        assert run.frontend_port == 9200

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
            backend_port=9100,
            frontend_port=9200,
        )

        lock_file = manager.locks_dir / f"{run_id}.lock"
        assert lock_file.exists()

        data = json.loads(lock_file.read_text())
        assert data["run_id"] == run_id
        assert data["pid"] == os.getpid()
        assert data["worktree_path"] == str(worktree_path)
        assert data["backend_port"] == 9100
        assert data["frontend_port"] == 9200
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

    def test_unregister_run_removes_lock_file(
        self, manager: ConcurrentRunManager, tmp_path: Path
    ) -> None:
        """unregister_run removes the lock file."""
        run_id = "01HQXK5P3Z7V8R2M4N6T9W1Y3C"
        worktree_path = tmp_path / "trees" / run_id

        manager.register_run(run_id=run_id, worktree_path=worktree_path)
        lock_file = manager.locks_dir / f"{run_id}.lock"
        assert lock_file.exists()

        manager.unregister_run(run_id)
        assert not lock_file.exists()

    def test_unregister_run_nonexistent_is_safe(
        self, manager: ConcurrentRunManager
    ) -> None:
        """unregister_run doesn't raise for nonexistent lock file."""
        # Should not raise
        manager.unregister_run("nonexistent_run_id")

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
            backend_port=9100,
            frontend_port=9200,
        )

        runs = manager.get_active_runs()

        assert len(runs) == 1
        assert runs[0].run_id == run_id
        assert runs[0].pid == os.getpid()
        assert runs[0].backend_port == 9100
        assert runs[0].frontend_port == 9200

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

    def test_can_start_run_when_under_limit(
        self, manager: ConcurrentRunManager
    ) -> None:
        """can_start_run returns True when under max_concurrent."""
        assert manager.can_start_run() is True

    def test_can_start_run_when_at_limit(
        self, tmp_path: Path
    ) -> None:
        """can_start_run returns False when at max_concurrent."""
        # Create manager with max_concurrent=1
        manager = ConcurrentRunManager(tmp_path, max_concurrent=1)

        # Register one run with current PID
        manager.register_run(
            run_id="01HQTEST123456789ABCD",
            worktree_path=tmp_path / "trees" / "01HQTEST123456789ABCD",
        )

        assert manager.can_start_run() is False

    def test_check_can_start_or_raise_passes_under_limit(
        self, manager: ConcurrentRunManager
    ) -> None:
        """check_can_start_or_raise doesn't raise when under limit."""
        # Should not raise
        manager.check_can_start_or_raise()

    def test_check_can_start_or_raise_raises_at_limit(
        self, tmp_path: Path
    ) -> None:
        """check_can_start_or_raise raises MaxConcurrentRunsError at limit."""
        manager = ConcurrentRunManager(tmp_path, max_concurrent=1)

        manager.register_run(
            run_id="01HQTEST123456789ABCD",
            worktree_path=tmp_path / "trees" / "01HQTEST123456789ABCD",
        )

        with pytest.raises(MaxConcurrentRunsError) as exc_info:
            manager.check_can_start_or_raise()

        assert exc_info.value.code == "MAX_CONCURRENT_REACHED"
        assert "1" in exc_info.value.message  # max_concurrent value
        assert exc_info.value.context["max_concurrent"] == 1
        assert exc_info.value.context["active_count"] == 1

    def test_get_run_info_returns_active_run(
        self, manager: ConcurrentRunManager, tmp_path: Path
    ) -> None:
        """get_run_info returns ActiveRun for existing run."""
        run_id = "01HQXK5P3Z7V8R2M4N6T9W1Y3C"
        worktree_path = tmp_path / "trees" / run_id

        manager.register_run(
            run_id=run_id,
            worktree_path=worktree_path,
            backend_port=9100,
        )

        run_info = manager.get_run_info(run_id)

        assert run_info is not None
        assert run_info.run_id == run_id
        assert run_info.backend_port == 9100

    def test_get_run_info_returns_none_for_nonexistent(
        self, manager: ConcurrentRunManager
    ) -> None:
        """get_run_info returns None for nonexistent run."""
        run_info = manager.get_run_info("nonexistent")
        assert run_info is None

    def test_get_run_info_returns_none_for_stale_run(
        self, manager: ConcurrentRunManager
    ) -> None:
        """get_run_info returns None and cleans up stale lock."""
        manager.locks_dir.mkdir(parents=True, exist_ok=True)
        lock_file = manager.locks_dir / "stale.lock"
        lock_data = {
            "run_id": "stale",
            "pid": 999999999,
            "start_time": datetime.now(UTC).isoformat(),
            "worktree_path": "/fake/path",
        }
        lock_file.write_text(json.dumps(lock_data))

        run_info = manager.get_run_info("stale")

        assert run_info is None
        assert not lock_file.exists()

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

    def test_get_orphaned_worktrees_empty(
        self, manager: ConcurrentRunManager
    ) -> None:
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


class TestMaxConcurrentRunsError:
    """Tests for MaxConcurrentRunsError exception."""

    def test_error_creation(self) -> None:
        """MaxConcurrentRunsError can be created with required fields."""
        error = MaxConcurrentRunsError(
            code="MAX_CONCURRENT_REACHED",
            message="Maximum concurrent runs reached (15)",
        )

        assert error.code == "MAX_CONCURRENT_REACHED"
        assert error.message == "Maximum concurrent runs reached (15)"
        assert error.context == {}

    def test_error_with_context(self) -> None:
        """MaxConcurrentRunsError stores context information."""
        error = MaxConcurrentRunsError(
            code="MAX_CONCURRENT_REACHED",
            message="Maximum concurrent runs reached (15)",
            context={"max_concurrent": 15, "active_count": 15},
        )

        assert error.context["max_concurrent"] == 15
        assert error.context["active_count"] == 15

    def test_error_to_dict(self) -> None:
        """MaxConcurrentRunsError serializes to dict correctly."""
        error = MaxConcurrentRunsError(
            code="MAX_CONCURRENT_REACHED",
            message="Maximum concurrent runs reached",
            suggestion="Wait for a run to complete",
            context={"max_concurrent": 15},
        )

        d = error.to_dict()

        assert d["code"] == "MAX_CONCURRENT_REACHED"
        assert d["message"] == "Maximum concurrent runs reached"
        assert d["suggestion"] == "Wait for a run to complete"
        assert d["context"]["max_concurrent"] == 15
