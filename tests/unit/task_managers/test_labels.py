"""Tests for LabelManager service.

Story 12.7 Task 3: Tests for label management service.
"""

import pytest
from unittest.mock import MagicMock

from adw.models.config import TaskManagerLabelsConfig
from adw.task_managers.labels import LabelManager


class TestLabelManagerInit:
    """Tests for LabelManager initialization."""

    def test_init_with_task_manager_and_config(self) -> None:
        """LabelManager initializes with task manager and config."""
        mock_task_manager = MagicMock()
        config = TaskManagerLabelsConfig(enabled=True, prefix="adw:")

        manager = LabelManager(mock_task_manager, config, "task-uuid")

        assert manager._task_manager is mock_task_manager
        assert manager._config is config
        assert manager._task_id == "task-uuid"

    def test_init_stores_current_phase(self) -> None:
        """LabelManager tracks current phase label."""
        mock_task_manager = MagicMock()
        config = TaskManagerLabelsConfig()

        manager = LabelManager(mock_task_manager, config, "task-uuid")

        assert manager._current_phase_label is None


class TestLabelManagerLabelNames:
    """Tests for label name construction."""

    def test_default_prefix_is_adw(self) -> None:
        """Default prefix is 'adw:'."""
        mock_task_manager = MagicMock()
        config = TaskManagerLabelsConfig()

        manager = LabelManager(mock_task_manager, config, "task-uuid")

        assert manager._get_label("running") == "adw:running"
        assert manager._get_label("completed") == "adw:completed"
        assert manager._get_label("failed") == "adw:failed"

    def test_custom_prefix_is_used(self) -> None:
        """Custom prefix is used in label names."""
        mock_task_manager = MagicMock()
        config = TaskManagerLabelsConfig(prefix="ci:")

        manager = LabelManager(mock_task_manager, config, "task-uuid")

        assert manager._get_label("running") == "ci:running"
        assert manager._get_label("phase:build") == "ci:phase:build"

    def test_phase_label_format(self) -> None:
        """Phase labels follow format {prefix}phase:{phase_name}."""
        mock_task_manager = MagicMock()
        config = TaskManagerLabelsConfig(prefix="adw:")

        manager = LabelManager(mock_task_manager, config, "task-uuid")

        assert manager._get_phase_label("plan") == "adw:phase:plan"
        assert manager._get_phase_label("build") == "adw:phase:build"
        assert manager._get_phase_label("validate") == "adw:phase:validate"


class TestLabelManagerSetRunning:
    """Tests for set_running method."""

    def test_set_running_adds_running_label(self) -> None:
        """set_running adds the running label."""
        mock_task_manager = MagicMock()
        config = TaskManagerLabelsConfig()

        manager = LabelManager(mock_task_manager, config, "task-uuid")
        manager.set_running()

        mock_task_manager.add_label.assert_called_once_with("task-uuid", "adw:running")

    def test_set_running_noop_when_disabled(self) -> None:
        """set_running does nothing when labels disabled."""
        mock_task_manager = MagicMock()
        config = TaskManagerLabelsConfig(enabled=False)

        manager = LabelManager(mock_task_manager, config, "task-uuid")
        manager.set_running()

        mock_task_manager.add_label.assert_not_called()


class TestLabelManagerSetPhase:
    """Tests for set_phase method."""

    def test_set_phase_adds_phase_label(self) -> None:
        """set_phase adds the phase label."""
        mock_task_manager = MagicMock()
        config = TaskManagerLabelsConfig()

        manager = LabelManager(mock_task_manager, config, "task-uuid")
        manager.set_phase("build")

        mock_task_manager.add_label.assert_called_with("task-uuid", "adw:phase:build")

    def test_set_phase_removes_previous_phase_label(self) -> None:
        """set_phase removes previous phase label."""
        mock_task_manager = MagicMock()
        config = TaskManagerLabelsConfig()

        manager = LabelManager(mock_task_manager, config, "task-uuid")
        manager.set_phase("plan")
        manager.set_phase("build")

        # Should remove plan, add build
        mock_task_manager.remove_label.assert_called_with("task-uuid", "adw:phase:plan")
        mock_task_manager.add_label.assert_called_with("task-uuid", "adw:phase:build")

    def test_set_phase_tracks_current_phase(self) -> None:
        """set_phase updates current phase tracking."""
        mock_task_manager = MagicMock()
        config = TaskManagerLabelsConfig()

        manager = LabelManager(mock_task_manager, config, "task-uuid")
        manager.set_phase("build")

        assert manager._current_phase_label == "adw:phase:build"

    def test_set_phase_noop_when_disabled(self) -> None:
        """set_phase does nothing when labels disabled."""
        mock_task_manager = MagicMock()
        config = TaskManagerLabelsConfig(enabled=False)

        manager = LabelManager(mock_task_manager, config, "task-uuid")
        manager.set_phase("build")

        mock_task_manager.add_label.assert_not_called()


class TestLabelManagerSetCompleted:
    """Tests for set_completed method."""

    def test_set_completed_removes_running_adds_completed(self) -> None:
        """set_completed removes running and adds completed."""
        mock_task_manager = MagicMock()
        config = TaskManagerLabelsConfig()

        manager = LabelManager(mock_task_manager, config, "task-uuid")
        manager.set_completed()

        mock_task_manager.remove_label.assert_called_with("task-uuid", "adw:running")
        mock_task_manager.add_label.assert_called_with("task-uuid", "adw:completed")

    def test_set_completed_removes_phase_label(self) -> None:
        """set_completed removes current phase label."""
        mock_task_manager = MagicMock()
        config = TaskManagerLabelsConfig()

        manager = LabelManager(mock_task_manager, config, "task-uuid")
        manager._current_phase_label = "adw:phase:validate"
        manager.set_completed()

        # Should remove running, phase, and add completed
        calls = mock_task_manager.remove_label.call_args_list
        assert any(call[0] == ("task-uuid", "adw:phase:validate") for call in calls)

    def test_set_completed_noop_when_disabled(self) -> None:
        """set_completed does nothing when labels disabled."""
        mock_task_manager = MagicMock()
        config = TaskManagerLabelsConfig(enabled=False)

        manager = LabelManager(mock_task_manager, config, "task-uuid")
        manager.set_completed()

        mock_task_manager.add_label.assert_not_called()
        mock_task_manager.remove_label.assert_not_called()


class TestLabelManagerSetFailed:
    """Tests for set_failed method."""

    def test_set_failed_removes_running_adds_failed(self) -> None:
        """set_failed removes running and adds failed."""
        mock_task_manager = MagicMock()
        config = TaskManagerLabelsConfig()

        manager = LabelManager(mock_task_manager, config, "task-uuid")
        manager.set_failed()

        mock_task_manager.remove_label.assert_called_with("task-uuid", "adw:running")
        mock_task_manager.add_label.assert_called_with("task-uuid", "adw:failed")

    def test_set_failed_keeps_phase_label(self) -> None:
        """set_failed keeps phase label for debugging."""
        mock_task_manager = MagicMock()
        config = TaskManagerLabelsConfig()

        manager = LabelManager(mock_task_manager, config, "task-uuid")
        manager._current_phase_label = "adw:phase:build"
        manager.set_failed()

        # Should NOT remove phase label
        for call in mock_task_manager.remove_label.call_args_list:
            assert call[0] != ("task-uuid", "adw:phase:build")

    def test_set_failed_noop_when_disabled(self) -> None:
        """set_failed does nothing when labels disabled."""
        mock_task_manager = MagicMock()
        config = TaskManagerLabelsConfig(enabled=False)

        manager = LabelManager(mock_task_manager, config, "task-uuid")
        manager.set_failed()

        mock_task_manager.add_label.assert_not_called()
        mock_task_manager.remove_label.assert_not_called()


class TestLabelManagerLifecycle:
    """Integration tests for full label lifecycle (Story 12.7 Task 7)."""

    def test_successful_run_lifecycle(self) -> None:
        """Test label lifecycle for a successful run: running -> phases -> completed."""
        mock_task_manager = MagicMock()
        config = TaskManagerLabelsConfig(enabled=True, prefix="adw:")

        manager = LabelManager(mock_task_manager, config, "task-uuid")

        # Run starts
        manager.set_running()
        mock_task_manager.add_label.assert_called_with("task-uuid", "adw:running")

        # Phase 1: plan
        manager.set_phase("plan")
        mock_task_manager.add_label.assert_called_with("task-uuid", "adw:phase:plan")

        # Phase 2: build (removes plan, adds build)
        manager.set_phase("build")
        mock_task_manager.remove_label.assert_called_with("task-uuid", "adw:phase:plan")
        mock_task_manager.add_label.assert_called_with("task-uuid", "adw:phase:build")

        # Run completes (removes running, removes build phase, adds completed)
        mock_task_manager.reset_mock()
        manager.set_completed()

        # Verify running removed
        remove_calls = mock_task_manager.remove_label.call_args_list
        assert any(call[0] == ("task-uuid", "adw:running") for call in remove_calls)
        # Verify build phase removed
        assert any(call[0] == ("task-uuid", "adw:phase:build") for call in remove_calls)
        # Verify completed added
        mock_task_manager.add_label.assert_called_with("task-uuid", "adw:completed")

    def test_failed_run_lifecycle(self) -> None:
        """Test label lifecycle for a failed run: running -> phases -> failed."""
        mock_task_manager = MagicMock()
        config = TaskManagerLabelsConfig(enabled=True, prefix="ci:")

        manager = LabelManager(mock_task_manager, config, "task-uuid")

        # Run starts
        manager.set_running()
        mock_task_manager.add_label.assert_called_with("task-uuid", "ci:running")

        # Phase 1: plan
        manager.set_phase("plan")
        mock_task_manager.add_label.assert_called_with("task-uuid", "ci:phase:plan")

        # Phase 2: build
        manager.set_phase("build")
        mock_task_manager.add_label.assert_called_with("task-uuid", "ci:phase:build")

        # Run fails (removes running, keeps build phase, adds failed)
        mock_task_manager.reset_mock()
        manager.set_failed()

        # Verify running removed
        mock_task_manager.remove_label.assert_called_with("task-uuid", "ci:running")
        # Verify failed added
        mock_task_manager.add_label.assert_called_with("task-uuid", "ci:failed")
        # Phase label should NOT be removed (kept for debugging)
        for call in mock_task_manager.remove_label.call_args_list:
            assert call[0] != ("task-uuid", "ci:phase:build")


class TestLabelManagerErrorResilience:
    """Tests for non-blocking error handling (Story 12.7 Task 6)."""

    def test_set_phase_still_adds_label_when_remove_fails(self) -> None:
        """set_phase adds new label even when remove_label fails."""
        mock_task_manager = MagicMock()
        mock_task_manager.remove_label.side_effect = Exception("API error")
        config = TaskManagerLabelsConfig()

        manager = LabelManager(mock_task_manager, config, "task-uuid")
        manager._current_phase_label = "adw:phase:plan"

        # Should not raise, and should still add new label
        manager.set_phase("build")

        # remove_label was attempted and failed
        mock_task_manager.remove_label.assert_called_once_with(
            "task-uuid", "adw:phase:plan"
        )
        # add_label should still be called
        mock_task_manager.add_label.assert_called_once_with(
            "task-uuid", "adw:phase:build"
        )

    def test_set_completed_still_adds_label_when_remove_fails(self) -> None:
        """set_completed adds completed label even when remove_label fails."""
        mock_task_manager = MagicMock()
        mock_task_manager.remove_label.side_effect = Exception("API error")
        config = TaskManagerLabelsConfig()

        manager = LabelManager(mock_task_manager, config, "task-uuid")

        # Should not raise, and should still add completed label
        manager.set_completed()

        # remove_label was attempted and failed
        mock_task_manager.remove_label.assert_called_once_with(
            "task-uuid", "adw:running"
        )
        # add_label should still be called
        mock_task_manager.add_label.assert_called_once_with(
            "task-uuid", "adw:completed"
        )

    def test_set_failed_still_adds_label_when_remove_fails(self) -> None:
        """set_failed adds failed label even when remove_label fails."""
        mock_task_manager = MagicMock()
        mock_task_manager.remove_label.side_effect = Exception("API error")
        config = TaskManagerLabelsConfig()

        manager = LabelManager(mock_task_manager, config, "task-uuid")

        # Should not raise, and should still add failed label
        manager.set_failed()

        # remove_label was attempted and failed
        mock_task_manager.remove_label.assert_called_once_with(
            "task-uuid", "adw:running"
        )
        # add_label should still be called
        mock_task_manager.add_label.assert_called_once_with(
            "task-uuid", "adw:failed"
        )

    def test_operations_continue_on_partial_failure(self) -> None:
        """Operations continue even when some calls fail."""
        mock_task_manager = MagicMock()
        # First remove succeeds, second remove fails
        mock_task_manager.remove_label.side_effect = [None, Exception("API error")]
        config = TaskManagerLabelsConfig()

        manager = LabelManager(mock_task_manager, config, "task-uuid")
        manager._current_phase_label = "adw:phase:validate"

        # Should not raise
        manager.set_completed()

        # Both removes were attempted
        assert mock_task_manager.remove_label.call_count == 2
        # add_label should still be called for completed
        mock_task_manager.add_label.assert_called_once_with(
            "task-uuid", "adw:completed"
        )
