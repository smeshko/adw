"""Unit tests for run directory management."""

import pytest

from adw.core.run_directory import RunDirectoryManager


class TestRunDirectoryManagerModule:
    """Test that the run directory module exists and can be imported."""

    def test_run_directory_manager_class_exists(self) -> None:
        """Test that RunDirectoryManager class exists."""
        assert RunDirectoryManager is not None

    def test_run_directory_manager_has_create_method(self) -> None:
        """Test that RunDirectoryManager has a create method."""
        assert hasattr(RunDirectoryManager, "create")

    def test_run_directory_manager_accepts_project_root(
        self, tmp_path: pytest.TempPathFactory
    ) -> None:
        """Test that RunDirectoryManager can be instantiated with project_root."""
        manager = RunDirectoryManager(project_root=tmp_path)
        assert manager.project_root == tmp_path
