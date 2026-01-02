"""Interruption handling for graceful shutdown.

This module provides the InterruptionHandler class that manages signal handlers
for SIGINT and SIGTERM, ensuring context is saved before exit.

Key features:
- Signal handler registration and restoration
- Context preservation on interrupt (NFR7)
- Snapshot creation for recovery
- Graceful shutdown flag for main loop checking
"""

from __future__ import annotations

import signal
from collections.abc import Generator
from contextlib import contextmanager
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from adw.core.context_manager import ContextManager
    from adw.core.snapshot_manager import SnapshotManager
    from adw.models import RunContext

__all__ = [
    "InterruptionHandler",
    "ShutdownRequested",
    "can_resume",
    "get_resume_phase",
    "prepare_resume",
]

# Default phase order for ADW workflow
_PHASE_ORDER: list[str] = ["plan", "build", "verify", "validate", "document"]


class ShutdownRequested(BaseException):
    """Exception raised when graceful shutdown is requested.

    Inherits from BaseException (not Exception) to ensure it's not
    accidentally caught by generic except clauses.

    Attributes:
        phase: The phase that was running when shutdown was requested.
    """

    def __init__(self, phase: str) -> None:
        """Initialize ShutdownRequested.

        Args:
            phase: The phase where shutdown was requested.
        """
        self.phase = phase
        super().__init__(f"Shutdown requested during phase: {phase}")


class InterruptionHandler:
    """Handles graceful shutdown on interruption signals.

    Ensures:
    - Current context is saved before exit (NFR7)
    - Run status is set to "interrupted"
    - Final snapshot is created

    Attributes:
        context_manager: Manager for context persistence.
        snapshot_manager: Manager for state snapshots.

    Example:
        >>> handler = InterruptionHandler(context_manager, snapshot_manager)
        >>> with handler.protected_execution(context) as ctx:
        ...     # Run phases
        ...     # If interrupted, handler saves state automatically
    """

    def __init__(
        self,
        context_manager: ContextManager,
        snapshot_manager: SnapshotManager,
    ) -> None:
        """Initialize the InterruptionHandler.

        Args:
            context_manager: Manager for context persistence.
            snapshot_manager: Manager for state snapshots.
        """
        self.context_manager = context_manager
        self.snapshot_manager = snapshot_manager
        self._shutdown_requested: bool = False
        self._original_handlers: dict[signal.Signals, Any] = {}
        self._current_context: RunContext | None = None

    @property
    def shutdown_requested(self) -> bool:
        """Check if shutdown has been requested.

        Returns:
            True if a signal has been received requesting shutdown.
        """
        return self._shutdown_requested

    def set_context(self, context: RunContext) -> None:
        """Set the current context to save on interrupt.

        Args:
            context: RunContext to save if interrupted.
        """
        self._current_context = context

    def check_shutdown(self) -> None:
        """Check if shutdown was requested and handle gracefully.

        Should be called at safe points in the main loop (e.g., between phases).
        If shutdown was requested, saves context and raises ShutdownRequested.

        Raises:
            ShutdownRequested: If shutdown was requested via signal.
        """
        if not self._shutdown_requested:
            return

        if self._current_context:
            # Update context with interruption info
            self._current_context = self._current_context.model_copy(
                update={
                    "status": "interrupted",
                    "interrupted_phase": self._current_context.current_phase,
                    "interrupted_at": datetime.now(UTC),
                }
            )

            # Save context and snapshot
            try:
                self.context_manager.save(self._current_context)
                self.snapshot_manager.create_post_phase_snapshot(
                    context=self._current_context,
                    phase=self._current_context.current_phase,
                    phase_result=None,
                )
            except Exception:
                pass  # Best effort

            raise ShutdownRequested(phase=self._current_context.current_phase)

        raise ShutdownRequested(phase="unknown")

    def install_handlers(self) -> None:
        """Install signal handlers for interruption.

        Saves original handlers for later restoration.
        Handles both SIGINT (Ctrl+C) and SIGTERM.
        """
        self._original_handlers[signal.SIGINT] = signal.signal(
            signal.SIGINT, self._handle_signal
        )
        self._original_handlers[signal.SIGTERM] = signal.signal(
            signal.SIGTERM, self._handle_signal
        )

    def restore_handlers(self) -> None:
        """Restore original signal handlers.

        Should be called when protected execution completes.
        """
        for sig, handler in self._original_handlers.items():
            signal.signal(sig, handler)
        self._original_handlers.clear()

    def _handle_signal(self, signum: int, frame: object) -> None:
        """Handle interruption signal.

        Sets shutdown flag, saves context and snapshot, then raises
        KeyboardInterrupt to unwind the call stack.

        Args:
            signum: Signal number received.
            frame: Current stack frame (unused).

        Raises:
            KeyboardInterrupt: Always raised to unwind call stack.
        """
        self._shutdown_requested = True

        if self._current_context:
            # Update context with interruption info
            self._current_context = self._current_context.model_copy(
                update={
                    "status": "interrupted",
                    "interrupted_phase": self._current_context.current_phase,
                    "interrupted_at": datetime.now(UTC),
                }
            )

            # Save context and snapshot (best effort)
            try:
                self.context_manager.save(self._current_context)
                self.snapshot_manager.create_post_phase_snapshot(
                    context=self._current_context,
                    phase=self._current_context.current_phase,
                    phase_result=None,  # Interrupted, no result
                )
            except Exception:
                pass  # Best effort on signal handler

        raise KeyboardInterrupt

    @contextmanager
    def protected_execution(
        self,
        context: RunContext,
    ) -> Generator[RunContext]:
        """Context manager for protected execution.

        Installs signal handlers and ensures state is saved on interrupt.

        Args:
            context: RunContext for this execution.

        Yields:
            The RunContext passed in.

        Example:
            >>> with handler.protected_execution(context) as ctx:
            ...     run_phases(ctx)
        """
        self.set_context(context)
        self.install_handlers()
        try:
            yield context
        finally:
            self.restore_handlers()


def get_resume_phase(context: RunContext) -> str | None:
    """Determine which phase to resume from.

    Implements NFR8 resume semantics:
    - Completed runs cannot be resumed (returns None)
    - Interrupted runs re-execute from the interrupted phase
    - Running/failed runs continue from next uncompleted phase

    Args:
        context: The run context to examine.

    Returns:
        Phase to start from, or None if run is complete or no phases remain.
    """
    if context.status == "completed":
        return None

    if context.status == "interrupted" and context.interrupted_phase:
        # Resume from interrupted phase (re-execute from beginning)
        return context.interrupted_phase

    # For running/failed, find next uncompleted phase
    completed = set(context.phase_history)
    for phase in _PHASE_ORDER:
        if phase not in completed:
            return phase

    # All phases completed
    return None


def can_resume(context: RunContext) -> bool:
    """Check if a run can be resumed.

    Args:
        context: The run context to check.

    Returns:
        True if the run can be resumed, False otherwise.
    """
    return context.status != "completed"


def prepare_resume(context: RunContext) -> RunContext:
    """Prepare a context for resumption.

    Updates the context to be ready for continued execution:
    - Sets status to "running"
    - Clears interrupted_phase and interrupted_at
    - Preserves phase_history and other state

    Args:
        context: The run context to prepare for resume.

    Returns:
        New RunContext instance ready for execution.

    Raises:
        StateError: If run is already completed and cannot be resumed.
    """
    from adw.exceptions import StateError

    if context.status == "completed":
        raise StateError(
            code="RUN_ALREADY_COMPLETE",
            message=f"Run {context.run_id} is already completed",
            suggestion="Start a new run instead",
            recoverable=False,
        )

    return context.model_copy(
        update={
            "status": "running",
            "interrupted_phase": None,
            "interrupted_at": None,
        }
    )
