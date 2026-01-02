"""Tests for interruption handling module.

Tests signal handler registration, graceful shutdown, status tracking,
and resume from interrupt functionality.
"""

import signal
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from adw.core.interruption import InterruptionHandler
from adw.models import RunContext


@pytest.fixture
def runs_dir(tmp_path: Path) -> Path:
    """Create temporary runs directory."""
    runs = tmp_path / ".adw" / "runs"
    runs.mkdir(parents=True)
    return runs


@pytest.fixture
def sample_context(runs_dir: Path) -> RunContext:
    """Create a sample RunContext for testing."""
    run_id = "01JFTEST000000000000000001"
    run_dir = runs_dir / run_id
    run_dir.mkdir(parents=True)
    (run_dir / "snapshots").mkdir()
    return RunContext(
        run_id=run_id,
        feature_description="Test feature",
        current_phase="plan",
        phase_history=[],
        started_at=datetime.now(UTC),
        status="running",
    )


@pytest.fixture
def context_manager_mock(runs_dir: Path) -> MagicMock:
    """Create mock ContextManager."""
    mock = MagicMock()
    mock.runs_dir = runs_dir
    return mock


@pytest.fixture
def snapshot_manager_mock() -> MagicMock:
    """Create mock SnapshotManager."""
    return MagicMock()


@pytest.fixture
def interruption_handler(
    context_manager_mock: MagicMock,
    snapshot_manager_mock: MagicMock,
) -> InterruptionHandler:
    """Create InterruptionHandler instance."""
    return InterruptionHandler(
        context_manager=context_manager_mock,
        snapshot_manager=snapshot_manager_mock,
    )


class TestInterruptionHandlerInit:
    """Tests for InterruptionHandler initialization."""

    def test_init_sets_managers(
        self,
        context_manager_mock: MagicMock,
        snapshot_manager_mock: MagicMock,
    ) -> None:
        """Test that __init__ stores manager references."""
        handler = InterruptionHandler(
            context_manager=context_manager_mock,
            snapshot_manager=snapshot_manager_mock,
        )
        assert handler.context_manager is context_manager_mock
        assert handler.snapshot_manager is snapshot_manager_mock

    def test_init_shutdown_not_requested(
        self,
        interruption_handler: InterruptionHandler,
    ) -> None:
        """Test that shutdown is not requested initially."""
        assert interruption_handler.shutdown_requested is False


class TestSignalHandlerRegistration:
    """Tests for signal handler registration."""

    def test_install_handlers_changes_sigint(
        self,
        interruption_handler: InterruptionHandler,
    ) -> None:
        """Test that install_handlers changes SIGINT handler."""
        original = signal.getsignal(signal.SIGINT)
        try:
            interruption_handler.install_handlers()
            current = signal.getsignal(signal.SIGINT)
            assert current != original
        finally:
            interruption_handler.restore_handlers()

    def test_install_handlers_changes_sigterm(
        self,
        interruption_handler: InterruptionHandler,
    ) -> None:
        """Test that install_handlers changes SIGTERM handler."""
        original = signal.getsignal(signal.SIGTERM)
        try:
            interruption_handler.install_handlers()
            current = signal.getsignal(signal.SIGTERM)
            assert current != original
        finally:
            interruption_handler.restore_handlers()

    def test_restore_handlers_restores_original(
        self,
        interruption_handler: InterruptionHandler,
    ) -> None:
        """Test that restore_handlers restores original handlers."""
        original_int = signal.getsignal(signal.SIGINT)
        original_term = signal.getsignal(signal.SIGTERM)

        interruption_handler.install_handlers()
        interruption_handler.restore_handlers()

        assert signal.getsignal(signal.SIGINT) == original_int
        assert signal.getsignal(signal.SIGTERM) == original_term


class TestSetContext:
    """Tests for set_context method."""

    def test_set_context_stores_context(
        self,
        interruption_handler: InterruptionHandler,
        sample_context: RunContext,
    ) -> None:
        """Test that set_context stores the context."""
        interruption_handler.set_context(sample_context)
        assert interruption_handler._current_context is sample_context


class TestHandleSignal:
    """Tests for signal handling behavior."""

    def test_handle_signal_sets_shutdown_flag(
        self,
        interruption_handler: InterruptionHandler,
        sample_context: RunContext,
    ) -> None:
        """Test that signal handler sets shutdown flag."""
        interruption_handler.set_context(sample_context)

        with pytest.raises(KeyboardInterrupt):
            interruption_handler._handle_signal(signal.SIGINT, None)

        assert interruption_handler.shutdown_requested is True

    def test_handle_signal_saves_context(
        self,
        interruption_handler: InterruptionHandler,
        sample_context: RunContext,
        context_manager_mock: MagicMock,
    ) -> None:
        """Test that signal handler saves context."""
        interruption_handler.set_context(sample_context)

        with pytest.raises(KeyboardInterrupt):
            interruption_handler._handle_signal(signal.SIGINT, None)

        context_manager_mock.save.assert_called_once()

    def test_handle_signal_updates_status_to_interrupted(
        self,
        interruption_handler: InterruptionHandler,
        sample_context: RunContext,
        context_manager_mock: MagicMock,
    ) -> None:
        """Test that signal handler updates status to interrupted."""
        interruption_handler.set_context(sample_context)

        with pytest.raises(KeyboardInterrupt):
            interruption_handler._handle_signal(signal.SIGINT, None)

        saved_context = context_manager_mock.save.call_args[0][0]
        assert saved_context.status == "interrupted"

    def test_handle_signal_sets_interrupted_phase(
        self,
        interruption_handler: InterruptionHandler,
        sample_context: RunContext,
        context_manager_mock: MagicMock,
    ) -> None:
        """Test that signal handler sets interrupted_phase."""
        interruption_handler.set_context(sample_context)

        with pytest.raises(KeyboardInterrupt):
            interruption_handler._handle_signal(signal.SIGINT, None)

        saved_context = context_manager_mock.save.call_args[0][0]
        assert saved_context.interrupted_phase == "plan"

    def test_handle_signal_sets_interrupted_at(
        self,
        interruption_handler: InterruptionHandler,
        sample_context: RunContext,
        context_manager_mock: MagicMock,
    ) -> None:
        """Test that signal handler sets interrupted_at timestamp."""
        interruption_handler.set_context(sample_context)
        before = datetime.now(UTC)

        with pytest.raises(KeyboardInterrupt):
            interruption_handler._handle_signal(signal.SIGINT, None)

        after = datetime.now(UTC)
        saved_context = context_manager_mock.save.call_args[0][0]
        assert saved_context.interrupted_at is not None
        assert before <= saved_context.interrupted_at <= after

    def test_handle_signal_creates_snapshot(
        self,
        interruption_handler: InterruptionHandler,
        sample_context: RunContext,
        snapshot_manager_mock: MagicMock,
    ) -> None:
        """Test that signal handler creates a snapshot."""
        interruption_handler.set_context(sample_context)

        with pytest.raises(KeyboardInterrupt):
            interruption_handler._handle_signal(signal.SIGINT, None)

        snapshot_manager_mock.create_post_phase_snapshot.assert_called_once()

    def test_handle_signal_without_context_still_sets_flag(
        self,
        interruption_handler: InterruptionHandler,
    ) -> None:
        """Test that handler sets flag even without context."""
        with pytest.raises(KeyboardInterrupt):
            interruption_handler._handle_signal(signal.SIGINT, None)

        assert interruption_handler.shutdown_requested is True


class TestProtectedExecution:
    """Tests for protected_execution context manager."""

    def test_protected_execution_installs_handlers(
        self,
        interruption_handler: InterruptionHandler,
        sample_context: RunContext,
    ) -> None:
        """Test that protected_execution installs handlers."""
        original = signal.getsignal(signal.SIGINT)

        with interruption_handler.protected_execution(sample_context):
            assert signal.getsignal(signal.SIGINT) != original

        # After exiting, handlers should be restored
        assert signal.getsignal(signal.SIGINT) == original

    def test_protected_execution_yields_context(
        self,
        interruption_handler: InterruptionHandler,
        sample_context: RunContext,
    ) -> None:
        """Test that protected_execution yields the context."""
        with interruption_handler.protected_execution(sample_context) as ctx:
            assert ctx is sample_context

    def test_protected_execution_restores_on_exception(
        self,
        interruption_handler: InterruptionHandler,
        sample_context: RunContext,
    ) -> None:
        """Test that handlers are restored even on exception."""
        original = signal.getsignal(signal.SIGINT)

        with (
            pytest.raises(ValueError),
            interruption_handler.protected_execution(sample_context),
        ):
            raise ValueError("test error")

        assert signal.getsignal(signal.SIGINT) == original


class TestShutdownRequested:
    """Tests for shutdown_requested property."""

    def test_shutdown_requested_false_initially(
        self,
        interruption_handler: InterruptionHandler,
    ) -> None:
        """Test shutdown_requested is False initially."""
        assert interruption_handler.shutdown_requested is False

    def test_shutdown_requested_true_after_signal(
        self,
        interruption_handler: InterruptionHandler,
        sample_context: RunContext,
    ) -> None:
        """Test shutdown_requested is True after signal."""
        interruption_handler.set_context(sample_context)

        with pytest.raises(KeyboardInterrupt):
            interruption_handler._handle_signal(signal.SIGINT, None)

        assert interruption_handler.shutdown_requested is True


class TestCheckShutdown:
    """Tests for check_shutdown method."""

    def test_check_shutdown_does_nothing_when_not_requested(
        self,
        interruption_handler: InterruptionHandler,
        sample_context: RunContext,
    ) -> None:
        """Test check_shutdown returns normally when no shutdown requested."""
        interruption_handler.set_context(sample_context)
        # Should not raise
        interruption_handler.check_shutdown()

    def test_check_shutdown_raises_when_requested(
        self,
        interruption_handler: InterruptionHandler,
        sample_context: RunContext,
    ) -> None:
        """Test check_shutdown raises ShutdownRequested when flag is set."""
        from adw.core.interruption import ShutdownRequested

        interruption_handler.set_context(sample_context)
        interruption_handler._shutdown_requested = True

        with pytest.raises(ShutdownRequested):
            interruption_handler.check_shutdown()

    def test_check_shutdown_saves_context(
        self,
        interruption_handler: InterruptionHandler,
        sample_context: RunContext,
        context_manager_mock: MagicMock,
    ) -> None:
        """Test check_shutdown saves context when shutdown requested."""
        from adw.core.interruption import ShutdownRequested

        interruption_handler.set_context(sample_context)
        interruption_handler._shutdown_requested = True

        with pytest.raises(ShutdownRequested):
            interruption_handler.check_shutdown()

        context_manager_mock.save.assert_called_once()

    def test_check_shutdown_updates_status(
        self,
        interruption_handler: InterruptionHandler,
        sample_context: RunContext,
        context_manager_mock: MagicMock,
    ) -> None:
        """Test check_shutdown updates status to interrupted."""
        from adw.core.interruption import ShutdownRequested

        interruption_handler.set_context(sample_context)
        interruption_handler._shutdown_requested = True

        with pytest.raises(ShutdownRequested):
            interruption_handler.check_shutdown()

        saved_context = context_manager_mock.save.call_args[0][0]
        assert saved_context.status == "interrupted"


class TestShutdownRequestedException:
    """Tests for ShutdownRequested exception."""

    def test_shutdown_requested_exception_message(
        self,
    ) -> None:
        """Test ShutdownRequested has correct message."""
        from adw.core.interruption import ShutdownRequested

        exc = ShutdownRequested(phase="build")
        assert exc.phase == "build"
        assert "build" in str(exc)

    def test_shutdown_requested_exception_is_base_exception(
        self,
    ) -> None:
        """Test ShutdownRequested inherits from BaseException."""
        from adw.core.interruption import ShutdownRequested

        exc = ShutdownRequested(phase="plan")
        assert isinstance(exc, BaseException)


class TestGetResumePhase:
    """Tests for get_resume_phase function."""

    def test_returns_none_for_completed_run(
        self,
        sample_context: RunContext,
    ) -> None:
        """Test that completed runs return None."""
        from adw.core.interruption import get_resume_phase

        context = sample_context.model_copy(
            update={"status": "completed"}
        )

        assert get_resume_phase(context) is None

    def test_returns_interrupted_phase_for_interrupted_run(
        self,
        sample_context: RunContext,
    ) -> None:
        """Test that interrupted runs return the interrupted phase."""
        from adw.core.interruption import get_resume_phase

        context = sample_context.model_copy(
            update={
                "status": "interrupted",
                "interrupted_phase": "build",
                "phase_history": ["plan"],
            }
        )

        assert get_resume_phase(context) == "build"

    def test_returns_next_phase_for_running(
        self,
        sample_context: RunContext,
    ) -> None:
        """Test that running context returns next uncompleted phase."""
        from adw.core.interruption import get_resume_phase

        context = sample_context.model_copy(
            update={
                "status": "running",
                "phase_history": ["plan"],
            }
        )

        # Next phase after plan is build
        assert get_resume_phase(context) == "build"

    def test_returns_next_phase_for_failed(
        self,
        sample_context: RunContext,
    ) -> None:
        """Test that failed context returns next uncompleted phase."""
        from adw.core.interruption import get_resume_phase

        context = sample_context.model_copy(
            update={
                "status": "failed",
                "phase_history": ["plan", "build"],
            }
        )

        # Next phase after build is verify
        assert get_resume_phase(context) == "verify"

    def test_returns_first_phase_when_none_completed(
        self,
        sample_context: RunContext,
    ) -> None:
        """Test that empty phase_history returns first phase."""
        from adw.core.interruption import get_resume_phase

        context = sample_context.model_copy(
            update={
                "status": "running",
                "phase_history": [],
            }
        )

        assert get_resume_phase(context) == "plan"

    def test_returns_none_when_all_phases_completed(
        self,
        sample_context: RunContext,
    ) -> None:
        """Test returns None when all phases in history."""
        from adw.core.interruption import get_resume_phase

        context = sample_context.model_copy(
            update={
                "status": "running",
                "phase_history": ["plan", "build", "verify", "validate", "document"],
            }
        )

        assert get_resume_phase(context) is None


class TestCanResume:
    """Tests for can_resume function."""

    def test_can_resume_completed_returns_false(
        self,
        sample_context: RunContext,
    ) -> None:
        """Test that completed runs cannot be resumed."""
        from adw.core.interruption import can_resume

        context = sample_context.model_copy(
            update={"status": "completed"}
        )

        assert can_resume(context) is False

    def test_can_resume_running_returns_true(
        self,
        sample_context: RunContext,
    ) -> None:
        """Test that running runs can be resumed."""
        from adw.core.interruption import can_resume

        assert can_resume(sample_context) is True

    def test_can_resume_interrupted_returns_true(
        self,
        sample_context: RunContext,
    ) -> None:
        """Test that interrupted runs can be resumed."""
        from adw.core.interruption import can_resume

        context = sample_context.model_copy(
            update={
                "status": "interrupted",
                "interrupted_phase": "build",
            }
        )

        assert can_resume(context) is True

    def test_can_resume_failed_returns_true(
        self,
        sample_context: RunContext,
    ) -> None:
        """Test that failed runs can be resumed."""
        from adw.core.interruption import can_resume

        context = sample_context.model_copy(
            update={"status": "failed"}
        )

        assert can_resume(context) is True


class TestPrepareResume:
    """Tests for prepare_resume function."""

    def test_prepare_resume_updates_status_to_running(
        self,
        sample_context: RunContext,
    ) -> None:
        """Test that prepare_resume updates status to running."""
        from adw.core.interruption import prepare_resume

        context = sample_context.model_copy(
            update={
                "status": "interrupted",
                "interrupted_phase": "build",
            }
        )

        resumed = prepare_resume(context)
        assert resumed.status == "running"

    def test_prepare_resume_clears_interrupted_phase(
        self,
        sample_context: RunContext,
    ) -> None:
        """Test that prepare_resume clears interrupted_phase."""
        from adw.core.interruption import prepare_resume

        context = sample_context.model_copy(
            update={
                "status": "interrupted",
                "interrupted_phase": "build",
            }
        )

        resumed = prepare_resume(context)
        assert resumed.interrupted_phase is None

    def test_prepare_resume_clears_interrupted_at(
        self,
        sample_context: RunContext,
    ) -> None:
        """Test that prepare_resume clears interrupted_at."""
        from datetime import UTC, datetime

        from adw.core.interruption import prepare_resume

        context = sample_context.model_copy(
            update={
                "status": "interrupted",
                "interrupted_phase": "build",
                "interrupted_at": datetime.now(UTC),
            }
        )

        resumed = prepare_resume(context)
        assert resumed.interrupted_at is None

    def test_prepare_resume_preserves_phase_history(
        self,
        sample_context: RunContext,
    ) -> None:
        """Test that prepare_resume preserves phase_history."""
        from adw.core.interruption import prepare_resume

        context = sample_context.model_copy(
            update={
                "status": "interrupted",
                "interrupted_phase": "build",
                "phase_history": ["plan"],
            }
        )

        resumed = prepare_resume(context)
        assert resumed.phase_history == ["plan"]

    def test_prepare_resume_returns_new_instance(
        self,
        sample_context: RunContext,
    ) -> None:
        """Test that prepare_resume returns a new instance."""
        from adw.core.interruption import prepare_resume

        context = sample_context.model_copy(
            update={"status": "interrupted", "interrupted_phase": "build"}
        )

        resumed = prepare_resume(context)
        assert resumed is not context

    def test_prepare_resume_works_on_failed(
        self,
        sample_context: RunContext,
    ) -> None:
        """Test that prepare_resume works on failed runs."""
        from adw.core.interruption import prepare_resume

        context = sample_context.model_copy(update={"status": "failed"})

        resumed = prepare_resume(context)
        assert resumed.status == "running"

    def test_prepare_resume_raises_on_completed(
        self,
        sample_context: RunContext,
    ) -> None:
        """Test that prepare_resume raises on completed runs."""
        from adw.core.interruption import prepare_resume
        from adw.exceptions import StateError

        context = sample_context.model_copy(update={"status": "completed"})

        with pytest.raises(StateError) as exc_info:
            prepare_resume(context)

        assert exc_info.value.code == "RUN_ALREADY_COMPLETE"
