"""Unit tests for run directory management."""

from datetime import datetime
from pathlib import Path

import pytest

from adw.core.run_directory import RunDirectoryManager
from adw.exceptions import StateError
from adw.models import RunContext
from adw.utils.ulid import generate_run_id


@pytest.fixture
def run_manager(tmp_path: Path) -> RunDirectoryManager:
    """Create a RunDirectoryManager for testing."""
    return RunDirectoryManager(tmp_path)


@pytest.fixture
def sample_context() -> RunContext:
    """Create a sample RunContext for testing."""
    return RunContext(
        run_id=generate_run_id(),
        feature_description="Test feature",
        current_phase="plan",
        started_at=datetime.now(),
    )


class TestRunDirectoryManagerModule:
    """Test that the run directory module exists and can be imported."""

    def test_run_directory_manager_class_exists(self) -> None:
        """Test that RunDirectoryManager class exists."""
        assert RunDirectoryManager is not None

    def test_run_directory_manager_has_create_method(self) -> None:
        """Test that RunDirectoryManager has a create method."""
        assert hasattr(RunDirectoryManager, "create")

    def test_run_directory_manager_accepts_project_root(
        self, tmp_path: Path
    ) -> None:
        """Test that RunDirectoryManager can be instantiated with project_root."""
        manager = RunDirectoryManager(project_root=tmp_path)
        assert manager.project_root == tmp_path


class TestDirectoryStructureCreation:
    """Test directory structure creation."""

    def test_create_directory_structure(
        self, run_manager: RunDirectoryManager, sample_context: RunContext
    ) -> None:
        """Test that all required subdirectories are created."""
        run_dir = run_manager.create(sample_context)

        assert run_dir.exists()
        assert (run_dir / "artifacts").exists()
        assert (run_dir / "logs").exists()
        assert (run_dir / "llm").exists()
        assert (run_dir / "snapshots").exists()

    def test_create_returns_correct_path(
        self, run_manager: RunDirectoryManager, sample_context: RunContext
    ) -> None:
        """Test that create returns the correct path."""
        run_dir = run_manager.create(sample_context)

        expected = run_manager.runs_dir / sample_context.run_id
        assert run_dir == expected

    def test_create_creates_runs_dir_parent(
        self, run_manager: RunDirectoryManager, sample_context: RunContext
    ) -> None:
        """Test that create creates .adw/runs/ parent directory."""
        run_dir = run_manager.create(sample_context)

        assert run_manager.runs_dir.exists()
        assert run_manager.runs_dir == run_dir.parent

    def test_create_with_existing_run_id_raises_error(
        self, run_manager: RunDirectoryManager, sample_context: RunContext
    ) -> None:
        """Test that creating duplicate run raises StateError."""
        run_manager.create(sample_context)

        with pytest.raises(StateError) as exc_info:
            run_manager.create(sample_context)

        assert exc_info.value.code == "RUN_ALREADY_EXISTS"
        assert not exc_info.value.recoverable

    def test_create_multiple_runs(
        self, run_manager: RunDirectoryManager
    ) -> None:
        """Test that multiple runs can be created."""
        contexts = [
            RunContext(
                run_id=generate_run_id(),
                feature_description=f"Feature {i}",
                current_phase="plan",
                started_at=datetime.now(),
            )
            for i in range(3)
        ]

        run_dirs = [run_manager.create(ctx) for ctx in contexts]

        # All should exist and be unique
        assert len(set(run_dirs)) == 3
        for run_dir in run_dirs:
            assert run_dir.exists()


class TestFileLocking:
    """Test file locking functionality."""

    def test_lock_file_created_after_create(
        self, run_manager: RunDirectoryManager, sample_context: RunContext
    ) -> None:
        """Test that .lock file is created when run directory is created."""
        run_dir = run_manager.create(sample_context)
        assert (run_dir / ".lock").exists()

    def test_acquire_lock_returns_context_manager(
        self, run_manager: RunDirectoryManager, sample_context: RunContext
    ) -> None:
        """Test that acquire_lock returns a context manager."""
        run_dir = run_manager.create(sample_context)
        lock = run_manager.acquire_lock(sample_context.run_id)

        # Should be usable as context manager
        with lock:
            # Should not raise
            pass

    def test_acquire_lock_is_exclusive(
        self, run_manager: RunDirectoryManager, sample_context: RunContext
    ) -> None:
        """Test that only one process can hold the lock at a time."""
        import filelock

        run_dir = run_manager.create(sample_context)

        # First lock should succeed
        lock1 = run_manager.acquire_lock(sample_context.run_id, timeout=1)
        lock1.acquire()

        try:
            # Second lock with short timeout should fail
            lock2 = run_manager.acquire_lock(sample_context.run_id, timeout=0.1)
            with pytest.raises(filelock.Timeout):
                lock2.acquire()
        finally:
            lock1.release()

    def test_acquire_lock_for_nonexistent_run_raises_error(
        self, run_manager: RunDirectoryManager
    ) -> None:
        """Test that acquiring lock for nonexistent run raises StateError."""
        with pytest.raises(StateError) as exc_info:
            run_manager.acquire_lock("nonexistent_run_id")

        assert exc_info.value.code == "RUN_NOT_FOUND"


class TestContextSerialization:
    """Test context serialization functionality."""

    def test_context_json_created_after_create(
        self, run_manager: RunDirectoryManager, sample_context: RunContext
    ) -> None:
        """Test that context.json is created when run directory is created."""
        run_dir = run_manager.create(sample_context)
        assert (run_dir / "context.json").exists()

    def test_context_json_contains_valid_content(
        self, run_manager: RunDirectoryManager, sample_context: RunContext
    ) -> None:
        """Test that context.json contains valid JSON that can be loaded."""
        import json

        run_dir = run_manager.create(sample_context)
        context_path = run_dir / "context.json"

        content = context_path.read_text()
        data = json.loads(content)

        assert data["run_id"] == sample_context.run_id
        assert data["feature_description"] == sample_context.feature_description
        assert data["current_phase"] == sample_context.current_phase

    def test_context_json_can_be_deserialized(
        self, run_manager: RunDirectoryManager, sample_context: RunContext
    ) -> None:
        """Test that context.json can be deserialized back to RunContext."""
        run_dir = run_manager.create(sample_context)
        context_path = run_dir / "context.json"

        loaded = RunContext.model_validate_json(context_path.read_text())

        assert loaded.run_id == sample_context.run_id
        assert loaded.feature_description == sample_context.feature_description
        assert loaded.current_phase == sample_context.current_phase
        assert loaded.status == sample_context.status

    def test_context_json_is_formatted(
        self, run_manager: RunDirectoryManager, sample_context: RunContext
    ) -> None:
        """Test that context.json is human-readable (indented)."""
        run_dir = run_manager.create(sample_context)
        context_path = run_dir / "context.json"

        content = context_path.read_text()
        # Indented JSON should have newlines
        assert "\n" in content
