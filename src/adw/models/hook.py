"""Hook-related models for ADW.

This module contains models for hook execution results,
used when running pre-hook and post-hook shell scripts.
"""

from typing import Literal

from pydantic import BaseModel, Field


class HookResult(BaseModel):
    """Result of executing a shell hook script.

    This model captures the complete output of a hook execution,
    including stdout, stderr, exit code, and timing information.

    Attributes:
        stdout: Standard output captured from the hook script
        stderr: Standard error captured from the hook script
        exit_code: Process exit code (0 for success)
        duration_ms: Execution time in milliseconds
        hook_type: Type of hook ('pre' or 'post')

    Example:
        >>> result = HookResult(
        ...     stdout="Environment ready",
        ...     stderr="",
        ...     exit_code=0,
        ...     duration_ms=150,
        ...     hook_type="pre",
        ... )
    """

    stdout: str = Field(
        default="",
        description="Standard output captured from the hook script",
    )
    stderr: str = Field(
        default="",
        description="Standard error captured from the hook script",
    )
    exit_code: int = Field(
        ...,
        description="Process exit code (0 for success)",
    )
    duration_ms: int = Field(
        ...,
        ge=0,
        description="Execution time in milliseconds",
    )
    hook_type: Literal["pre", "post"] = Field(
        ...,
        description="Type of hook ('pre' or 'post')",
    )

    model_config = {
        "frozen": False,
        "validate_assignment": True,
    }
