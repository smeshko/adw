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

    The `content` field contains the full conversation text from the LLM,
    while `final_output` contains only the last assistant message. Use
    `final_output` when you need just the result (e.g., for artifacts),
    and `content` when you need the full conversation trace for debugging.

    Example:
        >>> result = LLMResult(
        ...     success=True,
        ...     content="Generated code here...",
        ...     final_output="The final result",
        ...     tool_calls=[],
        ...     tokens_used=500,
        ...     duration_ms=2500,
        ... )
    """

    success: bool
    """Whether the execution completed successfully."""

    content: str
    """The full text content from the LLM conversation (all messages)."""

    final_output: str = ""
    """Only the last assistant message text (ISS-023).

    This is the actual result/output of the phase, excluding intermediate
    reasoning, tool calls, and verbose output. Use this for artifacts and
    downstream phase input. Falls back to content if not explicitly set.
    """

    tool_calls: list[ToolCall] = Field(default_factory=list)
    """List of tool calls made during execution."""

    tokens_used: int = 0
    """Total number of tokens consumed by this execution (input + output)."""

    input_tokens: int = 0
    """Number of input tokens consumed."""

    output_tokens: int = 0
    """Number of output tokens generated."""

    cache_creation_input_tokens: int = 0
    """Number of tokens used to create prompt cache."""

    cache_read_input_tokens: int = 0
    """Number of tokens read from prompt cache."""

    total_cost_usd: float = 0.0
    """Actual cost in USD as reported by Claude Code."""

    duration_ms: int = 0
    """Execution duration in milliseconds."""

    error: str | None = None
    """Error message if success is False."""

    attempt_count: int = 1
    """Number of attempts made (including final successful one)."""
