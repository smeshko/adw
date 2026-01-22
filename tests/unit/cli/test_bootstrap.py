"""Tests for CLI bootstrap module.

Tests for create_orchestrator() task manager service wiring (ISS-033).
Focuses on business logic: StatusSyncService and LabelManager creation.

Per ADR-001: Tests focus on validation logic and integration points,
not trivial attribute assignment.
"""

from unittest.mock import MagicMock, patch

import pytest

from adw.models.config import TaskManagerConfig, TaskManagerLabelsConfig
from adw.models.task import TaskInfo


class TestBootstrapTaskManagerWiring:
    """Tests for task manager service wiring in create_orchestrator (ISS-033)."""

    @pytest.fixture
    def mock_task_manager(self) -> MagicMock:
        """Create a mock TaskManager."""
        manager = MagicMock()
        manager.name = "linear"
        return manager

    @pytest.fixture
    def mock_task_info(self) -> TaskInfo:
        """Create a mock TaskInfo with distinct id and identifier."""
        return TaskInfo(
            id="internal-uuid-123-456-789",
            identifier="RULE-151",
            title="Test Task",
        )

    @pytest.fixture
    def mock_config_with_labels(self) -> TaskManagerConfig:
        """Create a task manager config with labels enabled."""
        return TaskManagerConfig(
            type="linear",
            labels=TaskManagerLabelsConfig(enabled=True),
        )

    @pytest.fixture
    def mock_config_without_labels(self) -> TaskManagerConfig:
        """Create a task manager config with labels disabled."""
        return TaskManagerConfig(
            type="linear",
            labels=TaskManagerLabelsConfig(enabled=False),
        )

    @patch("adw.cli.bootstrap.ConfigLoader")
    @patch("adw.cli.bootstrap.StatusSyncService")
    def test_status_sync_service_created_when_task_manager_configured(
        self,
        mock_sync_service_class: MagicMock,
        mock_config_loader: MagicMock,
        mock_task_manager: MagicMock,
        mock_task_info: TaskInfo,
        mock_config_with_labels: TaskManagerConfig,
    ) -> None:
        """StatusSyncService is instantiated when task_manager is provided.

        This is a critical business logic test - StatusSyncService must be
        created for phase comment posting to work (ISS-033 fix).
        """
        from adw.cli.bootstrap import create_orchestrator
        from adw.models.config import ProjectConfig

        # Configure mock config loader to return config with task manager
        mock_project_config = MagicMock(spec=ProjectConfig)
        mock_project_config.worktree = None
        mock_project_config.git = None
        mock_project_config.task_manager = mock_config_with_labels
        mock_config_loader.return_value.load.return_value = mock_project_config

        # Create orchestrator with task manager
        with patch("adw.cli.bootstrap.Orchestrator"):
            create_orchestrator(
                task_manager=mock_task_manager,
                task_info=mock_task_info,
            )

        # Verify StatusSyncService was created with correct arguments (ISS-039: now includes task_info)
        mock_sync_service_class.assert_called_once_with(
            mock_task_manager,
            mock_config_with_labels,
            task_info=mock_task_info,
        )

    @patch("adw.cli.bootstrap.ConfigLoader")
    @patch("adw.cli.bootstrap.StatusSyncService")
    def test_status_sync_service_none_without_task_manager(
        self,
        mock_sync_service_class: MagicMock,
        mock_config_loader: MagicMock,
    ) -> None:
        """StatusSyncService is None when no task_manager is configured.

        Verifies StatusSyncService is not created when task_manager=None.
        """
        from adw.cli.bootstrap import create_orchestrator
        from adw.exceptions import ConfigError

        # Configure mock config loader to raise ConfigError (normal case for no config)
        mock_config_loader.return_value.load.side_effect = ConfigError(
            code="NO_CONFIG", message="No config"
        )

        # Create orchestrator without task manager
        with patch("adw.cli.bootstrap.Orchestrator"):
            create_orchestrator()

        # Verify StatusSyncService was NOT created (no task_manager provided)
        mock_sync_service_class.assert_not_called()

    @patch("adw.cli.bootstrap.ConfigLoader")
    @patch("adw.cli.bootstrap.LabelManager")
    def test_label_manager_receives_internal_uuid(
        self,
        mock_label_manager_class: MagicMock,
        mock_config_loader: MagicMock,
        mock_task_manager: MagicMock,
        mock_task_info: TaskInfo,
        mock_config_with_labels: TaskManagerConfig,
    ) -> None:
        """LabelManager is created with task_info.id (UUID), not identifier.

        This is the critical fix for ISS-033 - the Linear API requires
        internal UUID for label operations, not the public identifier.
        """
        from adw.cli.bootstrap import create_orchestrator
        from adw.models.config import ProjectConfig

        # Ensure task_info has distinct id and identifier
        assert mock_task_info.id == "internal-uuid-123-456-789"
        assert mock_task_info.identifier == "RULE-151"

        # Configure mock config loader
        mock_project_config = MagicMock(spec=ProjectConfig)
        mock_project_config.worktree = None
        mock_project_config.git = None
        mock_project_config.task_manager = mock_config_with_labels
        mock_config_loader.return_value.load.return_value = mock_project_config

        # Create orchestrator with task_info
        with (
            patch("adw.cli.bootstrap.Orchestrator"),
            patch("adw.cli.bootstrap.StatusSyncService"),
        ):
            create_orchestrator(
                task_manager=mock_task_manager,
                task_info=mock_task_info,  # Contains internal UUID
            )

        # Verify LabelManager was created with internal UUID, NOT identifier
        mock_label_manager_class.assert_called_once_with(
            mock_task_manager,
            mock_config_with_labels.labels,
            "internal-uuid-123-456-789",  # Should be task_info.id
        )

    @patch("adw.cli.bootstrap.ConfigLoader")
    @patch("adw.cli.bootstrap.LabelManager")
    def test_label_manager_not_created_without_task_info(
        self,
        mock_label_manager_class: MagicMock,
        mock_config_loader: MagicMock,
        mock_task_manager: MagicMock,
        mock_config_with_labels: TaskManagerConfig,
    ) -> None:
        """LabelManager is None when task_info is not available.

        Even with task_manager and task_id, LabelManager requires task_info
        to get the internal UUID. This is intentional (ISS-033).
        """
        from adw.cli.bootstrap import create_orchestrator
        from adw.models.config import ProjectConfig

        # Configure mock config loader
        mock_project_config = MagicMock(spec=ProjectConfig)
        mock_project_config.worktree = None
        mock_project_config.git = None
        mock_project_config.task_manager = mock_config_with_labels
        mock_config_loader.return_value.load.return_value = mock_project_config

        # Create orchestrator with task_manager but WITHOUT task_info
        with (
            patch("adw.cli.bootstrap.Orchestrator"),
            patch("adw.cli.bootstrap.StatusSyncService"),
        ):
            create_orchestrator(
                task_manager=mock_task_manager,
                task_info=None,  # No task_info
            )

        # Verify LabelManager was NOT created
        mock_label_manager_class.assert_not_called()

    @patch("adw.cli.bootstrap.ConfigLoader")
    @patch("adw.cli.bootstrap.LabelManager")
    def test_label_manager_not_created_when_labels_disabled(
        self,
        mock_label_manager_class: MagicMock,
        mock_config_loader: MagicMock,
        mock_task_manager: MagicMock,
        mock_task_info: TaskInfo,
        mock_config_without_labels: TaskManagerConfig,
    ) -> None:
        """LabelManager is not created when labels.enabled=False."""
        from adw.cli.bootstrap import create_orchestrator
        from adw.models.config import ProjectConfig

        # Configure mock config loader with labels disabled
        mock_project_config = MagicMock(spec=ProjectConfig)
        mock_project_config.worktree = None
        mock_project_config.git = None
        mock_project_config.task_manager = mock_config_without_labels
        mock_config_loader.return_value.load.return_value = mock_project_config

        # Create orchestrator with labels disabled
        with (
            patch("adw.cli.bootstrap.Orchestrator"),
            patch("adw.cli.bootstrap.StatusSyncService"),
        ):
            create_orchestrator(
                task_manager=mock_task_manager,
                task_info=mock_task_info,
            )

        # Verify LabelManager was NOT created (labels disabled)
        mock_label_manager_class.assert_not_called()
