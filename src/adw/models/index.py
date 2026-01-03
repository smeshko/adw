"""Index entry model for global workflow execution index.

This module contains the IndexEntry model for tracking workflow runs
in the global index at ~/.adw/index.jsonl.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class IndexEntry(BaseModel):
    """Entry in the global workflow execution index.

    Each entry represents a single ADW workflow run, tracking its lifecycle
    from start to completion. Entries are stored in ~/.adw/index.jsonl
    as JSONL format (one JSON object per line).

    Attributes:
        run_id: ULID run identifier (26 characters, lexicographically sortable)
        project_path: Absolute path to the project directory
        project_name: Project directory name (extracted from project_path)
        feature_description: Description of the feature being developed
        started_at: When this run started (UTC timestamp)
        completed_at: When this run completed (None if still running)
        status: Current run status (running, completed, failed, interrupted, aborted)
        phase_reached: Last phase that was executed
        phases_completed: List of phases that completed successfully

    Example:
        >>> from datetime import datetime, UTC
        >>> entry = IndexEntry(
        ...     run_id="01KDSG2VDHNK0W4HSCZWJZXWSQ",
        ...     project_path="/path/to/project",
        ...     project_name="my-project",
        ...     feature_description="Add user authentication",
        ...     started_at=datetime.now(UTC),
        ...     status="running",
        ... )
        >>> # Serialize to JSON for JSONL storage
        >>> json_line = entry.model_dump_json()
    """

    run_id: str = Field(..., description="ULID run identifier (26 characters)")
    project_path: str = Field(..., description="Absolute path to project directory")
    project_name: str = Field(..., description="Project directory name")
    feature_description: str = Field(
        ..., description="Description of the feature being developed"
    )
    started_at: datetime = Field(..., description="When this run started (UTC)")
    completed_at: datetime | None = Field(
        default=None, description="When this run completed (None if running)"
    )
    status: Literal["running", "completed", "failed", "interrupted", "aborted"] = Field(
        ..., description="Current run status"
    )
    phase_reached: str | None = Field(
        default=None, description="Last phase that was executed"
    )
    phases_completed: list[str] = Field(
        default_factory=list, description="List of phases that completed successfully"
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
                "project_path": "/path/to/project",
                "project_name": "my-project",
                "feature_description": "Add user authentication",
                "started_at": "2024-01-15T10:30:00Z",
                "completed_at": None,
                "status": "running",
                "phase_reached": None,
                "phases_completed": [],
            }
        },
    }
