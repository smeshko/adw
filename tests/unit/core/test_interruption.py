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
