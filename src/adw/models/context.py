"""Context models for ADW run state management.

This module contains models for tracking run context, session context,
and project context throughout the ADW workflow execution.
"""

from datetime import datetime

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


# Placeholder for SessionContext - will be implemented in Task 5
# Placeholder for ProjectContext - will be implemented in Task 5
