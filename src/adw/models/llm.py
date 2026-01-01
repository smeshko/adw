"""LLM-related Pydantic models.

This module defines models for LLM execution results and tool calls.
"""

from typing import Any

from pydantic import BaseModel, Field


class ToolCall(BaseModel):
    """A tool call made by the LLM during execution.

    Tracks which tools the LLM invoked and their results.

    Example:
        >>> tool_call = ToolCall(
        ...     tool_name="read_file",
        ...     arguments={"path": "/src/main.py"},
        ...     result_summary="File read successfully, 150 lines",
        ... )
    """

    tool_name: str
    """Name of the tool that was called."""

    arguments: dict[str, Any] = Field(default_factory=dict)
    """Arguments passed to the tool."""

    result_summary: str | None = None
    """Optional summary of the tool's result."""


class LLMResult(BaseModel):
    """Result from an LLM execution.

    Captures all relevant information from an LLM call including
    success status, content, tool calls, and performance metrics.

    Example:
        >>> result = LLMResult(
        ...     success=True,
        ...     content="Generated code here...",
        ...     tool_calls=[],
        ...     tokens_used=500,
        ...     duration_ms=2500,
        ... )
    """

    success: bool
    """Whether the execution completed successfully."""

    content: str
    """The text content returned by the LLM."""

    tool_calls: list[ToolCall] = Field(default_factory=list)
    """List of tool calls made during execution."""

    tokens_used: int = 0
    """Number of tokens consumed by this execution."""

    duration_ms: int = 0
    """Execution duration in milliseconds."""

    error: str | None = None
    """Error message if success is False."""

    attempt_count: int = 1
    """Number of attempts made (including final successful one)."""
