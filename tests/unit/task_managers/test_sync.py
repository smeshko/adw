"""Tests for StatusSyncService (Story 12.3).

Tests verify that status synchronization works correctly with task managers,
handles phase transitions, and provides non-blocking error handling.
"""

from datetime import datetime
from unittest.mock import MagicMock

import pytest

from adw.models import RunContext, TaskManagerConfig
from adw.models.task import TaskInfo
from adw.task_managers.sync import DEFAULT_STATE_MAPPING, StatusSyncService


class TestStatusSyncService:
    """Tests for StatusSyncService core functionality."""

    @pytest.fixture
    def mock_task_manager(self) -> MagicMock:
        """Create a mock task manager."""
        manager = MagicMock()
        manager.name = "linear"
        manager.update_status = MagicMock()
        return manager

    @pytest.fixture
    def config(self) -> TaskManagerConfig:
        """Create a task manager config with default state mapping."""
        return TaskManagerConfig(
            type="linear",
            team_key="RULE",
        )

    @pytest.fixture
    def context_with_task(self) -> RunContext:
        """Create a RunContext with task information."""
        return RunContext(
            run_id="01KDSG2VDHNK0W4HSCZWJZXWSQ",
            feature_description="Test feature",
            current_phase="plan",
            started_at=datetime.now(),
            task_id="RULE-123",
            task_info=TaskInfo(
                id="uuid-123",
                identifier="RULE-123",
                title="Test task",
            ),
            task_manager="linear",
        )

    @pytest.fixture
    def context_without_task(self) -> RunContext:
        """Create a RunContext without task information."""
        return RunContext(
            run_id="01KDSG2VDHNK0W4HSCZWJZXWSQ",
            feature_description="Test feature",
            current_phase="plan",
            started_at=datetime.now(),
        )

    def test_sync_phase_start_updates_status(
        self,
        mock_task_manager: MagicMock,
        config: TaskManagerConfig,
        context_with_task: RunContext,
    ) -> None:
        """Calls update_status with mapped phase status on phase start."""
        service = StatusSyncService(mock_task_manager, config)
        service.sync_phase_start(context_with_task, "plan")

        mock_task_manager.update_status.assert_called_once()
        call_args = mock_task_manager.update_status.call_args
        assert call_args[0][0] == "uuid-123"  # task_id (internal UUID)
        assert call_args[0][1] == "In Progress"  # mapped status

    def test_sync_phase_start_skipped_without_task_id(
        self,
        mock_task_manager: MagicMock,
        config: TaskManagerConfig,
        context_without_task: RunContext,
    ) -> None:
        """Does nothing when context has no task_id."""
        service = StatusSyncService(mock_task_manager, config)
        service.sync_phase_start(context_without_task, "plan")

        mock_task_manager.update_status.assert_not_called()

    def test_sync_phase_transition(
        self,
        mock_task_manager: MagicMock,
        config: TaskManagerConfig,
        context_with_task: RunContext,
    ) -> None:
        """Calls update_status with next phase mapping on transition."""
        service = StatusSyncService(mock_task_manager, config)
        service.sync_phase_transition(context_with_task, "plan", "build")

        mock_task_manager.update_status.assert_called_once()
        call_args = mock_task_manager.update_status.call_args
        assert call_args[0][0] == "uuid-123"
        assert call_args[0][1] == "In Progress"  # build maps to In Progress

    def test_sync_phase_transition_to_validate(
        self,
        mock_task_manager: MagicMock,
        config: TaskManagerConfig,
        context_with_task: RunContext,
    ) -> None:
        """Validate phase maps to In Review status."""
        service = StatusSyncService(mock_task_manager, config)
        service.sync_phase_transition(context_with_task, "build", "validate")

        call_args = mock_task_manager.update_status.call_args
        assert call_args[0][1] == "In Review"

    def test_sync_run_failed_updates_to_failed_status(
        self,
        mock_task_manager: MagicMock,
        config: TaskManagerConfig,
        context_with_task: RunContext,
    ) -> None:
        """Updates to 'failed' mapped state on run failure."""
        service = StatusSyncService(mock_task_manager, config)
        service.sync_run_failed(context_with_task, "build", "Test error")

        mock_task_manager.update_status.assert_called_once()
        call_args = mock_task_manager.update_status.call_args
        assert call_args[0][0] == "uuid-123"
        assert call_args[0][1] == "In Progress"  # failed maps to In Progress

    def test_sync_run_complete_does_not_change_status(
        self,
        mock_task_manager: MagicMock,
        config: TaskManagerConfig,
        context_with_task: RunContext,
    ) -> None:
        """Run completion does not update status (closing handled by 12.8)."""
        service = StatusSyncService(mock_task_manager, config)
        service.sync_run_complete(context_with_task, success=True)

        # sync_run_complete should NOT update status - that's for 12.8
        mock_task_manager.update_status.assert_not_called()


class TestPhaseStatusMapping:
    """Tests for default phase-to-status mapping."""

    def test_default_mapping_plan_to_in_progress(self) -> None:
        """'plan' phase maps to 'In Progress' by default."""
        assert DEFAULT_STATE_MAPPING["plan"] == "In Progress"

    def test_default_mapping_build_to_in_progress(self) -> None:
        """'build' phase maps to 'In Progress' by default."""
        assert DEFAULT_STATE_MAPPING["build"] == "In Progress"

    def test_default_mapping_validate_to_in_review(self) -> None:
        """'validate' phase maps to 'In Review' by default."""
        assert DEFAULT_STATE_MAPPING["validate"] == "In Review"

    def test_default_mapping_document_to_in_review(self) -> None:
        """'document' phase maps to 'In Review' by default."""
        assert DEFAULT_STATE_MAPPING["document"] == "In Review"

    def test_default_mapping_failed_to_in_progress(self) -> None:
        """'failed' state maps to 'In Progress' by default."""
        assert DEFAULT_STATE_MAPPING["failed"] == "In Progress"


class TestStatusSyncServiceCustomMapping:
    """Tests for custom state mapping configuration."""

    @pytest.fixture
    def mock_task_manager(self) -> MagicMock:
        """Create a mock task manager."""
        manager = MagicMock()
        manager.name = "linear"
        return manager

    @pytest.fixture
    def custom_config(self) -> TaskManagerConfig:
        """Create config with custom state mapping."""
        return TaskManagerConfig(
            type="linear",
            team_key="RULE",
            state_mapping={
                "plan": "Planning",
                "build": "In Development",
                "validate": "QA Review",
                "document": "Documentation",
                "failed": "Blocked",
            },
        )

    @pytest.fixture
    def context_with_task(self) -> RunContext:
        """Create a RunContext with task information."""
        return RunContext(
            run_id="01KDSG2VDHNK0W4HSCZWJZXWSQ",
            feature_description="Test feature",
            current_phase="plan",
            started_at=datetime.now(),
            task_id="RULE-123",
            task_info=TaskInfo(
                id="uuid-123",
                identifier="RULE-123",
                title="Test task",
            ),
            task_manager="linear",
        )

    def test_sync_uses_custom_state_mapping(
        self,
        mock_task_manager: MagicMock,
        custom_config: TaskManagerConfig,
        context_with_task: RunContext,
    ) -> None:
        """Uses custom mapping from config when provided."""
        service = StatusSyncService(mock_task_manager, custom_config)
        service.sync_phase_start(context_with_task, "plan")

        call_args = mock_task_manager.update_status.call_args
        assert call_args[0][1] == "Planning"  # Custom mapping

    def test_sync_unknown_phase_uses_phase_name(
        self,
        mock_task_manager: MagicMock,
        custom_config: TaskManagerConfig,
        context_with_task: RunContext,
    ) -> None:
        """Falls back to phase name when no mapping exists."""
        # Create config with minimal mapping
        minimal_config = TaskManagerConfig(
            type="linear",
            team_key="RULE",
            state_mapping={"plan": "Planning"},  # Only plan mapped
        )
        service = StatusSyncService(mock_task_manager, minimal_config)
        service.sync_phase_start(context_with_task, "unknown_phase")

        call_args = mock_task_manager.update_status.call_args
        assert call_args[0][1] == "unknown_phase"  # Falls back to phase name


class TestStatusSyncServiceErrorHandling:
    """Tests for non-blocking error handling."""

    @pytest.fixture
    def failing_task_manager(self) -> MagicMock:
        """Create a task manager that raises on update_status."""
        manager = MagicMock()
        manager.name = "linear"
        manager.update_status = MagicMock(side_effect=Exception("API Error"))
        return manager

    @pytest.fixture
    def config(self) -> TaskManagerConfig:
        """Create a task manager config."""
        return TaskManagerConfig(type="linear", team_key="RULE")

    @pytest.fixture
    def context_with_task(self) -> RunContext:
        """Create a RunContext with task information."""
        return RunContext(
            run_id="01KDSG2VDHNK0W4HSCZWJZXWSQ",
            feature_description="Test feature",
            current_phase="plan",
            started_at=datetime.now(),
            task_id="RULE-123",
            task_info=TaskInfo(
                id="uuid-123",
                identifier="RULE-123",
                title="Test task",
            ),
            task_manager="linear",
        )

    def test_sync_continues_on_api_error(
        self,
        failing_task_manager: MagicMock,
        config: TaskManagerConfig,
        context_with_task: RunContext,
    ) -> None:
        """Logs warning but doesn't raise on API failure."""
        service = StatusSyncService(failing_task_manager, config)

        # Should not raise
        service.sync_phase_start(context_with_task, "plan")

        # Task manager was called (and failed)
        failing_task_manager.update_status.assert_called_once()

    def test_sync_logs_error_details(
        self,
        failing_task_manager: MagicMock,
        config: TaskManagerConfig,
        context_with_task: RunContext,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Logs task_id, phase, and error message."""
        import logging

        caplog.set_level(logging.WARNING)
        service = StatusSyncService(failing_task_manager, config)
        service.sync_phase_start(context_with_task, "plan")

        assert "Failed to sync status" in caplog.text
        assert "uuid-123" in caplog.text or "API Error" in caplog.text


class TestStatusSyncServiceComments:
    """Tests for comment posting functionality (Story 12.6)."""

    @pytest.fixture
    def mock_task_manager(self) -> MagicMock:
        """Create a mock task manager with post_comment."""
        manager = MagicMock()
        manager.name = "linear"
        manager.update_status = MagicMock()
        manager.post_comment = MagicMock()
        return manager

    @pytest.fixture
    def config(self) -> TaskManagerConfig:
        """Create a task manager config with sync_comments enabled."""
        return TaskManagerConfig(type="linear", team_key="RULE", sync_comments=True)

    @pytest.fixture
    def context_with_task(self) -> RunContext:
        """Create a RunContext with task information."""
        return RunContext(
            run_id="01KDSG2VDHNK0W4HSCZWJZXWSQ",
            feature_description="Test feature",
            current_phase="plan",
            started_at=datetime.now(),
            task_id="RULE-123",
            task_info=TaskInfo(
                id="uuid-123",
                identifier="RULE-123",
                title="Test task",
            ),
            task_manager="linear",
        )

    @pytest.fixture
    def context_without_task(self) -> RunContext:
        """Create a RunContext without task information."""
        return RunContext(
            run_id="01KDSG2VDHNK0W4HSCZWJZXWSQ",
            feature_description="Test feature",
            current_phase="plan",
            started_at=datetime.now(),
        )

    def test_post_phase_comment_calls_task_manager(
        self,
        mock_task_manager: MagicMock,
        config: TaskManagerConfig,
        context_with_task: RunContext,
    ) -> None:
        """post_phase_comment calls task_manager.post_comment."""
        from datetime import timedelta

        from adw.models.phase import PhaseResult, PhaseStatus

        service = StatusSyncService(mock_task_manager, config)
        started = datetime.now()
        completed = started + timedelta(seconds=45.2)
        result = PhaseResult(
            phase="plan",
            status=PhaseStatus.COMPLETED,
            started_at=started,
            completed_at=completed,
            artifacts=["file1.md", "file2.md", "file3.md"],
        )

        service.post_phase_comment(context_with_task, "plan", result)

        mock_task_manager.post_comment.assert_called_once()
        call_args = mock_task_manager.post_comment.call_args
        assert call_args[0][0] == "uuid-123"  # task_id
        assert "plan" in call_args[0][1].lower()  # phase in body
        assert "45.20" in call_args[0][1]  # duration

    def test_post_phase_comment_skips_without_task(
        self,
        mock_task_manager: MagicMock,
        config: TaskManagerConfig,
        context_without_task: RunContext,
    ) -> None:
        """post_phase_comment is no-op without task info."""
        from adw.models.phase import PhaseResult, PhaseStatus

        service = StatusSyncService(mock_task_manager, config)
        result = PhaseResult(
            phase="plan", status=PhaseStatus.COMPLETED, started_at=datetime.now()
        )

        service.post_phase_comment(context_without_task, "plan", result)

        mock_task_manager.post_comment.assert_not_called()

    def test_post_failure_comment_includes_error(
        self,
        mock_task_manager: MagicMock,
        config: TaskManagerConfig,
        context_with_task: RunContext,
    ) -> None:
        """post_failure_comment includes error message."""
        service = StatusSyncService(mock_task_manager, config)

        service.post_failure_comment(
            context_with_task, "build", "Build failed: missing dep"
        )

        mock_task_manager.post_comment.assert_called_once()
        call_args = mock_task_manager.post_comment.call_args
        assert call_args[0][0] == "uuid-123"
        assert "build" in call_args[0][1].lower()
        assert "missing dep" in call_args[0][1]

    def test_post_completion_comment_includes_pr_url(
        self,
        mock_task_manager: MagicMock,
        config: TaskManagerConfig,
        context_with_task: RunContext,
    ) -> None:
        """post_completion_comment includes PR URL when provided."""
        service = StatusSyncService(mock_task_manager, config)

        service.post_completion_comment(
            context_with_task,
            pr_url="https://github.com/org/repo/pull/42",
            summary="All tests passed",
        )

        mock_task_manager.post_comment.assert_called_once()
        call_args = mock_task_manager.post_comment.call_args
        assert call_args[0][0] == "uuid-123"
        assert "https://github.com/org/repo/pull/42" in call_args[0][1]

    def test_post_completion_comment_without_pr_url(
        self,
        mock_task_manager: MagicMock,
        config: TaskManagerConfig,
        context_with_task: RunContext,
    ) -> None:
        """post_completion_comment works without PR URL."""
        service = StatusSyncService(mock_task_manager, config)

        service.post_completion_comment(
            context_with_task,
            pr_url=None,
            summary="Completed",
        )

        mock_task_manager.post_comment.assert_called_once()
        call_args = mock_task_manager.post_comment.call_args
        assert "01KDSG2VDHNK0W4HSCZWJZXWSQ" in call_args[0][1]  # run_id

    def test_safe_post_comment_handles_errors(
        self,
        context_with_task: RunContext,
    ) -> None:
        """_safe_post_comment catches exceptions and logs warning."""
        failing_manager = MagicMock()
        failing_manager.post_comment = MagicMock(side_effect=Exception("API Error"))

        # Need sync_comments=True to test comment posting error handling
        config_with_comments = TaskManagerConfig(
            type="linear", team_key="RULE", sync_comments=True
        )
        service = StatusSyncService(failing_manager, config_with_comments)

        # Should not raise
        service.post_completion_comment(context_with_task, summary="Test")

    def test_comments_not_posted_when_sync_comments_false(
        self,
        mock_task_manager: MagicMock,
        context_with_task: RunContext,
    ) -> None:
        """Comments are not posted when sync_comments is False."""
        config_no_comments = TaskManagerConfig(
            type="linear", team_key="RULE", sync_comments=False
        )
        service = StatusSyncService(mock_task_manager, config_no_comments)

        service.post_completion_comment(context_with_task, summary="Test")

        mock_task_manager.post_comment.assert_not_called()

    def test_success_comments_skipped_when_comment_on_failure_only(
        self,
        mock_task_manager: MagicMock,
        context_with_task: RunContext,
    ) -> None:
        """Success comments are skipped when comment_on_failure_only is True."""
        config_failure_only = TaskManagerConfig(
            type="linear",
            team_key="RULE",
            sync_comments=True,
            comment_on_failure_only=True,
        )
        service = StatusSyncService(mock_task_manager, config_failure_only)

        # Success comments should be skipped
        service.post_completion_comment(context_with_task, summary="Test")
        mock_task_manager.post_comment.assert_not_called()

    def test_failure_comments_posted_even_with_comment_on_failure_only(
        self,
        mock_task_manager: MagicMock,
        context_with_task: RunContext,
    ) -> None:
        """Failure comments are still posted when comment_on_failure_only is True."""
        config_failure_only = TaskManagerConfig(
            type="linear",
            team_key="RULE",
            sync_comments=True,
            comment_on_failure_only=True,
        )
        service = StatusSyncService(mock_task_manager, config_failure_only)

        # Failure comments should be posted
        service.post_failure_comment(context_with_task, "build", "Error")
        mock_task_manager.post_comment.assert_called_once()
