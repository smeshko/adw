"""Main orchestrator for ADW pipeline execution.

This module provides the Orchestrator class that coordinates phase execution
in the fixed order: Plan → Build → Verify → Validate → Document.

Key responsibilities:
- Phase sequencing and transitions
- State persistence at boundaries
- Error handling and retry logic
- Snapshot creation for debugging
"""

import logging
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Protocol

from ulid import ULID

from adw.core.constants import PHASE_SEQUENCE
from adw.core.context_manager import ContextManager
from adw.core.interruption import InterruptionHandler, ShutdownRequested
from adw.core.run_directory import RunDirectoryManager
from adw.core.snapshot_manager import SnapshotManager
from adw.exceptions import ADWError
from adw.models import RunContext
from adw.models.phase import PhaseResult

if TYPE_CHECKING:
    from adw.cli.progress import ProgressDisplay
    from adw.core.artifact_manager import ArtifactManager


class PhaseRunnerProtocol(Protocol):
    """Protocol defining the interface for phase runners.

    This allows the Orchestrator to work with any class that implements
    the run() method, without requiring a specific PhaseRunner class.
    """

    def run(self, phase: str, context: RunContext) -> PhaseResult:
        """Execute a single phase.

        Args:
            phase: Phase name to execute.
            context: Current run context.

        Returns:
            PhaseResult from the execution.
        """
        ...


__all__ = ["Orchestrator", "PhaseRunnerProtocol"]

logger = logging.getLogger(__name__)


class Orchestrator:
    """Main orchestrator for ADW pipeline execution.

    Coordinates phase execution in fixed order:
    Plan → Build → Verify → Validate → Document

    Handles:
    - Phase sequencing and transitions
    - State persistence at boundaries
    - Error handling and retry logic
    - Snapshot creation for debugging

    Attributes:
        runs_dir: Path to the .adw/runs directory.
        context_manager: Manager for persisting run context.
        snapshot_manager: Manager for creating state snapshots.
        artifact_manager: Manager for storing phase artifacts.
        run_directory_manager: Manager for run directory structure.
        interruption_handler: Handler for graceful shutdown on Ctrl+C/SIGTERM.
        max_retries: Maximum retry attempts for recoverable errors.

    Example:
        >>> from pathlib import Path
        >>> orchestrator = Orchestrator(
        ...     runs_dir=Path("/my/project/.adw/runs"),
        ...     context_manager=context_manager,
        ...     snapshot_manager=snapshot_manager,
        ...     artifact_manager=artifact_manager,
        ...     run_directory_manager=run_directory_manager,
        ... )
        >>> orchestrator.set_phase_runner(phase_runner)
        >>> context = orchestrator.run("Add user authentication")
    """

    def __init__(
        self,
        runs_dir: Path,
        context_manager: ContextManager,
        snapshot_manager: SnapshotManager,
        artifact_manager: "ArtifactManager",
        run_directory_manager: RunDirectoryManager,
        interruption_handler: InterruptionHandler | None = None,
        *,
        progress_display: "ProgressDisplay | None" = None,
        max_retries: int = 3,
    ) -> None:
        """Initialize the Orchestrator.

        Args:
            runs_dir: Path to the .adw/runs directory.
            context_manager: Manager for persisting run context.
            snapshot_manager: Manager for creating state snapshots.
            artifact_manager: Manager for storing phase artifacts.
            run_directory_manager: Manager for run directory structure.
            interruption_handler: Handler for graceful shutdown (optional).
            progress_display: Display for phase progress (optional, Story 5.5).
            max_retries: Maximum retry attempts for recoverable errors (default: 3).
        """
        self.runs_dir = runs_dir
        self.context_manager = context_manager
        self.snapshot_manager = snapshot_manager
        # TODO(Story 5.3): ArtifactManager used for artifact passing
        self.artifact_manager = artifact_manager
        self.run_directory_manager = run_directory_manager
        self.interruption_handler = interruption_handler or InterruptionHandler(
            context_manager, snapshot_manager
        )
        self.progress_display = progress_display
        self.max_retries = max_retries
        self._phase_runner: PhaseRunnerProtocol | None = None

    def set_phase_runner(self, phase_runner: PhaseRunnerProtocol) -> None:
        """Set the phase runner for executing individual phases.

        This is set separately to avoid circular dependencies, as PhaseRunner
        needs to know about the Orchestrator but the Orchestrator needs to
        delegate phase execution to the PhaseRunner.

        Args:
            phase_runner: The PhaseRunner instance to use.
        """
        self._phase_runner = phase_runner

    def get_next_phase(self, current_phase: str) -> str | None:
        """Get the next phase in the sequence.

        Args:
            current_phase: Current phase name.

        Returns:
            Next phase name, or None if current is the last phase.

        Example:
            >>> orchestrator.get_next_phase("plan")
            "build"
            >>> orchestrator.get_next_phase("document")
            None
        """
        try:
            idx = PHASE_SEQUENCE.index(current_phase)
            if idx < len(PHASE_SEQUENCE) - 1:
                return PHASE_SEQUENCE[idx + 1]
            return None
        except ValueError:
            return None

    def run(self, feature_description: str) -> RunContext:
        """Execute the full pipeline for a feature.

        This method orchestrates the complete execution flow:
        1. Generate a new run ID (ULID)
        2. Create initial context and run directory
        3. Execute each phase in sequence with interruption checking
        4. Handle errors, retries, and graceful shutdown
        5. Mark run as completed, failed, or interrupted

        Args:
            feature_description: Description of the feature to implement.

        Returns:
            Final RunContext with status and artifacts.

        Raises:
            ADWError: If a non-recoverable error occurs.
            ShutdownRequested: If graceful shutdown is requested (Ctrl+C/SIGTERM).
            RuntimeError: If PhaseRunner is not set.

        Example:
            >>> context = orchestrator.run("Add user authentication")
            >>> print(context.status)  # "completed" or "failed"
        """
        # Generate run ID
        run_id = str(ULID())

        # Create initial context
        context = RunContext(
            run_id=run_id,
            feature_description=feature_description,
            current_phase=PHASE_SEQUENCE[0],
            started_at=datetime.now(UTC),
            status="running",
        )

        # Create run directory structure
        self.run_directory_manager.create(context)

        # Persist initial state before any phase execution (NFR6)
        self.context_manager.save(context)

        logger.info(
            "Starting run",
            extra={"run_id": run_id, "feature": feature_description},
        )

        try:
            with self.interruption_handler.protected_execution(context):
                for phase in PHASE_SEQUENCE:
                    # Check for shutdown request between phases (NFR7)
                    self.interruption_handler.set_context(context)
                    self.interruption_handler.check_shutdown()

                    context = self._execute_phase_with_transitions(context, phase)

                # All phases complete
                context = context.model_copy(
                    update={
                        "status": "completed",
                        "completed_at": datetime.now(UTC),
                    }
                )
                self.context_manager.save(context)

                # Show pipeline summary (Story 5.5)
                if self.progress_display:
                    total_tokens = sum(context.phase_tokens.values())
                    duration_ms = 0
                    if context.completed_at and context.started_at:
                        duration_ms = int(
                            (context.completed_at - context.started_at).total_seconds()
                            * 1000
                        )
                    self.progress_display.show_pipeline_summary(
                        completed_phases=context.phase_history,
                        status="completed",
                        total_duration_ms=duration_ms,
                        total_tokens=total_tokens,
                    )

                logger.info("Run completed", extra={"run_id": run_id})

        except ShutdownRequested as e:
            # Graceful shutdown - state already saved by handler
            logger.info(
                "Run interrupted",
                extra={"run_id": run_id, "phase": e.phase},
            )
            raise

        except ADWError as e:
            # Mark as failed and persist
            context = context.model_copy(
                update={
                    "status": "failed",
                    "completed_at": datetime.now(UTC),
                }
            )
            self.context_manager.save(context)

            # Show pipeline summary on failure (Story 5.5)
            if self.progress_display:
                total_tokens = sum(context.phase_tokens.values())
                duration_ms = 0
                if context.completed_at and context.started_at:
                    duration_ms = int(
                        (context.completed_at - context.started_at).total_seconds()
                        * 1000
                    )
                self.progress_display.show_pipeline_summary(
                    completed_phases=context.phase_history,
                    status="failed",
                    total_duration_ms=duration_ms,
                    total_tokens=total_tokens,
                )

            logger.error(
                "Run failed",
                extra={
                    "run_id": run_id,
                    "phase": getattr(e, "phase", None),
                    "error_code": e.code,
                },
            )
            raise

        return context

    def _execute_phase_with_transitions(
        self,
        context: RunContext,
        phase: str,
    ) -> RunContext:
        """Execute a single phase with proper transitions.

        Flow:
        1. Update current_phase and persist
        2. Create pre-phase snapshot
        3. Notify progress display of phase start
        4. Execute phase (with retries if recoverable)
        5. Create post-phase snapshot
        6. Notify progress display of completion/error
        7. Update phase_history and persist

        Must complete transitions within 1 second (NFR2).

        Args:
            context: Current run context.
            phase: Phase to execute.

        Returns:
            Updated context after phase completion.

        Raises:
            ADWError: If phase fails with non-recoverable error.
            RuntimeError: If PhaseRunner is not set.
        """
        transition_start = time.monotonic()

        # Update current phase
        context = context.model_copy(update={"current_phase": phase})
        self.context_manager.save(context)

        # Pre-phase snapshot
        self.snapshot_manager.create_pre_phase_snapshot(context, phase)

        # Notify progress display of phase start (Story 5.5)
        if self.progress_display:
            self.progress_display.on_phase_start(phase)

        logger.info(
            "Starting phase",
            extra={"phase": phase, "run_id": context.run_id},
        )

        try:
            # Execute phase with retry for recoverable errors
            result = self._execute_phase_with_retry(context, phase)

            # Post-phase snapshot
            self.snapshot_manager.create_post_phase_snapshot(context, phase, result)

            # Notify progress display of phase completion (Story 5.5)
            if self.progress_display:
                self.progress_display.on_phase_complete(phase, result)

            # Update context with phase completion
            context = context.model_copy(
                update={
                    "phase_history": [*context.phase_history, phase],
                    "phase_tokens": {**context.phase_tokens, phase: result.tokens_used},
                }
            )
            self.context_manager.save(context)

            transition_time_ms = (time.monotonic() - transition_start) * 1000
            logger.info(
                "Phase completed",
                extra={"phase": phase, "duration_ms": transition_time_ms},
            )

            if transition_time_ms > 1000:
                logger.warning(
                    "Transition exceeded 1s",
                    extra={"phase": phase, "duration_ms": transition_time_ms},
                )

            return context

        except ADWError as e:
            # Notify progress display of phase error (Story 5.5)
            if self.progress_display:
                self.progress_display.on_phase_error(phase, e)
            raise

    def _execute_phase_with_retry(
        self,
        context: RunContext,
        phase: str,
    ) -> PhaseResult:
        """Execute a phase with retry logic for recoverable errors.

        Implements exponential backoff: 1s, 2s, 4s between retries.

        Args:
            context: Current run context.
            phase: Phase to execute.

        Returns:
            PhaseResult from successful execution.

        Raises:
            ADWError: If error is non-recoverable or retries exhausted.
            RuntimeError: If PhaseRunner is not set.
        """
        if self._phase_runner is None:
            raise RuntimeError("PhaseRunner not set - call set_phase_runner() first")

        last_error: ADWError | None = None

        for attempt in range(self.max_retries):
            try:
                # Delegate to PhaseRunner (Story 5.2)
                # Using getattr to call run method since we don't have the type yet
                return self._phase_runner.run(phase, context)

            except ADWError as e:
                # Note: Only ADWError subclasses are retried. Other exceptions
                # (IOError, etc.) bubble up immediately as they indicate
                # infrastructure issues that retrying won't resolve.
                last_error = e

                if not e.recoverable:
                    logger.error(
                        "Non-recoverable error",
                        extra={"phase": phase, "error_code": e.code},
                    )
                    raise

                if attempt < self.max_retries - 1:
                    delay = 2**attempt  # 1, 2, 4 seconds
                    logger.warning(
                        "Retrying phase",
                        extra={
                            "phase": phase,
                            "attempt": attempt + 1,
                            "max_attempts": self.max_retries,
                            "delay": delay,
                        },
                    )
                    time.sleep(delay)

        # Retries exhausted
        logger.error(
            "Retries exhausted",
            extra={"phase": phase, "attempts": self.max_retries},
        )
        if last_error is not None:
            raise last_error
        raise RuntimeError("Unexpected state: no error captured but retries exhausted")
