"""Tests for StatusSyncService (Story 12.3).

Tests verify that status synchronization works correctly with task managers,
handles phase transitions, and provides non-blocking error handling.
"""

from datetime import UTC, datetime, timedelta
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
            started_at=datetime.now(UTC),
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
        from adw.models.phase import PhaseResult, PhaseStatus

        service = StatusSyncService(mock_task_manager, config)
        started = datetime.now(UTC)
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

    def test_post_phase_comment_includes_enriched_data(
        self,
        mock_task_manager: MagicMock,
        config: TaskManagerConfig,
        context_with_task: RunContext,
    ) -> None:
        """post_phase_comment passes artifact names, tokens, tool calls."""
        from adw.models.llm import ToolCall
        from adw.models.phase import PhaseResult, PhaseStatus

        service = StatusSyncService(mock_task_manager, config)
        started = datetime.now(UTC)
        completed = started + timedelta(seconds=60)
        result = PhaseResult(
            phase="build",
            status=PhaseStatus.COMPLETED,
            started_at=started,
            completed_at=completed,
            artifacts=["src/main.py", "tests/test_main.py"],
            tokens_used=12000,
            tool_calls=[
                ToolCall(tool_name="write_file", arguments={"path": "src/main.py"}),
                ToolCall(tool_name="write_file", arguments={"path": "tests/test_main.py"}),
            ],
        )

        service.post_phase_comment(context_with_task, "build", result)

        body = mock_task_manager.post_comment.call_args[0][1]
        assert "`src/main.py`" in body
        assert "`tests/test_main.py`" in body
        assert "12,000" in body
        assert "2" in body  # 2 tool calls

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

    def test_post_failure_comment_includes_enriched_data(
        self,
        mock_task_manager: MagicMock,
        config: TaskManagerConfig,
    ) -> None:
        """post_failure_comment includes phase timeline and branch info."""
        context = RunContext(
            run_id="01KDSG2VDHNK0W4HSCZWJZXWSQ",
            feature_description="Test feature",
            current_phase="build",
            started_at=datetime.now(UTC) - timedelta(seconds=120),
            task_id="RULE-123",
            task_info=TaskInfo(
                id="uuid-123",
                identifier="RULE-123",
                title="Test task",
            ),
            task_manager="linear",
            phase_history=["plan"],
            branch_name="adw/feature-test",
            artifacts={"plan": ["plan.md"]},
        )

        service = StatusSyncService(mock_task_manager, config)
        service.post_failure_comment(context, "build", "Error occurred")

        body = mock_task_manager.post_comment.call_args[0][1]
        assert "plan ✓" in body
        assert "build ✗" in body
        assert "`adw/feature-test`" in body
        assert "`plan.md`" in body

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

    def test_post_completion_comment_includes_enriched_data(
        self,
        mock_task_manager: MagicMock,
        config: TaskManagerConfig,
    ) -> None:
        """post_completion_comment includes timeline, tokens, commits, artifacts."""
        started = datetime.now(UTC) - timedelta(seconds=300)
        completed = datetime.now(UTC)
        context = RunContext(
            run_id="01KDSG2VDHNK0W4HSCZWJZXWSQ",
            feature_description="Test feature",
            current_phase="ship",
            started_at=started,
            completed_at=completed,
            task_id="RULE-123",
            task_info=TaskInfo(
                id="uuid-123",
                identifier="RULE-123",
                title="Test task",
            ),
            task_manager="linear",
            phase_history=["plan", "build", "validate", "document", "ship"],
            phase_tokens={"plan": 10000, "build": 30000, "validate": 5000},
            commit_shas=["abc123", "def456"],
            artifacts={"plan": ["plan.md"], "build": ["src/app.py"]},
        )

        service = StatusSyncService(mock_task_manager, config)
        service.post_completion_comment(
            context,
            pr_url="https://github.com/org/repo/pull/99",
            summary="All done",
        )

        body = mock_task_manager.post_comment.call_args[0][1]
        assert "plan ✓" in body
        assert "ship ✓" in body
        assert "45,000" in body  # total_tokens = 10000 + 30000 + 5000
        assert "2" in body  # 2 commits
        assert "`plan.md`" in body
        assert "`src/app.py`" in body

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

class TestStatusSyncServiceRunStartedComment:
    """Tests for post_run_started_comment."""

    @pytest.fixture
    def mock_task_manager(self) -> MagicMock:
        """Create a mock task manager."""
        manager = MagicMock()
        manager.name = "linear"
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
            started_at=datetime.now(UTC),
            branch_name="adw/feature-test",
            task_id="RULE-123",
            task_info=TaskInfo(
                id="uuid-123",
                identifier="RULE-123",
                title="Test task",
                assignee="developer@example.com",
            ),
            task_manager="linear",
        )

    def test_post_run_started_comment_posts(
        self,
        mock_task_manager: MagicMock,
        config: TaskManagerConfig,
        context_with_task: RunContext,
    ) -> None:
        """post_run_started_comment posts a comment with run details."""
        service = StatusSyncService(mock_task_manager, config)
        service.post_run_started_comment(context_with_task)

        mock_task_manager.post_comment.assert_called_once()
        body = mock_task_manager.post_comment.call_args[0][1]
        assert "▶ ADW Run Started" in body
        assert "01KDSG2VDHNK0W4HSCZWJZXWSQ" in body
        assert "`adw/feature-test`" in body
        assert "plan" in body  # pipeline visualization

    def test_post_run_started_comment_includes_assignee(
        self,
        mock_task_manager: MagicMock,
        config: TaskManagerConfig,
        context_with_task: RunContext,
    ) -> None:
        """post_run_started_comment includes assignee in comment."""
        service = StatusSyncService(mock_task_manager, config)
        service.post_run_started_comment(context_with_task)

        body = mock_task_manager.post_comment.call_args[0][1]
        assert "developer@example.com" in body

    def test_post_run_started_skipped_without_task(
        self,
        mock_task_manager: MagicMock,
        config: TaskManagerConfig,
    ) -> None:
        """post_run_started_comment is no-op without task info."""
        context = RunContext(
            run_id="01KDSG2VDHNK0W4HSCZWJZXWSQ",
            feature_description="Test",
            current_phase="plan",
            started_at=datetime.now(UTC),
        )
        service = StatusSyncService(mock_task_manager, config)
        service.post_run_started_comment(context)

        mock_task_manager.post_comment.assert_not_called()

    def test_post_run_started_skipped_when_sync_comments_false(
        self,
        mock_task_manager: MagicMock,
        context_with_task: RunContext,
    ) -> None:
        """post_run_started_comment is no-op when sync_comments is False."""
        config = TaskManagerConfig(
            type="linear", team_key="RULE", sync_comments=False
        )
        service = StatusSyncService(mock_task_manager, config)
        service.post_run_started_comment(context_with_task)

        mock_task_manager.post_comment.assert_not_called()

class TestStatusSyncServiceTaskInfo:
    """Tests for ISS-039: StatusSyncService task_info storage and usage."""

    @pytest.fixture
    def mock_task_manager(self) -> MagicMock:
        """Create a mock task manager with all necessary methods."""
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
    def task_info(self) -> TaskInfo:
        """Create a TaskInfo instance."""
        return TaskInfo(
            id="uuid-stored-123",
            identifier="RULE-151",
            title="Test task from constructor",
        )

    @pytest.fixture
    def context_without_task(self) -> RunContext:
        """Create a RunContext WITHOUT task information."""
        return RunContext(
            run_id="01KDSG2VDHNK0W4HSCZWJZXWSQ",
            feature_description="Test feature",
            current_phase="plan",
            started_at=datetime.now(),
            # No task_id or task_info - intentionally empty
        )

    def test_stores_task_info_from_constructor(
        self,
        mock_task_manager: MagicMock,
        config: TaskManagerConfig,
        task_info: TaskInfo,
    ) -> None:
        """StatusSyncService stores task_info from constructor."""
        service = StatusSyncService(mock_task_manager, config, task_info=task_info)
        assert service._task_info is not None
        assert service._task_info == task_info
        assert service._task_info.id == "uuid-stored-123"

    def test_post_phase_comment_uses_stored_task_info(
        self,
        mock_task_manager: MagicMock,
        config: TaskManagerConfig,
        task_info: TaskInfo,
        context_without_task: RunContext,
    ) -> None:
        """post_phase_comment uses stored task_info even when context has none."""
        from adw.models.phase import PhaseResult, PhaseStatus

        # Service has stored task_info, but context does NOT
        service = StatusSyncService(mock_task_manager, config, task_info=task_info)

        # Verify context has no task info
        assert context_without_task.task_info is None
        assert context_without_task.task_id is None

        started = datetime.now()
        completed = started + timedelta(seconds=10.5)
        result = PhaseResult(
            phase="plan",
            status=PhaseStatus.COMPLETED,
            started_at=started,
            completed_at=completed,
            artifacts=["file.md"],
        )

        # Should still work because service has stored task_info
        service.post_phase_comment(context_without_task, "plan", result)

        # Verify comment was posted using STORED task_info.id
        mock_task_manager.post_comment.assert_called_once()
        call_args = mock_task_manager.post_comment.call_args
        assert call_args[0][0] == "uuid-stored-123"  # Uses stored task_info.id

    def test_sync_phase_start_uses_stored_task_info(
        self,
        mock_task_manager: MagicMock,
        config: TaskManagerConfig,
        task_info: TaskInfo,
        context_without_task: RunContext,
    ) -> None:
        """sync_phase_start uses stored task_info even when context has none."""
        service = StatusSyncService(mock_task_manager, config, task_info=task_info)

        # Context has no task info
        assert context_without_task.task_info is None

        service.sync_phase_start(context_without_task, "plan")

        # Verify update_status was called using stored task_info.id
        mock_task_manager.update_status.assert_called_once()
        call_args = mock_task_manager.update_status.call_args
        assert call_args[0][0] == "uuid-stored-123"

    def test_falls_back_to_context_task_info(
        self,
        mock_task_manager: MagicMock,
        config: TaskManagerConfig,
    ) -> None:
        """Falls back to context.task_info when no stored task_info."""
        context_with_task = RunContext(
            run_id="01KDSG2VDHNK0W4HSCZWJZXWSQ",
            feature_description="Test feature",
            current_phase="plan",
            started_at=datetime.now(),
            task_id="RULE-456",
            task_info=TaskInfo(
                id="uuid-context-456",
                identifier="RULE-456",
                title="Task from context",
            ),
        )

        # Service created WITHOUT task_info (task_info=None)
        service = StatusSyncService(mock_task_manager, config, task_info=None)

        service.sync_phase_start(context_with_task, "plan")

        # Should use context.task_info.id as fallback
        mock_task_manager.update_status.assert_called_once()
        call_args = mock_task_manager.update_status.call_args
        assert call_args[0][0] == "uuid-context-456"  # Fallback to context

    def test_methods_do_not_return_early_with_stored_task_info(
        self,
        mock_task_manager: MagicMock,
        config: TaskManagerConfig,
        task_info: TaskInfo,
        context_without_task: RunContext,
    ) -> None:
        """Methods execute fully when stored task_info is available.

        This is the key fix for ISS-039: methods should NOT return early
        when context has no task_info, as long as the service has stored task_info.
        """
        from adw.models.phase import PhaseResult, PhaseStatus

        service = StatusSyncService(mock_task_manager, config, task_info=task_info)

        # All these methods should execute (not return early) because
        # the service has stored task_info even though context has none
        started = datetime.now()
        completed = started + timedelta(seconds=5.0)
        result = PhaseResult(
            phase="plan",
            status=PhaseStatus.COMPLETED,
            started_at=started,
            completed_at=completed,
        )

        service.sync_phase_start(context_without_task, "plan")
        service.sync_phase_transition(context_without_task, "plan", "build")
        service.sync_run_failed(context_without_task, "build", "Error")
        service.post_phase_comment(context_without_task, "plan", result)
        service.post_failure_comment(context_without_task, "build", "Error")
        service.post_completion_comment(context_without_task, summary="Done")

        # Verify that all methods actually executed (called the task manager)
        assert (
            mock_task_manager.update_status.call_count == 3
        )  # start, transition, failed
        assert (
            mock_task_manager.post_comment.call_count == 3
        )  # phase, failure, completion
