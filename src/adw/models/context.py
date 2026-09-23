"""Context models for ADW run state management.

This module contains models for tracking run context and state snapshots
throughout the ADW workflow execution.
"""

from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel, Field, computed_field, field_validator

from adw.models.task import TaskInfo

if TYPE_CHECKING:
    from adw.models.phase import PhaseResult


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
    current_phase: str = Field(..., description="Name of the currently active phase")
    phase_history: list[str] = Field(
        default_factory=list, description="List of phases executed"
    )
    started_at: datetime = Field(..., description="When this run started")
    completed_at: datetime | None = Field(
        default=None, description="When this run completed"
    )
    status: Literal["running", "completed", "interrupted", "failed", "aborted"] = Field(
        default="running", description="Current run status"
    )
    interrupted_phase: str | None = Field(
        default=None,
        description="Phase where interruption occurred (status='interrupted')",
    )
    interrupted_at: datetime | None = Field(
        default=None,
        description="Timestamp when run was interrupted",
    )
    artifacts: dict[str, list[str]] = Field(
        default_factory=dict,
        description="Mapping of phase names to artifact paths",
    )
    phase_tokens: dict[str, int] = Field(
        default_factory=dict,
        description="Token usage per phase (phase name -> token count)",
    )
    commit_shas: list[str] = Field(
        default_factory=list,
        description="Git commit SHAs created during this run (for audit)",
    )
    worktree_path: Path | None = Field(
        default=None,
        description="Path to git worktree for this run (None if not using worktree)",
    )
    use_worktree: bool = Field(
        default=True,
        description="Whether this run uses worktree isolation",
    )
    branch_name: str | None = Field(
        default=None,
        description="Git branch name for this run (e.g., 'adw/01HQX...')",
    )
    branch_deleted: bool = Field(
        default=False,
        description="Whether the branch has been deleted during cleanup",
    )
    task_id: str | None = Field(
        default=None,
        description="Task ID from external task manager (e.g., 'RULE-123'). "
        "Populated when run is initiated from a task.",
    )
    task_info: TaskInfo | None = Field(
        default=None,
        description="Full task information from external task manager. "
        "Contains title, description, status, labels, etc.",
    )
    task_manager: str | None = Field(
        default=None,
        description="Task manager type (e.g., 'linear', 'jira', 'github'). "
        "None when run is not associated with a task manager.",
    )
    pr_url: str | None = Field(
        default=None,
        description="URL of the pull request created for this run. "
        "Set after document phase completes.",
    )
    pr_creation_attempted: bool = Field(
        default=False,
        description="Whether PR creation was attempted for this run. "
        "Set to True before attempting PR creation in document phase. "
        "(Phase Extensions)",
    )
    pr_creation_failed: bool = Field(
        default=False,
        description="Whether PR creation failed for this run. "
        "Used by ShipExtension to skip ship phase when PR is unavailable. "
        "(Phase Extensions)",
    )
    pr_failure_reason: str | None = Field(
        default=None,
        description="Reason PR creation failed, if applicable. "
        "Provides context for why ship phase may be skipped. "
        "(Phase Extensions)",
    )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def total_tokens(self) -> int:
        """Calculate total tokens used across all phases.

        Returns:
            Sum of all phase token counts.
        """
        return sum(self.phase_tokens.values())

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
    }


class StateSnapshot(BaseModel):
    """State captured at phase boundaries for debugging and recovery.

    Snapshots are created before and after each phase to enable:
    - Debugging failures by examining pre-failure state
    - Resuming from known-good states
    - Time-travel debugging

    Snapshots are named: <seq>_<timing>_<phase>.json
    Example: 001_pre_plan.json, 002_post_plan.json

    Attributes:
        context: Full run context at snapshot time
        phase_result: Phase result (only for post-phase snapshots)
        timestamp: When snapshot was created (auto-generated if not provided)
        label: Human-readable label (e.g., 'pre_plan', 'post_build')
        sequence: Sequential snapshot number (1, 2, 3, ...)
    """

    context: "RunContext" = Field(..., description="Full run context at snapshot time")
    phase_result: "PhaseResult | None" = Field(
        default=None, description="Phase result (only for post-phase snapshots)"
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="When snapshot was created",
    )
    label: str = Field(..., description="Human-readable label (e.g., 'pre_plan')")
    sequence: int = Field(
        ..., gt=0, description="Sequential snapshot number (1, 2, ...)"
    )

    model_config = {
        "frozen": False,
        "validate_assignment": True,
    }
