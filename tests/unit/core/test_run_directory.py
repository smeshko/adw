# TEST REDUCTION: Removed 4 trivial tests (2025-01):
# - TestRunDirectoryManagerModule class (3 tests): class_exists, has_create_method, accepts_project_root
# - test_context_json_is_formatted: implementation detail (JSON indentation)
"""Unit tests for run directory management."""

from datetime import datetime
from pathlib import Path

import pytest
from ulid import ULID

from adw.core.run_directory import RunDirectoryManager
from adw.exceptions import StateError
from adw.models import RunContext


@pytest.fixture
def run_manager(tmp_path: Path) -> RunDirectoryManager:
    """Create a RunDirectoryManager for testing."""
    return RunDirectoryManager(tmp_path)


@pytest.fixture
def sample_context() -> RunContext:
    """Create a sample RunContext for testing."""
    return RunContext(
        run_id=str(ULID()),
        feature_description="Test feature",
        current_phase="plan",
        started_at=datetime.now(),
    )


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

    def test_create_succeeds_when_dir_precreated_by_logging(
        self, run_manager: RunDirectoryManager, sample_context: RunContext
    ) -> None:
        """Test that create succeeds when directory was pre-created by logging.

        This simulates the case where the file logging transport creates
        the run directory (via logs/ subdirectory creation) before
        run_directory_manager.create() is called.
        """
        # Simulate early logging creating the logs directory
        run_dir = run_manager.runs_dir / sample_context.run_id
        logs_dir = run_dir / "logs"
        logs_dir.mkdir(parents=True)

        # create() should succeed because context.json doesn't exist
        result = run_manager.create(sample_context)

        assert result.exists()
        assert (result / "context.json").exists()
        assert (result / "artifacts").exists()

    def test_create_multiple_runs(self, run_manager: RunDirectoryManager) -> None:
        """Test that multiple runs can be created."""
        contexts = [
            RunContext(
                run_id=str(ULID()),
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
