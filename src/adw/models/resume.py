"""Resume models for centralized resume logic.

This module provides dataclasses for resume operations:
- ResumeInfo: Information about what can be resumed and how
- ResumeStatus: Status summary for display/API responses

These models are used by the ResumeManager to communicate resume state.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from adw.models import RunContext

__all__ = ["ResumeInfo", "ResumeStatus"]


@dataclass(frozen=True)
class ResumeInfo:
    """Information required to resume a run.

    Encapsulates all data needed to perform a resume operation.
    Immutable to prevent accidental modification after preparation.

    Attributes:
        context: The run context to resume.
        resume_phase: Phase to resume from.
        is_valid: Whether this resume info is valid for execution.
        validation_error: Error message if not valid, None otherwise.
    """

    context: RunContext
    resume_phase: str
    is_valid: bool = True
    validation_error: str | None = None

    @property
    def run_id(self) -> str:
        """Get the run ID for convenience."""
        return self.context.run_id

    @property
    def feature_description(self) -> str:
        """Get the feature description for convenience."""
        return self.context.feature_description

    @property
    def completed_phases(self) -> list[str]:
        """Get the list of completed phases for convenience."""
        return list(self.context.phase_history)


@dataclass(frozen=True)
class ResumeStatus:
    """Status summary of a run for display or API responses.

    Provides a structured view of run status suitable for
    command-line display or API responses.

    Attributes:
        run_id: The run identifier.
        status: Current status (running, completed, interrupted, failed, aborted).
        current_phase: Phase currently set.
        interrupted_phase: Phase where interruption occurred (if any).
        completed_phases: List of phases in phase_history.
        can_resume: Whether the run can be resumed.
        resume_phase: Phase to resume from (if applicable).
    """

    run_id: str
    status: str
    current_phase: str
    interrupted_phase: str | None
    completed_phases: list[str]
    can_resume: bool
    resume_phase: str | None

    def to_dict(self) -> dict[str, object]:
        """Convert to dictionary for JSON serialization.

        Returns:
            Dictionary with all status fields.
        """
        return {
            "run_id": self.run_id,
            "status": self.status,
            "current_phase": self.current_phase,
            "interrupted_phase": self.interrupted_phase,
            "completed_phases": self.completed_phases,
            "can_resume": self.can_resume,
            "resume_phase": self.resume_phase,
        }
