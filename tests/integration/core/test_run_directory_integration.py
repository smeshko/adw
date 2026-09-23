"""Integration tests for run directory management.

These tests verify the full workflow of run directory creation and management
as it would be used in a real project.
"""

from datetime import datetime
from pathlib import Path

import pytest
from ulid import ULID

from adw.core.run_directory import RunDirectoryManager
from adw.models import RunContext


@pytest.fixture
def project_structure(tmp_path: Path) -> Path:
    """Create a realistic project structure for integration testing."""
    # Create common project directories
    (tmp_path / "src").mkdir()
    (tmp_path / "tests").mkdir()
    (tmp_path / ".git").mkdir()  # Simulate git repo
    return tmp_path


class TestFullWorkflow:
    """Test the complete run directory creation workflow."""

    def test_complete_run_lifecycle(self, project_structure: Path) -> None:
        """Test creating and accessing a run directory."""
        manager = RunDirectoryManager(project_structure)

        # Create a run
        context = RunContext(
            run_id=str(ULID()),
            feature_description="Add user authentication",
            current_phase="plan",
            started_at=datetime.now(),
        )

        run_dir = manager.create(context)

        # Verify directory structure
        assert run_dir.exists()
        assert (run_dir / "artifacts").is_dir()
        assert (run_dir / "logs").is_dir()
        assert (run_dir / "llm").is_dir()
        assert (run_dir / "snapshots").is_dir()
        assert (run_dir / ".lock").is_file()
        assert (run_dir / "context.json").is_file()

        # The run lives under runs_dir, named by its run id
        assert run_dir == manager.runs_dir / context.run_id
        assert (manager.runs_dir / context.run_id / "context.json").is_file()

        # Verify context can be loaded
        loaded_context = RunContext.model_validate_json(
            (run_dir / "context.json").read_text()
        )
        assert loaded_context.run_id == context.run_id
        assert loaded_context.feature_description == context.feature_description

    def test_multiple_runs_workflow(self, project_structure: Path) -> None:
        """Test managing multiple runs in sequence."""
        import time

        manager = RunDirectoryManager(project_structure)

        # Create multiple runs
        run_ids = []
        for i in range(5):
            context = RunContext(
                run_id=str(ULID()),
                feature_description=f"Feature {i}",
                current_phase="plan",
                started_at=datetime.now(),
            )
            run_ids.append(context.run_id)
            manager.create(context)
            time.sleep(0.01)  # Ensure unique ULIDs

        # Verify all runs exist
        for run_id in run_ids:
            assert (manager.runs_dir / run_id / "context.json").is_file()

        # Verify chronological sorting
        assert sorted(p.name for p in manager.runs_dir.iterdir()) == run_ids


class TestPersistenceAcrossRestarts:
    """Test that run directories persist across manager restarts."""

    def test_runs_persist_after_manager_recreated(
        self, project_structure: Path
    ) -> None:
        """Test that runs survive manager instance recreation."""
        # Create run with first manager
        manager1 = RunDirectoryManager(project_structure)
        context = RunContext(
            run_id=str(ULID()),
            feature_description="Persistent run",
            current_phase="plan",
            started_at=datetime.now(),
        )
        run_dir = manager1.create(context)
        original_run_id = context.run_id

        # Delete manager reference
        del manager1

        # Create new manager pointing to same project
        manager2 = RunDirectoryManager(project_structure)

        # Should find the same run
        assert manager2.runs_dir / original_run_id == run_dir
        assert (manager2.runs_dir / original_run_id / "context.json").is_file()

        # Context should still be loadable
        loaded = RunContext.model_validate_json((run_dir / "context.json").read_text())
        assert loaded.run_id == original_run_id


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_special_characters_in_project_path(self, tmp_path: Path) -> None:
        """Test handling of special characters in project path."""
        special_path = tmp_path / "project with spaces & symbols"
        special_path.mkdir()

        manager = RunDirectoryManager(special_path)
        context = RunContext(
            run_id=str(ULID()),
            feature_description="Special path test",
            current_phase="plan",
            started_at=datetime.now(),
        )

        run_dir = manager.create(context)
        assert run_dir.exists()

        # Verify the run is on disk where the manager expects it
        assert (manager.runs_dir / context.run_id / "context.json").is_file()

    def test_unicode_in_feature_description(self, project_structure: Path) -> None:
        """Test handling of unicode in context fields."""
        manager = RunDirectoryManager(project_structure)

        # Use unicode in feature description
        context = RunContext(
            run_id=str(ULID()),
            feature_description="添加用户认证 🔐 مصادقة المستخدم",
            current_phase="plan",
            started_at=datetime.now(),
        )

        run_dir = manager.create(context)
        assert run_dir.exists()

        # Verify unicode persisted correctly
        loaded = RunContext.model_validate_json((run_dir / "context.json").read_text())
        assert loaded.feature_description == context.feature_description

    def test_deeply_nested_project_path(self, tmp_path: Path) -> None:
        """Test handling of deeply nested project paths."""
        deep_path = tmp_path
        for i in range(20):
            deep_path = deep_path / f"level_{i}"
        deep_path.mkdir(parents=True)

        manager = RunDirectoryManager(deep_path)
        context = RunContext(
            run_id=str(ULID()),
            feature_description="Deep path test",
            current_phase="plan",
            started_at=datetime.now(),
        )

        run_dir = manager.create(context)
        assert run_dir.exists()

        assert (manager.runs_dir / context.run_id / "context.json").is_file()
