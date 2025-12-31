"""Context models for ADW run state management.

This module contains models for tracking run context, session context,
and project context throughout the ADW workflow execution.
"""

from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, Field, field_validator


class RunContext(BaseModel):
    """Full run state for ADW workflow execution.

    This model tracks the complete state of a development run, including
    which phase is currently active, the history of phases executed, and
    any artifacts produced during the run.

    Attributes:
        run_id: ULID identifier for this run (26 chars, lexicographically sortable)
        feature_description: Description of the feature being developed
        current_phase: Name of the currently active phase
        phase_history: List of phases that have been executed
        started_at: When this run started
        completed_at: When this run completed (None if still running)
        status: Current run status (running, completed, failed)
        artifacts: Mapping of phase names to lists of artifact paths

    Example:
        >>> from datetime import datetime
        >>> context = RunContext(
        ...     run_id="01KDSG2VDHNK0W4HSCZWJZXWSQ",
        ...     feature_description="Add user authentication",
        ...     current_phase="plan",
        ...     started_at=datetime.now(),
        ... )
        >>> # Immutable update pattern
        >>> new_context = context.model_copy(update={"current_phase": "build"})
    """

    run_id: str = Field(..., description="ULID run identifier (26 characters)")
    feature_description: str = Field(
        ..., description="Description of the feature being developed"
    )
    current_phase: str = Field(
        ..., description="Name of the currently active phase"
    )
    phase_history: list[str] = Field(
        default_factory=list, description="List of phases executed"
    )
    started_at: datetime = Field(..., description="When this run started")
    completed_at: datetime | None = Field(
        default=None, description="When this run completed"
    )
    status: str = Field(default="running", description="Current run status")
    artifacts: dict[str, list[str]] = Field(
        default_factory=dict,
        description="Mapping of phase names to artifact paths",
    )

    @field_validator("run_id")
    @classmethod
    def validate_ulid(cls, v: str) -> str:
        """Validate that run_id is a valid ULID format.

        ULID format:
        - 26 characters
        - Base32 encoding (Crockford's alphabet)
        - First 10 chars: timestamp (48 bits)
        - Last 16 chars: randomness (80 bits)

        Args:
            v: The run_id value to validate

        Returns:
            The validated run_id

        Raises:
            ValueError: If the run_id is not a valid ULID format
        """
        if len(v) != 26:
            raise ValueError(f"ULID must be 26 characters, got {len(v)}")

        # Crockford's Base32 alphabet (excludes I, L, O, U to avoid confusion)
        valid_chars = set("0123456789ABCDEFGHJKMNPQRSTVWXYZ")
        upper_v = v.upper()

        for char in upper_v:
            if char not in valid_chars:
                raise ValueError(f"Invalid ULID character: {char}")

        return v

    model_config = {
        "frozen": False,  # Allow mutation for development, use model_copy
        "validate_assignment": True,  # Validate on attribute assignment
        "json_schema_extra": {
            "example": {
                "run_id": "01KDSG2VDHNK0W4HSCZWJZXWSQ",
                "feature_description": "Add user authentication",
                "current_phase": "plan",
                "phase_history": ["plan"],
                "started_at": "2024-01-15T10:30:00",
                "completed_at": None,
                "status": "running",
                "artifacts": {"plan": ["plan.md"]},
            }
        },
    }


class SessionContext(BaseModel):
    """Current session state derived from RunContext.

    This model represents the active session state, providing a view
    into the current run context with session-specific information.

    Attributes:
        run_id: ULID of the current run
        current_phase: Currently active phase name
        is_resuming: Whether this session is resuming a previous run
        last_checkpoint: Path to the last saved state checkpoint
    """

    run_id: str = Field(..., description="ULID of the current run")
    current_phase: str = Field(..., description="Currently active phase name")
    is_resuming: bool = Field(
        default=False, description="Whether resuming a previous run"
    )
    last_checkpoint: str | None = Field(
        default=None, description="Path to last saved state checkpoint"
    )

    model_config = {
        "frozen": False,
        "validate_assignment": True,
    }


class ProjectContext(BaseModel):
    """Resolved project configuration and paths.

    This model contains the resolved project information including
    paths, configuration, and environment details.

    Attributes:
        project_root: Absolute path to the project root directory
        config_path: Path to the adw.yaml configuration file
        runs_dir: Directory for storing run data
        language: Programming language of the project
        framework: Framework being used (if any)
        platform: Target platform
    """

    project_root: Path = Field(..., description="Absolute path to project root")
    config_path: Path = Field(..., description="Path to adw.yaml configuration")
    runs_dir: Path = Field(..., description="Directory for storing run data")
    language: str = Field(..., description="Programming language")
    framework: str | None = Field(default=None, description="Framework being used")
    platform: str = Field(default="cli", description="Target platform")

    model_config = {
        "frozen": False,
        "validate_assignment": True,
        "arbitrary_types_allowed": True,  # Allow Path type
    }


class StateSnapshot(BaseModel):
    """Point-in-time snapshot of run state for debugging.

    This model captures a complete snapshot of the run state at a
    specific point in time, useful for debugging and recovery.

    Attributes:
        snapshot_id: Unique identifier for this snapshot
        run_id: ULID of the run this snapshot belongs to
        phase: Phase name at time of snapshot
        timestamp: When this snapshot was taken
        context_json: Serialized RunContext as JSON string
        notes: Optional notes about why snapshot was taken
    """

    snapshot_id: str = Field(..., description="Unique identifier for snapshot")
    run_id: str = Field(..., description="ULID of the run")
    phase: str = Field(..., description="Phase at time of snapshot")
    timestamp: datetime = Field(..., description="When snapshot was taken")
    context_json: str = Field(..., description="Serialized RunContext")
    notes: str | None = Field(default=None, description="Optional notes")

    model_config = {
        "frozen": False,
        "validate_assignment": True,
    }
