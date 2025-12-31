"""Phase-related models for ADW workflow execution.

This module contains models for tracking phase status, results,
and artifacts during pipeline execution.
"""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field, computed_field


class PhaseStatus(str, Enum):
    """Status of a phase in the ADW workflow.

    Phases progress through these states:
    - PENDING: Phase is queued but not yet started
    - RUNNING: Phase is currently executing
    - COMPLETED: Phase finished successfully
    - FAILED: Phase encountered an error
    """

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class ArtifactType(str, Enum):
    """Type classification for artifacts produced by phases.

    Artifacts are categorized by their purpose:
    - PLAN: Planning documents (e.g., plan.md)
    - CODE: Source code files
    - TEST: Test files and results
    - LOG: Log files from execution
    - EVIDENCE: Evidence captures (screenshots, API responses)
    - CONFIG: Configuration files
    - OTHER: Uncategorized artifacts
    """

    PLAN = "plan"
    CODE = "code"
    TEST = "test"
    LOG = "log"
    EVIDENCE = "evidence"
    CONFIG = "config"
    OTHER = "other"


class Artifact(BaseModel):
    """Metadata for an artifact produced by a phase.

    This model captures information about artifacts generated during
    phase execution, including their type, location, and creation time.

    Attributes:
        path: Relative path to the artifact file
        artifact_type: Type classification of the artifact
        phase: Phase that produced this artifact
        created_at: When the artifact was created
        size_bytes: Size of the artifact in bytes (if known)
        description: Optional description of the artifact
    """

    path: str = Field(..., description="Relative path to the artifact file")
    artifact_type: ArtifactType = Field(
        ..., description="Type classification of the artifact"
    )
    phase: str = Field(..., description="Phase that produced this artifact")
    created_at: datetime = Field(..., description="When the artifact was created")
    size_bytes: int | None = Field(
        default=None, description="Size in bytes (if known)"
    )
    description: str | None = Field(
        default=None, description="Optional description"
    )

    model_config = {
        "frozen": False,
        "validate_assignment": True,
    }


class PhaseResult(BaseModel):
    """Result of a single phase execution.

    This model captures the outcome of a phase, including timing,
    status, any artifacts produced, and error information if the
    phase failed.

    Attributes:
        phase: Name of the phase (e.g., "plan", "code", "test")
        status: Current status of the phase
        started_at: When the phase started executing
        completed_at: When the phase finished (None if still running)
        artifacts: List of artifact paths produced by this phase
        error: Error message if the phase failed

    Example:
        >>> result = PhaseResult(
        ...     phase="plan",
        ...     status=PhaseStatus.COMPLETED,
        ...     started_at=datetime.now(),
        ...     completed_at=datetime.now(),
        ...     artifacts=["plan.md"],
        ... )
        >>> result.duration_ms  # Computed property
    """

    phase: str = Field(..., description="Name of the phase")
    status: PhaseStatus = Field(..., description="Current status of the phase")
    started_at: datetime = Field(..., description="When the phase started")
    completed_at: datetime | None = Field(
        default=None, description="When the phase finished"
    )
    artifacts: list[str] = Field(
        default_factory=list, description="Artifact paths produced"
    )
    error: str | None = Field(
        default=None, description="Error message if phase failed"
    )

    @computed_field
    @property
    def duration_ms(self) -> int | None:
        """Calculate the duration of the phase in milliseconds.

        Returns:
            Duration in milliseconds, or None if phase hasn't completed.
        """
        if self.completed_at is None or self.started_at is None:
            return None
        delta = self.completed_at - self.started_at
        return int(delta.total_seconds() * 1000)

    model_config = {
        "frozen": False,
        "validate_assignment": True,
        "json_schema_extra": {
            "example": {
                "phase": "plan",
                "status": "completed",
                "started_at": "2024-01-15T10:30:00",
                "completed_at": "2024-01-15T10:31:00",
                "artifacts": ["plan.md"],
                "error": None,
            }
        },
    }
