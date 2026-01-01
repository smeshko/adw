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
