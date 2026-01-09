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

    def test_fetch_task_invalid_response_raises_error(
        self, manager: LinearTaskManager
    ) -> None:
        """fetch_task raises TaskError when API response is missing required fields."""
        # Missing title field
        mock_issue = {
            "id": "abc123",
            "identifier": "RULE-999",
            "title": None,  # Missing required field
        }

        with patch.object(manager, "_client") as mock_client:
            mock_client.fetch_issue.return_value = mock_issue

            with pytest.raises(TaskError) as exc_info:
                manager.fetch_task("RULE-999")

        assert exc_info.value.code == "TASK_INVALID_RESPONSE"
        assert "missing required fields" in exc_info.value.message.lower()


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


class TestLinearTaskManagerResolveTaskId:
    """Tests for LinearTaskManager.resolve_task_id."""

    @pytest.fixture
    def manager(self, monkeypatch: pytest.MonkeyPatch) -> LinearTaskManager:
        """Create a LinearTaskManager with mocked env vars."""
        monkeypatch.setenv("LINEAR_API_KEY", "lin_api_test123")
        monkeypatch.setenv("LINEAR_TEAM_ID", "team-uuid-123")
        config = TaskManagerConfig(type="linear", team_key="RULE")
        return LinearTaskManager(config)

    def test_resolve_direct_task_id(self, manager: LinearTaskManager) -> None:
        """resolve_task_id extracts direct task IDs."""
        assert manager.resolve_task_id("RULE-123") == "RULE-123"
        assert manager.resolve_task_id("RULE-1") == "RULE-1"
        assert manager.resolve_task_id("RULE-99999") == "RULE-99999"

    def test_resolve_case_insensitive(self, manager: LinearTaskManager) -> None:
        """resolve_task_id is case insensitive but normalizes to uppercase."""
        assert manager.resolve_task_id("rule-123") == "RULE-123"
        assert manager.resolve_task_id("Rule-456") == "RULE-456"
        assert manager.resolve_task_id("RuLe-789") == "RULE-789"

    def test_resolve_from_branch_name(self, manager: LinearTaskManager) -> None:
        """resolve_task_id extracts task ID from branch names."""
        assert manager.resolve_task_id("feature/RULE-123-add-auth") == "RULE-123"
        assert manager.resolve_task_id("fix/RULE-456") == "RULE-456"
        assert manager.resolve_task_id("story/RULE-789-implement-feature") == "RULE-789"

    def test_resolve_from_linear_url(self, manager: LinearTaskManager) -> None:
        """resolve_task_id extracts task ID from Linear URLs."""
        url = "https://linear.app/team/issue/RULE-123/some-slug"
        assert manager.resolve_task_id(url) == "RULE-123"

    def test_resolve_from_free_text(self, manager: LinearTaskManager) -> None:
        """resolve_task_id extracts task ID from free text."""
        assert manager.resolve_task_id("Working on RULE-123") == "RULE-123"
        assert manager.resolve_task_id("Fix for RULE-456 in progress") == "RULE-456"

    def test_resolve_returns_none_for_no_match(
        self, manager: LinearTaskManager
    ) -> None:
        """resolve_task_id returns None when no task ID found."""
        assert manager.resolve_task_id("no task here") is None
        assert manager.resolve_task_id("OTHER-123") is None
        assert manager.resolve_task_id("RULE-") is None
        assert manager.resolve_task_id("") is None

    def test_resolve_returns_first_match(self, manager: LinearTaskManager) -> None:
        """resolve_task_id returns first match when multiple present."""
        assert manager.resolve_task_id("RULE-123 and RULE-456") == "RULE-123"

    def test_resolve_no_team_key_returns_none(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """resolve_task_id returns None when team_key not configured."""
        monkeypatch.setenv("LINEAR_API_KEY", "lin_api_test123")
        monkeypatch.setenv("LINEAR_TEAM_ID", "team-uuid-123")
        config = TaskManagerConfig(type="linear", team_key=None)
        manager = LinearTaskManager(config)

        assert manager.resolve_task_id("RULE-123") is None


class TestLinearTaskManagerCloseTask:
    """Tests for LinearTaskManager.close_task."""

    @pytest.fixture
    def manager(self, monkeypatch: pytest.MonkeyPatch) -> LinearTaskManager:
        """Create a LinearTaskManager with mocked env vars."""
        monkeypatch.setenv("LINEAR_API_KEY", "lin_api_test123")
        monkeypatch.setenv("LINEAR_TEAM_ID", "team-uuid-123")
        config = TaskManagerConfig(
            type="linear",
            team_key="RULE",
            state_mapping={
                "done": "Done",
                "completed": "Done",
            },
        )
        return LinearTaskManager(config)

    def test_close_task_finds_done_state_and_updates(
        self, manager: LinearTaskManager
    ) -> None:
        """close_task finds Done state and updates issue with completedAt."""
        mock_states = [
            {"id": "state-1", "name": "Todo", "type": "started"},
            {"id": "state-2", "name": "In Progress", "type": "started"},
            {"id": "state-3", "name": "Done", "type": "completed"},
        ]

        with patch.object(manager, "_client") as mock_client:
            mock_client.get_team_states.return_value = mock_states
            mock_client.update_issue.return_value = {"success": True}

            manager.close_task("task-uuid-123")

            # Should call update_issue with Done state ID and completedAt
            mock_client.update_issue.assert_called_once()
            call_args = mock_client.update_issue.call_args
            assert call_args[0][0] == "task-uuid-123"
            assert call_args[0][1]["stateId"] == "state-3"
            assert "completedAt" in call_args[0][1]

    def test_close_task_uses_custom_state_mapping(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """close_task uses custom state mapping from config."""
        monkeypatch.setenv("LINEAR_API_KEY", "lin_api_test123")
        monkeypatch.setenv("LINEAR_TEAM_ID", "team-uuid-123")
        config = TaskManagerConfig(
            type="linear",
            team_key="RULE",
            state_mapping={"done": "Finished"},  # Custom state name
        )
        manager = LinearTaskManager(config)

        mock_states = [
            {"id": "state-1", "name": "Todo", "type": "started"},
            {"id": "state-2", "name": "Finished", "type": "completed"},
        ]

        with patch.object(manager, "_client") as mock_client:
            mock_client.get_team_states.return_value = mock_states
            mock_client.update_issue.return_value = {"success": True}

            manager.close_task("task-uuid-123")

            # Should use "Finished" state from custom mapping
            call_args = mock_client.update_issue.call_args
            assert call_args[0][1]["stateId"] == "state-2"

    def test_close_task_raises_error_when_done_state_not_found(
        self, manager: LinearTaskManager
    ) -> None:
        """close_task raises TaskError when Done state not found."""
        mock_states = [
            {"id": "state-1", "name": "Todo", "type": "started"},
            {"id": "state-2", "name": "In Progress", "type": "started"},
            # No Done/Completed state
        ]

        with patch.object(manager, "_client") as mock_client:
            mock_client.get_team_states.return_value = mock_states

            with pytest.raises(TaskError) as exc_info:
                manager.close_task("task-uuid-123")

            assert exc_info.value.code == "DONE_STATE_NOT_FOUND"


class TestLinearTaskManagerIsPrMerged:
    """Tests for LinearTaskManager.is_pr_merged."""

    def test_is_pr_merged_returns_false(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """is_pr_merged always returns False (handled by IssueCloser)."""
        monkeypatch.setenv("LINEAR_API_KEY", "lin_api_test123")
        monkeypatch.setenv("LINEAR_TEAM_ID", "team-uuid-123")
        config = TaskManagerConfig(type="linear", team_key="RULE")
        manager = LinearTaskManager(config)

        # Linear doesn't track PR status natively
        assert manager.is_pr_merged("https://github.com/owner/repo/pull/123") is False
        assert manager.is_pr_merged("any-url") is False


class TestLinearTaskManagerProtocol:
    """Tests for LinearTaskManager Protocol satisfaction."""

    def test_linear_manager_satisfies_task_manager_protocol(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """LinearTaskManager satisfies TaskManager Protocol."""
        from adw.task_managers.base import TaskManager

        monkeypatch.setenv("LINEAR_API_KEY", "lin_api_test123")
        monkeypatch.setenv("LINEAR_TEAM_ID", "team-uuid-123")

        config = TaskManagerConfig(type="linear", team_key="RULE")
        manager = LinearTaskManager(config)

        # isinstance check with runtime_checkable Protocol
        assert isinstance(manager, TaskManager)

        # Verify all protocol methods exist
        assert hasattr(manager, "name")
        assert hasattr(manager, "fetch_task")
        assert hasattr(manager, "update_status")
        assert hasattr(manager, "resolve_task_id")
        assert hasattr(manager, "close_task")
        assert hasattr(manager, "is_pr_merged")
