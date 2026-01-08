"""Unit tests for LinearTaskManager.

Tests for the Linear task manager implementation.
"""

import os
from unittest.mock import MagicMock, patch

import pytest

from adw.exceptions import ConfigError, TaskError
from adw.models.config import TaskManagerConfig
from adw.models.task import TaskInfo
from adw.task_managers.linear import LinearTaskManager


class TestLinearTaskManagerInit:
    """Tests for LinearTaskManager initialization."""

    def test_init_with_valid_env_vars(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """LinearTaskManager initializes successfully with valid environment variables."""
        monkeypatch.setenv("LINEAR_API_KEY", "lin_api_test123")
        monkeypatch.setenv("LINEAR_TEAM_ID", "team-uuid-123")

        config = TaskManagerConfig(type="linear", team_key="RULE")
        manager = LinearTaskManager(config)

        assert manager.name == "linear"
        assert manager._config == config

    def test_init_missing_api_key_raises_config_error(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Raises ConfigError when LINEAR_API_KEY is not set."""
        monkeypatch.delenv("LINEAR_API_KEY", raising=False)
        monkeypatch.setenv("LINEAR_TEAM_ID", "team-uuid-123")

        config = TaskManagerConfig(type="linear", team_key="RULE")

        with pytest.raises(ConfigError) as exc_info:
            LinearTaskManager(config)

        assert exc_info.value.code == "MISSING_LINEAR_API_KEY"
        assert "LINEAR_API_KEY" in exc_info.value.message

    def test_init_missing_team_id_raises_config_error(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Raises ConfigError when LINEAR_TEAM_ID is not set."""
        monkeypatch.setenv("LINEAR_API_KEY", "lin_api_test123")
        monkeypatch.delenv("LINEAR_TEAM_ID", raising=False)

        config = TaskManagerConfig(type="linear", team_key="RULE")

        with pytest.raises(ConfigError) as exc_info:
            LinearTaskManager(config)

        assert exc_info.value.code == "MISSING_LINEAR_TEAM_ID"
        assert "LINEAR_TEAM_ID" in exc_info.value.message

    def test_name_property_returns_linear(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The name property returns 'linear'."""
        monkeypatch.setenv("LINEAR_API_KEY", "lin_api_test123")
        monkeypatch.setenv("LINEAR_TEAM_ID", "team-uuid-123")

        config = TaskManagerConfig(type="linear", team_key="RULE")
        manager = LinearTaskManager(config)

        assert manager.name == "linear"


class TestLinearTaskManagerFetchTask:
    """Tests for LinearTaskManager.fetch_task."""

    @pytest.fixture
    def manager(self, monkeypatch: pytest.MonkeyPatch) -> LinearTaskManager:
        """Create a LinearTaskManager with mocked env vars."""
        monkeypatch.setenv("LINEAR_API_KEY", "lin_api_test123")
        monkeypatch.setenv("LINEAR_TEAM_ID", "team-uuid-123")
        config = TaskManagerConfig(type="linear", team_key="RULE")
        return LinearTaskManager(config)

    def test_fetch_task_returns_task_info(self, manager: LinearTaskManager) -> None:
        """fetch_task returns TaskInfo with mapped fields."""
        mock_issue = {
            "id": "abc123",
            "identifier": "RULE-123",
            "title": "Add user authentication",
            "description": "Implement OAuth2 login flow",
            "state": {"name": "In Progress"},
            "priority": 2,
            "labels": {"nodes": [{"name": "feature"}, {"name": "auth"}]},
            "assignee": {"name": "Alex Dev"},
            "parent": {"identifier": "RULE-100", "title": "Epic: Auth System"},
        }

        with patch.object(manager, "_client") as mock_client:
            mock_client.fetch_issue.return_value = mock_issue
            result = manager.fetch_task("RULE-123")

        assert isinstance(result, TaskInfo)
        assert result.id == "abc123"
        assert result.identifier == "RULE-123"
        assert result.title == "Add user authentication"
        assert result.description == "Implement OAuth2 login flow"
        assert result.status == "In Progress"
        assert result.priority == 2
        assert result.labels == ["feature", "auth"]
        assert result.assignee == "Alex Dev"
        assert result.parent_id == "RULE-100"
        assert result.parent_title == "Epic: Auth System"

    def test_fetch_task_not_found_raises_error(self, manager: LinearTaskManager) -> None:
        """fetch_task raises TaskError when task not found."""
        with patch.object(manager, "_client") as mock_client:
            mock_client.fetch_issue.return_value = None

            with pytest.raises(TaskError) as exc_info:
                manager.fetch_task("NONEXISTENT-999")

        assert exc_info.value.code == "TASK_NOT_FOUND"
        assert "NONEXISTENT-999" in exc_info.value.message

    def test_fetch_task_with_minimal_fields(self, manager: LinearTaskManager) -> None:
        """fetch_task handles minimal issue data gracefully."""
        mock_issue = {
            "id": "abc123",
            "identifier": "RULE-456",
            "title": "Simple task",
            "description": None,
            "state": None,
            "priority": None,
            "labels": {"nodes": []},
            "assignee": None,
            "parent": None,
        }

        with patch.object(manager, "_client") as mock_client:
            mock_client.fetch_issue.return_value = mock_issue
            result = manager.fetch_task("RULE-456")

        assert result.id == "abc123"
        assert result.title == "Simple task"
        assert result.description is None
        assert result.status is None
        assert result.priority is None
        assert result.labels == []
        assert result.assignee is None
        assert result.parent_id is None

    def test_fetch_task_with_labels(self, manager: LinearTaskManager) -> None:
        """fetch_task includes labels in TaskInfo."""
        mock_issue = {
            "id": "abc123",
            "identifier": "RULE-789",
            "title": "Task with labels",
            "description": None,
            "state": None,
            "priority": None,
            "labels": {"nodes": [{"name": "bug"}, {"name": "urgent"}, {"name": "backend"}]},
            "assignee": None,
            "parent": None,
        }

        with patch.object(manager, "_client") as mock_client:
            mock_client.fetch_issue.return_value = mock_issue
            result = manager.fetch_task("RULE-789")

        assert result.labels == ["bug", "urgent", "backend"]


class TestLinearTaskManagerUpdateStatus:
    """Tests for LinearTaskManager.update_status."""

    @pytest.fixture
    def manager(self, monkeypatch: pytest.MonkeyPatch) -> LinearTaskManager:
        """Create a LinearTaskManager with mocked env vars."""
        monkeypatch.setenv("LINEAR_API_KEY", "lin_api_test123")
        monkeypatch.setenv("LINEAR_TEAM_ID", "team-uuid-123")
        config = TaskManagerConfig(
            type="linear",
            team_key="RULE",
            state_mapping={
                "pending": "Todo",
                "running": "In Progress",
                "completed": "Done",
                "failed": "In Progress",
            },
        )
        return LinearTaskManager(config)

    def test_update_status_maps_adw_status_to_linear_state(
        self, manager: LinearTaskManager
    ) -> None:
        """update_status maps ADW status to Linear state name."""
        mock_states = [
            {"id": "state-1", "name": "Todo", "type": "started"},
            {"id": "state-2", "name": "In Progress", "type": "started"},
            {"id": "state-3", "name": "Done", "type": "completed"},
        ]

        with patch.object(manager, "_client") as mock_client:
            mock_client.get_team_states.return_value = mock_states
            mock_client.update_issue.return_value = {"success": True}

            manager.update_status("abc123", "running")

            # Should call update_issue with state ID for "In Progress"
            mock_client.update_issue.assert_called_once()
            call_args = mock_client.update_issue.call_args
            assert call_args[0][1]["stateId"] == "state-2"

    def test_update_status_caches_workflow_states(
        self, manager: LinearTaskManager
    ) -> None:
        """update_status caches team workflow states."""
        mock_states = [{"id": "state-1", "name": "Done", "type": "completed"}]

        with patch.object(manager, "_client") as mock_client:
            mock_client.get_team_states.return_value = mock_states
            mock_client.update_issue.return_value = {"success": True}

            # Call twice
            manager.update_status("abc123", "completed")
            manager.update_status("abc456", "completed")

            # Should only fetch states once
            mock_client.get_team_states.assert_called_once()

    def test_update_status_unknown_state_logs_warning(
        self, manager: LinearTaskManager, caplog: pytest.LogCaptureFixture
    ) -> None:
        """update_status logs warning for unknown state, doesn't fail."""
        mock_states = [{"id": "state-1", "name": "Todo", "type": "started"}]

        with patch.object(manager, "_client") as mock_client:
            mock_client.get_team_states.return_value = mock_states

            # "running" maps to "In Progress" but it's not in mock_states
            manager.update_status("abc123", "running")

            # Should NOT call update_issue since state not found
            mock_client.update_issue.assert_not_called()

    def test_update_status_api_error_does_not_fail(
        self, manager: LinearTaskManager
    ) -> None:
        """update_status handles API errors gracefully without raising."""
        mock_states = [{"id": "state-1", "name": "Done", "type": "completed"}]

        with patch.object(manager, "_client") as mock_client:
            mock_client.get_team_states.return_value = mock_states
            mock_client.update_issue.return_value = None  # Indicates failure

            # Should NOT raise
            manager.update_status("abc123", "completed")
