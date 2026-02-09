"""Tests for the RunLifecycle class.

This module tests the run lifecycle management for ADW pipeline execution,
including context creation, success finalization, and error handling.
"""

from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from adw.core.run_lifecycle import RunLifecycle
from adw.exceptions import PhaseError, WorktreeError
from adw.models import GitConfig, RunContext, WorktreeConfig


@pytest.fixture
def mock_context_manager() -> MagicMock:
    """Create a mock ContextManager."""
    manager = MagicMock()
    manager.save = MagicMock()
    return manager


@pytest.fixture
def mock_run_directory_manager(tmp_path: Path) -> MagicMock:
    """Create a mock RunDirectoryManager."""
    manager = MagicMock()
    run_dir = tmp_path / "runs" / "01TEST00000000000000000001"
    run_dir.mkdir(parents=True)
    manager.create = MagicMock(return_value=run_dir)
    return manager


@pytest.fixture
def mock_index_manager() -> MagicMock:
    """Create a mock IndexManager."""
    manager = MagicMock()
    manager.register_run = MagicMock()
    manager.update_run = MagicMock()
    return manager


@pytest.fixture
def mock_interruption_handler() -> MagicMock:
    """Create a mock InterruptionHandler."""
    handler = MagicMock()
    handler.shutdown_requested = False
    return handler


@pytest.fixture
def mock_progress_display() -> MagicMock:
    """Create a mock ProgressDisplay."""
    display = MagicMock()
    display.console = MagicMock()
    display.console.print = MagicMock()
    display.show_pipeline_summary = MagicMock()
    return display


@pytest.fixture
def mock_label_manager() -> MagicMock:
    """Create a mock LabelManager."""
    manager = MagicMock()
    manager.set_running = MagicMock()
    manager.set_completed = MagicMock()
    manager.set_failed = MagicMock()
    return manager


@pytest.fixture
def mock_status_sync_service() -> MagicMock:
    """Create a mock StatusSyncService."""
    service = MagicMock()
    service.sync_run_failed = MagicMock()
    service.post_failure_comment = MagicMock()
    service.post_completion_comment = MagicMock()
    return service


@pytest.fixture
def run_lifecycle(
    tmp_path: Path,
    mock_context_manager: MagicMock,
    mock_run_directory_manager: MagicMock,
    mock_index_manager: MagicMock,
    mock_interruption_handler: MagicMock,
) -> RunLifecycle:
    """Create a RunLifecycle instance with mocked dependencies."""
    runs_dir = tmp_path / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)
    project_path = tmp_path

    return RunLifecycle(
        runs_dir=runs_dir,
        project_path=project_path,
        context_manager=mock_context_manager,
        run_directory_manager=mock_run_directory_manager,
        index_manager=mock_index_manager,
        interruption_handler=mock_interruption_handler,
        worktree_config=WorktreeConfig(enabled=False),
    )


class TestRunLifecycleInit:
    """Tests for RunLifecycle initialization."""

    def test_init_stores_dependencies(
        self,
        tmp_path: Path,
        mock_context_manager: MagicMock,
        mock_run_directory_manager: MagicMock,
        mock_index_manager: MagicMock,
        mock_interruption_handler: MagicMock,
    ) -> None:
        """Test that __init__ stores all dependencies."""
        runs_dir = tmp_path / "runs"
        project_path = tmp_path

        lifecycle = RunLifecycle(
            runs_dir=runs_dir,
            project_path=project_path,
            context_manager=mock_context_manager,
            run_directory_manager=mock_run_directory_manager,
            index_manager=mock_index_manager,
            interruption_handler=mock_interruption_handler,
        )

        assert lifecycle.runs_dir == runs_dir
        assert lifecycle.project_path == project_path
        assert lifecycle.context_manager is mock_context_manager
        assert lifecycle.run_directory_manager is mock_run_directory_manager
        assert lifecycle.index_manager is mock_index_manager
        assert lifecycle.interruption_handler is mock_interruption_handler

    def test_init_default_configs(
        self,
        tmp_path: Path,
        mock_context_manager: MagicMock,
        mock_run_directory_manager: MagicMock,
        mock_index_manager: MagicMock,
        mock_interruption_handler: MagicMock,
    ) -> None:
        """Test that default configs are created."""
        lifecycle = RunLifecycle(
            runs_dir=tmp_path,
            project_path=tmp_path,
            context_manager=mock_context_manager,
            run_directory_manager=mock_run_directory_manager,
            index_manager=mock_index_manager,
            interruption_handler=mock_interruption_handler,
        )

        assert lifecycle.worktree_config is not None
        assert lifecycle.git_config is not None
        assert lifecycle.task_manager_config is not None

    def test_init_with_optional_managers(
        self,
        tmp_path: Path,
        mock_context_manager: MagicMock,
        mock_run_directory_manager: MagicMock,
        mock_index_manager: MagicMock,
        mock_interruption_handler: MagicMock,
        mock_label_manager: MagicMock,
        mock_status_sync_service: MagicMock,
        mock_progress_display: MagicMock,
    ) -> None:
        """Test that optional managers are stored."""
        lifecycle = RunLifecycle(
            runs_dir=tmp_path,
            project_path=tmp_path,
            context_manager=mock_context_manager,
            run_directory_manager=mock_run_directory_manager,
            index_manager=mock_index_manager,
            interruption_handler=mock_interruption_handler,
            progress_display=mock_progress_display,
            label_manager=mock_label_manager,
            status_sync_service=mock_status_sync_service,
        )

        assert lifecycle.progress_display is mock_progress_display
        assert lifecycle._label_manager is mock_label_manager
        assert lifecycle._status_sync_service is mock_status_sync_service


class TestCreateRunContext:
    """Tests for create_run_context method."""

    def test_creates_context_with_default_values(
        self,
        run_lifecycle: RunLifecycle,
        mock_context_manager: MagicMock,
        mock_run_directory_manager: MagicMock,
        mock_index_manager: MagicMock,
    ) -> None:
        """Test that context is created with proper defaults."""
        context = run_lifecycle.create_run_context(
            feature_description="Add user auth",
        )

        assert context.feature_description == "Add user auth"
        assert context.current_phase == "plan"
        assert context.status == "running"
        assert context.run_id is not None
        assert len(context.run_id) == 26  # ULID length

    def test_creates_context_with_custom_run_id(
        self,
        run_lifecycle: RunLifecycle,
    ) -> None:
        """Test that custom run_id is used."""
        context = run_lifecycle.create_run_context(
            feature_description="Add user auth",
            run_id="01HQTEST123456789012345678",
        )

        assert context.run_id == "01HQTEST123456789012345678"

    def test_creates_context_with_custom_starting_phase(
        self,
        run_lifecycle: RunLifecycle,
    ) -> None:
        """Test that custom starting_phase is used."""
        context = run_lifecycle.create_run_context(
            feature_description="Add user auth",
            starting_phase="build",
        )

        assert context.current_phase == "build"

    def test_initializes_run_directory(
        self,
        run_lifecycle: RunLifecycle,
        mock_run_directory_manager: MagicMock,
    ) -> None:
        """Test that run directory is created."""
        run_lifecycle.create_run_context(
            feature_description="Add user auth",
        )

        mock_run_directory_manager.create.assert_called_once()

    def test_persists_initial_state(
        self,
        run_lifecycle: RunLifecycle,
        mock_context_manager: MagicMock,
    ) -> None:
        """Test that initial state is persisted."""
        run_lifecycle.create_run_context(
            feature_description="Add user auth",
        )

        mock_context_manager.save.assert_called_once()

    def test_registers_run_in_index(
        self,
        run_lifecycle: RunLifecycle,
        mock_index_manager: MagicMock,
    ) -> None:
        """Test that run is registered in index."""
        run_lifecycle.create_run_context(
            feature_description="Add user auth",
        )

        mock_index_manager.register_run.assert_called_once()

    def test_sets_running_label_when_label_manager_present(
        self,
        tmp_path: Path,
        mock_context_manager: MagicMock,
        mock_run_directory_manager: MagicMock,
        mock_index_manager: MagicMock,
        mock_interruption_handler: MagicMock,
        mock_label_manager: MagicMock,
    ) -> None:
        """Test that running label is set when label_manager is present."""
        lifecycle = RunLifecycle(
            runs_dir=tmp_path,
            project_path=tmp_path,
            context_manager=mock_context_manager,
            run_directory_manager=mock_run_directory_manager,
            index_manager=mock_index_manager,
            interruption_handler=mock_interruption_handler,
            label_manager=mock_label_manager,
            worktree_config=WorktreeConfig(enabled=False),
        )

        lifecycle.create_run_context(feature_description="Add user auth")

        mock_label_manager.set_running.assert_called_once()


class TestInitializeRunPostsStartedComment:
    """Tests for run started comment in _initialize_run."""

    def test_posts_run_started_comment_when_sync_service_present(
        self,
        tmp_path: Path,
        mock_context_manager: MagicMock,
        mock_run_directory_manager: MagicMock,
        mock_index_manager: MagicMock,
        mock_interruption_handler: MagicMock,
        mock_status_sync_service: MagicMock,
    ) -> None:
        """_initialize_run calls post_run_started_comment on sync service."""
        lifecycle = RunLifecycle(
            runs_dir=tmp_path,
            project_path=tmp_path,
            context_manager=mock_context_manager,
            run_directory_manager=mock_run_directory_manager,
            index_manager=mock_index_manager,
            interruption_handler=mock_interruption_handler,
            status_sync_service=mock_status_sync_service,
            worktree_config=WorktreeConfig(enabled=False),
        )

        lifecycle.create_run_context(feature_description="Add user auth")

        mock_status_sync_service.post_run_started_comment.assert_called_once()

    def test_run_started_comment_is_non_blocking(
        self,
        tmp_path: Path,
        mock_context_manager: MagicMock,
        mock_run_directory_manager: MagicMock,
        mock_index_manager: MagicMock,
        mock_interruption_handler: MagicMock,
    ) -> None:
        """_initialize_run does not fail if post_run_started_comment raises."""
        failing_sync = MagicMock()
        failing_sync.post_run_started_comment = MagicMock(
            side_effect=Exception("Network error")
        )

        lifecycle = RunLifecycle(
            runs_dir=tmp_path,
            project_path=tmp_path,
            context_manager=mock_context_manager,
            run_directory_manager=mock_run_directory_manager,
            index_manager=mock_index_manager,
            interruption_handler=mock_interruption_handler,
            status_sync_service=failing_sync,
            worktree_config=WorktreeConfig(enabled=False),
        )

        # Should not raise
        context = lifecycle.create_run_context(feature_description="Add user auth")
        assert context.status == "running"

    def test_no_run_started_comment_without_sync_service(
        self,
        run_lifecycle: RunLifecycle,
    ) -> None:
        """_initialize_run does not call post_run_started_comment when no sync service."""
        # run_lifecycle fixture has no status_sync_service — should not error
        context = run_lifecycle.create_run_context(feature_description="Add user auth")
        assert context.status == "running"


class TestPrepareResumeContext:
    """Tests for prepare_resume_context method."""

    def test_sets_running_label(
        self,
        tmp_path: Path,
        mock_context_manager: MagicMock,
        mock_run_directory_manager: MagicMock,
        mock_index_manager: MagicMock,
        mock_interruption_handler: MagicMock,
        mock_label_manager: MagicMock,
    ) -> None:
        """Test that running label is set when resuming."""
        lifecycle = RunLifecycle(
            runs_dir=tmp_path,
            project_path=tmp_path,
            context_manager=mock_context_manager,
            run_directory_manager=mock_run_directory_manager,
            index_manager=mock_index_manager,
            interruption_handler=mock_interruption_handler,
            label_manager=mock_label_manager,
            worktree_config=WorktreeConfig(enabled=False),
        )

        context = RunContext(
            run_id="01TEST00000000000000000001",
            feature_description="Test",
            current_phase="build",
            started_at=datetime.now(UTC),
            status="failed",
        )

        result = lifecycle.prepare_resume_context(context)

        mock_label_manager.set_running.assert_called_once()
        assert result is context


class TestFinalizeSuccess:
    """Tests for finalize_success method."""

    def test_updates_status_to_completed(
        self,
        run_lifecycle: RunLifecycle,
        mock_context_manager: MagicMock,
    ) -> None:
        """Test that status is updated to completed."""
        context = RunContext(
            run_id="01TEST00000000000000000001",
            feature_description="Test",
            current_phase="document",
            started_at=datetime.now(UTC),
            status="running",
            phase_history=["plan", "build", "validate", "document"],
        )

        result = run_lifecycle.finalize_success(context)

        assert result.status == "completed"
        assert result.completed_at is not None

    def test_persists_completed_state(
        self,
        run_lifecycle: RunLifecycle,
        mock_context_manager: MagicMock,
    ) -> None:
        """Test that completed state is persisted."""
        context = RunContext(
            run_id="01TEST00000000000000000001",
            feature_description="Test",
            current_phase="document",
            started_at=datetime.now(UTC),
            status="running",
        )

        run_lifecycle.finalize_success(context)

        mock_context_manager.save.assert_called_once()

    def test_sets_completed_label(
        self,
        tmp_path: Path,
        mock_context_manager: MagicMock,
        mock_run_directory_manager: MagicMock,
        mock_index_manager: MagicMock,
        mock_interruption_handler: MagicMock,
        mock_label_manager: MagicMock,
    ) -> None:
        """Test that completed label is set."""
        lifecycle = RunLifecycle(
            runs_dir=tmp_path,
            project_path=tmp_path,
            context_manager=mock_context_manager,
            run_directory_manager=mock_run_directory_manager,
            index_manager=mock_index_manager,
            interruption_handler=mock_interruption_handler,
            label_manager=mock_label_manager,
            worktree_config=WorktreeConfig(enabled=False),
        )

        context = RunContext(
            run_id="01TEST00000000000000000001",
            feature_description="Test",
            current_phase="document",
            started_at=datetime.now(UTC),
            status="running",
        )

        lifecycle.finalize_success(context)

        mock_label_manager.set_completed.assert_called_once()

    def test_updates_index(
        self,
        run_lifecycle: RunLifecycle,
        mock_index_manager: MagicMock,
    ) -> None:
        """Test that global index is updated."""
        context = RunContext(
            run_id="01TEST00000000000000000001",
            feature_description="Test",
            current_phase="document",
            started_at=datetime.now(UTC),
            status="running",
        )

        run_lifecycle.finalize_success(context)

        mock_index_manager.update_run.assert_called_once()
        call_kwargs = mock_index_manager.update_run.call_args[1]
        assert call_kwargs["status"] == "completed"

    def test_posts_completion_comment(
        self,
        tmp_path: Path,
        mock_context_manager: MagicMock,
        mock_run_directory_manager: MagicMock,
        mock_index_manager: MagicMock,
        mock_interruption_handler: MagicMock,
        mock_status_sync_service: MagicMock,
    ) -> None:
        """Test that completion comment is posted."""
        lifecycle = RunLifecycle(
            runs_dir=tmp_path,
            project_path=tmp_path,
            context_manager=mock_context_manager,
            run_directory_manager=mock_run_directory_manager,
            index_manager=mock_index_manager,
            interruption_handler=mock_interruption_handler,
            status_sync_service=mock_status_sync_service,
            worktree_config=WorktreeConfig(enabled=False),
        )

        context = RunContext(
            run_id="01TEST00000000000000000001",
            feature_description="Test",
            current_phase="document",
            started_at=datetime.now(UTC),
            status="running",
        )

        lifecycle.finalize_success(context)

        mock_status_sync_service.post_completion_comment.assert_called_once()

    def test_shows_pipeline_summary(
        self,
        tmp_path: Path,
        mock_context_manager: MagicMock,
        mock_run_directory_manager: MagicMock,
        mock_index_manager: MagicMock,
        mock_interruption_handler: MagicMock,
        mock_progress_display: MagicMock,
    ) -> None:
        """Test that pipeline summary is shown."""
        lifecycle = RunLifecycle(
            runs_dir=tmp_path,
            project_path=tmp_path,
            context_manager=mock_context_manager,
            run_directory_manager=mock_run_directory_manager,
            index_manager=mock_index_manager,
            interruption_handler=mock_interruption_handler,
            progress_display=mock_progress_display,
            worktree_config=WorktreeConfig(enabled=False),
        )

        context = RunContext(
            run_id="01TEST00000000000000000001",
            feature_description="Test",
            current_phase="document",
            started_at=datetime.now(UTC),
            status="running",
        )

        lifecycle.finalize_success(context)

        mock_progress_display.show_pipeline_summary.assert_called_once()


class TestHandleADWError:
    """Tests for handle_adw_error method."""

    def test_updates_status_to_failed(
        self,
        run_lifecycle: RunLifecycle,
        mock_context_manager: MagicMock,
    ) -> None:
        """Test that status is updated to failed."""
        context = RunContext(
            run_id="01TEST00000000000000000001",
            feature_description="Test",
            current_phase="build",
            started_at=datetime.now(UTC),
            status="running",
        )

        error = PhaseError(
            code="TEST_ERROR",
            message="Test error",
            phase="build",
        )

        result = run_lifecycle.handle_adw_error(context, error)

        assert result.status == "failed"
        assert result.completed_at is not None

    def test_sets_failed_label(
        self,
        tmp_path: Path,
        mock_context_manager: MagicMock,
        mock_run_directory_manager: MagicMock,
        mock_index_manager: MagicMock,
        mock_interruption_handler: MagicMock,
        mock_label_manager: MagicMock,
    ) -> None:
        """Test that failed label is set."""
        lifecycle = RunLifecycle(
            runs_dir=tmp_path,
            project_path=tmp_path,
            context_manager=mock_context_manager,
            run_directory_manager=mock_run_directory_manager,
            index_manager=mock_index_manager,
            interruption_handler=mock_interruption_handler,
            label_manager=mock_label_manager,
            worktree_config=WorktreeConfig(enabled=False),
        )

        context = RunContext(
            run_id="01TEST00000000000000000001",
            feature_description="Test",
            current_phase="build",
            started_at=datetime.now(UTC),
            status="running",
        )

        error = PhaseError(code="TEST_ERROR", message="Test error", phase="build")
        lifecycle.handle_adw_error(context, error)

        mock_label_manager.set_failed.assert_called_once()

    def test_syncs_failure_status(
        self,
        tmp_path: Path,
        mock_context_manager: MagicMock,
        mock_run_directory_manager: MagicMock,
        mock_index_manager: MagicMock,
        mock_interruption_handler: MagicMock,
        mock_status_sync_service: MagicMock,
    ) -> None:
        """Test that failure status is synced."""
        lifecycle = RunLifecycle(
            runs_dir=tmp_path,
            project_path=tmp_path,
            context_manager=mock_context_manager,
            run_directory_manager=mock_run_directory_manager,
            index_manager=mock_index_manager,
            interruption_handler=mock_interruption_handler,
            status_sync_service=mock_status_sync_service,
            worktree_config=WorktreeConfig(enabled=False),
        )

        context = RunContext(
            run_id="01TEST00000000000000000001",
            feature_description="Test",
            current_phase="build",
            started_at=datetime.now(UTC),
            status="running",
        )

        error = PhaseError(code="TEST_ERROR", message="Test error", phase="build")
        lifecycle.handle_adw_error(context, error)

        mock_status_sync_service.sync_run_failed.assert_called_once()
        mock_status_sync_service.post_failure_comment.assert_called_once()

    def test_updates_index_on_failure(
        self,
        run_lifecycle: RunLifecycle,
        mock_index_manager: MagicMock,
    ) -> None:
        """Test that global index is updated on failure."""
        context = RunContext(
            run_id="01TEST00000000000000000001",
            feature_description="Test",
            current_phase="build",
            started_at=datetime.now(UTC),
            status="running",
        )

        error = PhaseError(code="TEST_ERROR", message="Test error", phase="build")
        run_lifecycle.handle_adw_error(context, error)

        mock_index_manager.update_run.assert_called_once()
        call_kwargs = mock_index_manager.update_run.call_args[1]
        assert call_kwargs["status"] == "failed"


class TestHandleException:
    """Tests for handle_exception method."""

    def test_handles_generic_exception(
        self,
        run_lifecycle: RunLifecycle,
        mock_context_manager: MagicMock,
    ) -> None:
        """Test that generic exceptions are handled."""
        context = RunContext(
            run_id="01TEST00000000000000000001",
            feature_description="Test",
            current_phase="build",
            started_at=datetime.now(UTC),
            status="running",
        )

        error = RuntimeError("Unexpected error")

        result = run_lifecycle.handle_exception(context, error)

        assert result.status == "failed"
        assert result.completed_at is not None


class TestHandleShutdown:
    """Tests for handle_shutdown method."""

    def test_sets_failed_label_on_shutdown(
        self,
        tmp_path: Path,
        mock_context_manager: MagicMock,
        mock_run_directory_manager: MagicMock,
        mock_index_manager: MagicMock,
        mock_interruption_handler: MagicMock,
        mock_label_manager: MagicMock,
    ) -> None:
        """Test that failed label is set on shutdown."""
        from adw.core.interruption import ShutdownRequested

        lifecycle = RunLifecycle(
            runs_dir=tmp_path,
            project_path=tmp_path,
            context_manager=mock_context_manager,
            run_directory_manager=mock_run_directory_manager,
            index_manager=mock_index_manager,
            interruption_handler=mock_interruption_handler,
            label_manager=mock_label_manager,
            worktree_config=WorktreeConfig(enabled=False),
        )

        context = RunContext(
            run_id="01TEST00000000000000000001",
            feature_description="Test",
            current_phase="build",
            started_at=datetime.now(UTC),
            status="running",
        )

        error = ShutdownRequested(phase="build")
        lifecycle.handle_shutdown(context, error)

        mock_label_manager.set_failed.assert_called_once()

    def test_updates_index_on_shutdown(
        self,
        run_lifecycle: RunLifecycle,
        mock_index_manager: MagicMock,
    ) -> None:
        """Test that global index is updated on shutdown."""
        from adw.core.interruption import ShutdownRequested

        context = RunContext(
            run_id="01TEST00000000000000000001",
            feature_description="Test",
            current_phase="build",
            started_at=datetime.now(UTC),
            status="running",
        )

        error = ShutdownRequested(phase="build")
        run_lifecycle.handle_shutdown(context, error)

        mock_index_manager.update_run.assert_called_once()
        call_kwargs = mock_index_manager.update_run.call_args[1]
        assert call_kwargs["status"] == "interrupted"


class TestShowWorktreePreserved:
    """Tests for _show_worktree_preserved method."""

    def test_shows_message_for_worktree_run(
        self,
        tmp_path: Path,
        mock_context_manager: MagicMock,
        mock_run_directory_manager: MagicMock,
        mock_index_manager: MagicMock,
        mock_interruption_handler: MagicMock,
        mock_progress_display: MagicMock,
    ) -> None:
        """Test that worktree message is shown."""
        lifecycle = RunLifecycle(
            runs_dir=tmp_path,
            project_path=tmp_path,
            context_manager=mock_context_manager,
            run_directory_manager=mock_run_directory_manager,
            index_manager=mock_index_manager,
            interruption_handler=mock_interruption_handler,
            progress_display=mock_progress_display,
            worktree_config=WorktreeConfig(enabled=False),
        )

        worktree_path = tmp_path / "worktree"
        context = RunContext(
            run_id="01TEST00000000000000000001",
            feature_description="Test",
            current_phase="build",
            started_at=datetime.now(UTC),
            status="running",
            use_worktree=True,
            worktree_path=worktree_path,
        )

        lifecycle._show_worktree_preserved(context, outcome="success")

        # Check that console.print was called (multiple times for the message)
        assert mock_progress_display.console.print.call_count >= 3

    def test_skips_message_for_non_worktree_run(
        self,
        tmp_path: Path,
        mock_context_manager: MagicMock,
        mock_run_directory_manager: MagicMock,
        mock_index_manager: MagicMock,
        mock_interruption_handler: MagicMock,
        mock_progress_display: MagicMock,
    ) -> None:
        """Test that worktree message is skipped for non-worktree runs."""
        lifecycle = RunLifecycle(
            runs_dir=tmp_path,
            project_path=tmp_path,
            context_manager=mock_context_manager,
            run_directory_manager=mock_run_directory_manager,
            index_manager=mock_index_manager,
            interruption_handler=mock_interruption_handler,
            progress_display=mock_progress_display,
            worktree_config=WorktreeConfig(enabled=False),
        )

        context = RunContext(
            run_id="01TEST00000000000000000001",
            feature_description="Test",
            current_phase="build",
            started_at=datetime.now(UTC),
            status="running",
            use_worktree=False,
        )

        lifecycle._show_worktree_preserved(context, outcome="success")

        # console.print should not be called
        mock_progress_display.console.print.assert_not_called()


class TestRunContextTaskInfoPopulation:
    """Tests for ISS-039: RunContext task_id and task_info population."""

    def test_context_created_with_task_info_populated(
        self,
        tmp_path: Path,
        mock_context_manager: MagicMock,
        mock_run_directory_manager: MagicMock,
        mock_index_manager: MagicMock,
        mock_interruption_handler: MagicMock,
    ) -> None:
        """RunContext is created with task_id and task_info from RunLifecycle."""
        from adw.models.task import TaskInfo

        task_info = TaskInfo(
            id="uuid-lifecycle-123",
            identifier="RULE-789",
            title="Test task from lifecycle",
        )

        lifecycle = RunLifecycle(
            runs_dir=tmp_path,
            project_path=tmp_path,
            context_manager=mock_context_manager,
            run_directory_manager=mock_run_directory_manager,
            index_manager=mock_index_manager,
            interruption_handler=mock_interruption_handler,
            worktree_config=WorktreeConfig(enabled=False),
            task_info=task_info,  # ISS-039: pass task_info to lifecycle
        )

        context = lifecycle.create_run_context(
            feature_description="Test feature",
            use_worktree=False,
        )

        # Verify task_id and task_info are populated
        assert context.task_id == "RULE-789"  # Should be task_info.identifier
        assert context.task_info is not None
        assert context.task_info.id == "uuid-lifecycle-123"
        assert context.task_info.identifier == "RULE-789"

    def test_context_created_without_task_info_when_not_provided(
        self,
        tmp_path: Path,
        mock_context_manager: MagicMock,
        mock_run_directory_manager: MagicMock,
        mock_index_manager: MagicMock,
        mock_interruption_handler: MagicMock,
    ) -> None:
        """RunContext has None for task_id/task_info when not provided."""
        lifecycle = RunLifecycle(
            runs_dir=tmp_path,
            project_path=tmp_path,
            context_manager=mock_context_manager,
            run_directory_manager=mock_run_directory_manager,
            index_manager=mock_index_manager,
            interruption_handler=mock_interruption_handler,
            worktree_config=WorktreeConfig(enabled=False),
            # No task_info provided
        )

        context = lifecycle.create_run_context(
            feature_description="Test feature",
            use_worktree=False,
        )

        # Verify task_id and task_info are None
        assert context.task_id is None
        assert context.task_info is None


class TestFetchBaseBranch:
    """Tests for _fetch_base_branch method."""

    def test_fetch_succeeds_returns_remote_ref(
        self,
        tmp_path: Path,
        mock_context_manager: MagicMock,
        mock_run_directory_manager: MagicMock,
        mock_index_manager: MagicMock,
        mock_interruption_handler: MagicMock,
    ) -> None:
        """Successful fetch returns origin/<branch> ref."""
        lifecycle = RunLifecycle(
            runs_dir=tmp_path,
            project_path=tmp_path,
            context_manager=mock_context_manager,
            run_directory_manager=mock_run_directory_manager,
            index_manager=mock_index_manager,
            interruption_handler=mock_interruption_handler,
        )

        with patch("adw.core.run_lifecycle.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stderr="")
            result = lifecycle._fetch_base_branch()

        assert result == "origin/staging"
        mock_run.assert_called_once_with(
            ["git", "fetch", "origin", "staging"],
            cwd=tmp_path,
            capture_output=True,
            text=True,
            check=False,
        )

    def test_fetch_uses_configured_base_branch(
        self,
        tmp_path: Path,
        mock_context_manager: MagicMock,
        mock_run_directory_manager: MagicMock,
        mock_index_manager: MagicMock,
        mock_interruption_handler: MagicMock,
    ) -> None:
        """Uses git.base_branch from config when set."""
        lifecycle = RunLifecycle(
            runs_dir=tmp_path,
            project_path=tmp_path,
            context_manager=mock_context_manager,
            run_directory_manager=mock_run_directory_manager,
            index_manager=mock_index_manager,
            interruption_handler=mock_interruption_handler,
            git_config=GitConfig(base_branch="main"),
        )

        with patch("adw.core.run_lifecycle.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stderr="")
            result = lifecycle._fetch_base_branch()

        assert result == "origin/main"
        mock_run.assert_called_once_with(
            ["git", "fetch", "origin", "main"],
            cwd=tmp_path,
            capture_output=True,
            text=True,
            check=False,
        )

    def test_fetch_falls_back_to_staging_when_base_branch_none(
        self,
        tmp_path: Path,
        mock_context_manager: MagicMock,
        mock_run_directory_manager: MagicMock,
        mock_index_manager: MagicMock,
        mock_interruption_handler: MagicMock,
    ) -> None:
        """Falls back to 'staging' when git.base_branch is None."""
        lifecycle = RunLifecycle(
            runs_dir=tmp_path,
            project_path=tmp_path,
            context_manager=mock_context_manager,
            run_directory_manager=mock_run_directory_manager,
            index_manager=mock_index_manager,
            interruption_handler=mock_interruption_handler,
            git_config=GitConfig(base_branch=None),
        )

        with patch("adw.core.run_lifecycle.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stderr="")
            result = lifecycle._fetch_base_branch()

        assert result == "origin/staging"

    def test_fetch_failure_raises_worktree_error(
        self,
        tmp_path: Path,
        mock_context_manager: MagicMock,
        mock_run_directory_manager: MagicMock,
        mock_index_manager: MagicMock,
        mock_interruption_handler: MagicMock,
    ) -> None:
        """Raises WorktreeError with GIT_FETCH_FAILED on fetch failure."""
        lifecycle = RunLifecycle(
            runs_dir=tmp_path,
            project_path=tmp_path,
            context_manager=mock_context_manager,
            run_directory_manager=mock_run_directory_manager,
            index_manager=mock_index_manager,
            interruption_handler=mock_interruption_handler,
        )

        with patch("adw.core.run_lifecycle.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=128, stderr="fatal: could not read from remote"
            )

            with pytest.raises(WorktreeError) as exc_info:
                lifecycle._fetch_base_branch()

        assert exc_info.value.code == "GIT_FETCH_FAILED"
        assert "staging" in exc_info.value.message
        assert "could not read from remote" in exc_info.value.message

    def test_fetch_failure_includes_suggestion(
        self,
        tmp_path: Path,
        mock_context_manager: MagicMock,
        mock_run_directory_manager: MagicMock,
        mock_index_manager: MagicMock,
        mock_interruption_handler: MagicMock,
    ) -> None:
        """WorktreeError from fetch failure includes actionable suggestion."""
        lifecycle = RunLifecycle(
            runs_dir=tmp_path,
            project_path=tmp_path,
            context_manager=mock_context_manager,
            run_directory_manager=mock_run_directory_manager,
            index_manager=mock_index_manager,
            interruption_handler=mock_interruption_handler,
        )

        with patch("adw.core.run_lifecycle.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=1, stderr="Connection refused"
            )

            with pytest.raises(WorktreeError) as exc_info:
                lifecycle._fetch_base_branch()

        assert exc_info.value.suggestion is not None
        assert "git remote -v" in exc_info.value.suggestion


class TestCreateWorktreeForRunFetch:
    """Tests for _create_worktree_for_run with fetch integration."""

    def test_passes_source_branch_to_create_worktree(
        self,
        tmp_path: Path,
        mock_context_manager: MagicMock,
        mock_run_directory_manager: MagicMock,
        mock_index_manager: MagicMock,
        mock_interruption_handler: MagicMock,
    ) -> None:
        """_create_worktree_for_run passes source_branch from fetch to create_worktree."""
        mock_worktree_manager = MagicMock()
        mock_worktree_manager.create_worktree.return_value = (
            tmp_path / "trees" / "RUN123",
            "adw/RUN123",
        )

        lifecycle = RunLifecycle(
            runs_dir=tmp_path,
            project_path=tmp_path,
            context_manager=mock_context_manager,
            run_directory_manager=mock_run_directory_manager,
            index_manager=mock_index_manager,
            interruption_handler=mock_interruption_handler,
            worktree_config=WorktreeConfig(enabled=True),
            worktree_manager=mock_worktree_manager,
        )

        with patch("adw.core.run_lifecycle.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stderr="")
            lifecycle._create_worktree_for_run("RUN123", "test feature")

        mock_worktree_manager.create_worktree.assert_called_once_with(
            "RUN123", source_branch="origin/staging", branch_name="feature/test-feature"
        )

    def test_passes_configured_base_branch_as_source(
        self,
        tmp_path: Path,
        mock_context_manager: MagicMock,
        mock_run_directory_manager: MagicMock,
        mock_index_manager: MagicMock,
        mock_interruption_handler: MagicMock,
    ) -> None:
        """source_branch uses configured base_branch."""
        mock_worktree_manager = MagicMock()
        mock_worktree_manager.create_worktree.return_value = (
            tmp_path / "trees" / "RUN123",
            "adw/RUN123",
        )

        lifecycle = RunLifecycle(
            runs_dir=tmp_path,
            project_path=tmp_path,
            context_manager=mock_context_manager,
            run_directory_manager=mock_run_directory_manager,
            index_manager=mock_index_manager,
            interruption_handler=mock_interruption_handler,
            worktree_config=WorktreeConfig(enabled=True),
            git_config=GitConfig(base_branch="develop"),
            worktree_manager=mock_worktree_manager,
        )

        with patch("adw.core.run_lifecycle.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stderr="")
            lifecycle._create_worktree_for_run("RUN123", "test feature")

        call_kwargs = mock_worktree_manager.create_worktree.call_args
        assert call_kwargs[1]["source_branch"] == "origin/develop"

    def test_fetch_failure_propagates_as_worktree_error(
        self,
        tmp_path: Path,
        mock_context_manager: MagicMock,
        mock_run_directory_manager: MagicMock,
        mock_index_manager: MagicMock,
        mock_interruption_handler: MagicMock,
    ) -> None:
        """Fetch failure raises WorktreeError before worktree creation."""
        mock_worktree_manager = MagicMock()

        lifecycle = RunLifecycle(
            runs_dir=tmp_path,
            project_path=tmp_path,
            context_manager=mock_context_manager,
            run_directory_manager=mock_run_directory_manager,
            index_manager=mock_index_manager,
            interruption_handler=mock_interruption_handler,
            worktree_config=WorktreeConfig(enabled=True),
            worktree_manager=mock_worktree_manager,
        )

        with patch("adw.core.run_lifecycle.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=128, stderr="fatal: no remote"
            )

            with pytest.raises(WorktreeError) as exc_info:
                lifecycle._create_worktree_for_run("RUN123", "test feature")

        assert exc_info.value.code == "GIT_FETCH_FAILED"
        # create_worktree should NOT have been called
        mock_worktree_manager.create_worktree.assert_not_called()
