"""Worktree-related models for ADW.

This module contains Pydantic models related to worktree operations
including port allocation for concurrent runs.
"""

from pydantic import BaseModel, Field


class PortAllocation(BaseModel):
    """Port allocation result for a run.

    Represents the deterministic port assignment for a specific run,
    including both backend and frontend ports calculated from the slot.

    Attributes:
        slot: The allocated slot number (0 to max_concurrent-1)
        backend_port: Port number for backend service (9100 + slot by default)
        frontend_port: Port number for frontend service (9200 + slot by default)
        run_id: The ULID of the run this allocation is for

    Example:
        >>> allocation = PortAllocation(
        ...     slot=3,
        ...     backend_port=9103,
        ...     frontend_port=9203,
        ...     run_id="01HQTEST123456789ABCD",
        ... )
        >>> allocation.backend_port
        9103
    """

    slot: int = Field(
        ...,
        ge=0,
        description="The allocated slot number (0 to max_concurrent-1)",
    )
    backend_port: int = Field(
        ...,
        gt=0,
        description="Port number for backend service",
    )
    frontend_port: int = Field(
        ...,
        gt=0,
        description="Port number for frontend service",
    )
    run_id: str = Field(
        ...,
        min_length=1,
        description="The ULID of the run this allocation is for",
    )

    model_config = {
        "frozen": True,
        "json_schema_extra": {
            "example": {
                "slot": 3,
                "backend_port": 9103,
                "frontend_port": 9203,
                "run_id": "01HQTEST123456789ABCD",
            }
        },
    }
