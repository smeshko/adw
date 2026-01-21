"""LLM-related Pydantic models.

This module defines models for LLM execution results and tool calls.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class StreamEventType(str, Enum):
    """Type of event in the Claude Code stream-json output."""

    TEXT = "text"
    """Streaming text content from the LLM."""

    TOOL_START = "tool_start"
    """Tool call initiated (content_block_start with tool_use)."""

    TOOL_RESULT = "tool_result"
    """Tool call result received."""


@dataclass
class StreamEvent:
    """Structured event parsed from Claude Code stream-json output.

    Represents different event types that occur during LLM streaming:
    - TEXT: Streaming text tokens from the LLM
    - TOOL_START: A tool call has been initiated
    - TOOL_RESULT: A tool call has completed with results

    Used by ClaudeCodeExecutor to handle real-time streaming of tool calls
    and text content to live.log.

    Example:
        >>> event = StreamEvent(
        ...     event_type=StreamEventType.TOOL_START,
        ...     tool_name="Read",
        ...     tool_id="toolu_01abc",
        ...     tool_input={"file_path": "/src/main.py"},
        ... )
    """

    event_type: StreamEventType
    """The type of stream event."""

    content: str = ""
    """Text content (for TEXT events)."""

    tool_name: str = ""
    """Name of the tool (for TOOL_START and TOOL_RESULT events)."""

    tool_id: str = ""
    """Tool use ID for correlation (for TOOL_START and TOOL_RESULT events)."""

    tool_input: dict[str, Any] = field(default_factory=dict)
    """Tool input arguments (for TOOL_START events)."""

    tool_output: str = ""
    """Tool output content (for TOOL_RESULT events)."""

    is_error: bool = False
    """Whether the tool result is an error (for TOOL_RESULT events)."""


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
    """Number of tokens consumed by this execution."""

    duration_ms: int = 0
    """Execution duration in milliseconds."""

    error: str | None = None
    """Error message if success is False."""

    attempt_count: int = 1
    """Number of attempts made (including final successful one)."""
