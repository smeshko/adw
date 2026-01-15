"""Centralized resume logic for ADW.

This module provides the ResumeManager class that consolidates all resume-related
logic in one place. This eliminates duplication across cli/resume.py, orchestrator.py,
and interruption.py.

Key responsibilities:
- Check if a run can be resumed (can_resume)
- Validate a run is resumable (validate_resumable)
- Find a run to resume by ID or most recent (find_run_to_resume)
- Determine the resume phase (get_resume_phase)
- Prepare a context for resumption (prepare_for_resume)
- Get run status summary (get_resume_status)
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

from adw.core.constants import PHASE_SEQUENCE
from adw.core.run_lookup import RunLookup
from adw.exceptions import ConfigError, StateError
from adw.models.resume import ResumeInfo, ResumeStatus

if TYPE_CHECKING:
    from adw.core.context_manager import ContextManager
    from adw.models import RunContext

__all__ = ["ResumeManager"]

logger = logging.getLogger(__name__)


class ResumeManager:
    """Centralized manager for all resume operations.

    Consolidates resume logic previously scattered across:
    - cli/resume.py: _find_run_to_resume(), validation
    - orchestrator.py: resume() validation, phase determination
    - interruption.py: can_resume(), prepare_resume(), get_resume_phase()

    Uses constructor injection pattern per project conventions.

    Attributes:
        runs_dir: Path to the .adw/runs directory.
        run_lookup: Service for finding runs by ID.
        context_manager: Manager for loading/saving contexts.

    Example:
        >>> from pathlib import Path
        >>> from adw.core import ContextManager
        >>> from adw.core.run_lookup import RunLookup
        >>> runs_dir = Path(".adw/runs")
        >>> resume_manager = ResumeManager(
        ...     runs_dir=runs_dir,
        ...     run_lookup=RunLookup(runs_dir),
        ...     context_manager=ContextManager(runs_dir),
        ... )
        >>> info = resume_manager.find_run_to_resume()
        >>> if info.is_valid:
        ...     print(f"Resuming {info.run_id} from {info.resume_phase}")
    """

    def __init__(
        self,
        runs_dir: Path,
        run_lookup: RunLookup,
        context_manager: ContextManager,
    ) -> None:
        """Initialize the ResumeManager.

        Args:
            runs_dir: Path to the .adw/runs directory.
            run_lookup: Service for finding runs by ID.
            context_manager: Manager for loading/saving contexts.
        """
        self.runs_dir = runs_dir
        self.run_lookup = run_lookup
        self.context_manager = context_manager

    def can_resume(self, context: RunContext) -> bool:
        """Check if a run can be resumed.

        A run can be resumed if it's not completed.

        Args:
            context: The run context to check.

        Returns:
            True if the run can be resumed, False otherwise.
        """
        return context.status != "completed"

    def validate_resumable(
        self,
        context: RunContext,
        *,
        from_phase: str | None = None,
    ) -> None:
        """Validate that a run can be resumed.

        Checks that:
        1. The run is not completed
        2. The specified phase (if any) is valid

        Args:
            context: The run context to validate.
            from_phase: Optional phase to validate. If provided, must be in
                PHASE_SEQUENCE.

        Raises:
            ConfigError: If run is completed or phase is invalid.
        """
        if context.status == "completed":
            raise ConfigError(
                code="RUN_COMPLETED",
                message="Run already completed",
                suggestion="Start a new run with 'adw run'",
                recoverable=False,
            )

        if from_phase is not None and from_phase not in PHASE_SEQUENCE:
            valid_phases = ", ".join(PHASE_SEQUENCE)
            raise ConfigError(
                code="INVALID_PHASE",
                message=f"Unknown phase: {from_phase}",
                suggestion=f"Valid phases: {valid_phases}",
                recoverable=False,
            )

    def find_run_to_resume(
        self,
        run_id: str | None = None,
        *,
        from_phase: str | None = None,
    ) -> ResumeInfo:
        """Find a run to resume and prepare resume info.

        If run_id is provided, looks up that specific run. Otherwise,
        finds the most recent incomplete run.

        Args:
            run_id: Specific run ID to resume, or None for most recent incomplete.
            from_phase: Optional phase to resume from (overrides context).

        Returns:
            ResumeInfo with the run context and resume phase.
            If an error occurs, ResumeInfo.is_valid will be False and
            validation_error will contain the error message.

        Raises:
            ConfigError: If run not found.
            StateError: If run state is corrupted.
        """
        # Find the context
        context = self._find_context(run_id)

        # Determine resume phase
        resume_phase = from_phase or self.get_resume_phase(context)

        if resume_phase is None:
            # All phases completed but status not "completed" - unusual state
            resume_phase = context.current_phase

        # Validate
        try:
            self.validate_resumable(context, from_phase=from_phase)
        except ConfigError as e:
            return ResumeInfo(
                context=context,
                resume_phase=resume_phase or context.current_phase,
                is_valid=False,
                validation_error=e.message,
                error_code=e.code,
                error_suggestion=e.suggestion,
            )

        return ResumeInfo(
            context=context,
            resume_phase=resume_phase,
            is_valid=True,
        )

    def _find_context(self, run_id: str | None) -> RunContext:
        """Find the context for a run.

        Args:
            run_id: Specific run ID, or None for most recent incomplete.

        Returns:
            RunContext for the run.

        Raises:
            ConfigError: If run not found.
            StateError: If run state is corrupted.
        """
        if run_id:
            context = self.run_lookup.find_by_id(run_id)
            if not context:
                # Check if run directory exists but context is corrupted
                run_path = self.runs_dir / run_id
                if run_path.exists():
                    raise StateError(
                        code="STATE_CORRUPTED",
                        message=f"Run {run_id} has corrupted state",
                        suggestion=(
                            f"Check snapshots in .adw/runs/{run_id}/snapshots/ "
                            "for recovery options"
                        ),
                        recoverable=False,
                    )
                raise ConfigError(
                    code="RUN_NOT_FOUND",
                    message=f"Run {run_id} not found",
                    suggestion="Use 'adw list' to see available runs",
                    recoverable=False,
                )
            return context

        # Find most recent incomplete
        context = self.run_lookup.find_most_recent_incomplete()
        if not context:
            raise ConfigError(
                code="NO_INCOMPLETE_RUNS",
                message="No incomplete runs found",
                suggestion="Use 'adw run \"feature\"' to start a new run",
                recoverable=False,
            )

        logger.debug(
            "Found incomplete run: %s (status=%s)",
            context.run_id,
            context.status,
        )
        return context

    def get_resume_phase(self, context: RunContext) -> str | None:
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
        for phase in PHASE_SEQUENCE:
            if phase not in completed:
                return phase

        # All phases completed
        return None

    def prepare_for_resume(
        self,
        context: RunContext,
        *,
        from_phase: str | None = None,
    ) -> RunContext:
        """Prepare a context for resumption.

        Updates the context to be ready for continued execution:
        - Validates the run can be resumed
        - Sets status to "running"
        - Clears interrupted_phase and interrupted_at
        - Preserves phase_history and other state

        Args:
            context: The run context to prepare for resume.
            from_phase: Optional phase to resume from.

        Returns:
            New RunContext instance ready for execution.

        Raises:
            ConfigError: If run is already completed.
            StateError: If run cannot be resumed.
        """
        self.validate_resumable(context, from_phase=from_phase)

        return context.model_copy(
            update={
                "status": "running",
                "interrupted_phase": None,
                "interrupted_at": None,
            }
        )

    def get_resume_status(self, context: RunContext) -> ResumeStatus:
        """Get a summary of run status for display.

        Returns a ResumeStatus dataclass with status information suitable for
        command-line display or API responses.

        Args:
            context: The run context to summarize.

        Returns:
            ResumeStatus with all status fields.
        """
        return ResumeStatus(
            run_id=context.run_id,
            status=context.status,
            current_phase=context.current_phase,
            interrupted_phase=context.interrupted_phase,
            completed_phases=list(context.phase_history),
            can_resume=self.can_resume(context),
            resume_phase=self.get_resume_phase(context),
        )
