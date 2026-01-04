"""Security-related Pydantic models.

This module defines models for security monitoring and tool execution logging.
"""

from typing import Any

from pydantic import BaseModel, Field


class ToolCallLog(BaseModel):
    """Log entry for a tool call during LLM execution.

    Captures comprehensive information about each tool invocation including
    timing, arguments, results, and security blocking status.

    This model is designed for JSONL serialization to support append-only
    logging in `.adw/runs/<id>/tools.jsonl`.

    Example:
        >>> log = ToolCallLog(
        ...     timestamp="2026-01-03T10:30:00.123Z",
        ...     tool_name="Bash",
        ...     arguments={"command": "npm test"},
        ...     result_summary="Exit code: 0, output: 15 tests passed",
        ...     duration_ms=2500,
        ...     phase="build",
        ... )
        >>> log.model_dump_json()  # Write to JSONL file
    """

    timestamp: str
    """ISO 8601 format timestamp when the tool was called."""

    tool_name: str
    """Name of the tool that was called (e.g., 'Bash', 'Read', 'Write')."""

    arguments: dict[str, Any] = Field(default_factory=dict)
    """Arguments passed to the tool."""

    result_summary: str | None = None
    """Brief summary of result (truncated if long)."""

    duration_ms: int = 0
    """Execution time in milliseconds."""

    blocked: bool = False
    """Whether the tool call was blocked by security checks."""

    block_reason: str | None = None
    """Reason for blocking (if blocked is True)."""

    phase: str | None = None
    """Current phase when the tool was called (e.g., 'plan', 'build')."""
