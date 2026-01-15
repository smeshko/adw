"""Logging-related models for ADW.

This module contains models for structured logging:
- LogLevel: Severity levels (TRACE, DEBUG, INFO, WARN, ERROR, FATAL)
- LogCategory: Log event categories (PHASE, LLM, HOOK, STATE, ERROR, PERFORMANCE)
- LogContext: Contextual information for scoped logging
- LogEvent: A single log entry with all metadata

And LLM capture models (Story 7.3):
- LLMRequest: Captured LLM request (prompt, params, timestamp, phase)
- LLMResponse: Captured LLM response (content, tool_calls, tokens, duration)
- LLMStreamEvent: Stream capture for token-by-token replay
- LLMToolCall: Tool invocation capture
- LLMToolResult: Tool execution result capture
- LLMStats: Token usage and timing statistics
- StreamEventType: Types of stream events
"""

from datetime import UTC, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class LogLevel(str, Enum):
    """Log severity levels.

    Levels are ordered from least to most severe:
    - TRACE: Detailed debugging information
    - DEBUG: General debugging information
    - INFO: General informational messages
    - WARN: Warning conditions
    - ERROR: Error conditions
    - FATAL: Critical errors causing termination
    """

    TRACE = "trace"
    DEBUG = "debug"
    INFO = "info"
    WARN = "warn"
    ERROR = "error"
    FATAL = "fatal"


class Verbosity(str, Enum):
    """CLI verbosity levels for controlling console output.

    Verbosity controls what level of detail is shown on the console:
    - QUIET: Only errors and fatal messages (-q, --quiet)
    - NORMAL: Info and above (default)
    - VERBOSE: Debug and above (-v, --verbose)
    - TRACE: Everything including trace (--trace)

    Note: Verbosity affects console output only, not file logs.
    File logs always capture everything for debugging purposes.
    """

    QUIET = "quiet"
    NORMAL = "normal"
    VERBOSE = "verbose"
    TRACE = "trace"


# Verbosity-to-LogLevel threshold mapping
# Determines the minimum LogLevel shown at each Verbosity
VERBOSITY_LEVEL_MAP: dict["Verbosity", LogLevel] = {
    Verbosity.QUIET: LogLevel.ERROR,  # Only ERROR and FATAL
    Verbosity.NORMAL: LogLevel.INFO,  # INFO, WARN, ERROR, FATAL
    Verbosity.VERBOSE: LogLevel.DEBUG,  # DEBUG and above
    Verbosity.TRACE: LogLevel.TRACE,  # Everything
}


class LogCategory(str, Enum):
    """Log event categories for filtering and organization.

    Categories indicate the subsystem or concern area:
    - PHASE: Phase execution events
    - LLM: LLM interaction events
    - HOOK: Shell hook execution events
    - STATE: State transition events
    - ERROR: Error and exception events
    - PERFORMANCE: Timing and performance metrics
    - WEBHOOK: Webhook server events
    """

    PHASE = "phase"
    LLM = "llm"
    HOOK = "hook"
    STATE = "state"
    ERROR = "error"
    PERFORMANCE = "performance"
    WEBHOOK = "webhook"


class LogContext(BaseModel):
    """Contextual information attached to log events.

    LogContext provides scoped context that can be inherited by child loggers.
    This enables hierarchical logging with automatic context propagation.

    Attributes:
        run_id: The current run ID (ULID)
        phase: The current phase name
        extra: Additional context fields

    Example:
        >>> ctx = LogContext(run_id="01HQ123ABC", phase="build")
        >>> child_ctx = ctx.merge(phase="test", extra={"step": 1})
        >>> child_ctx.run_id
        '01HQ123ABC'
        >>> child_ctx.phase
        'test'
    """

    run_id: str | None = Field(
        default=None,
        description="The current run ID (ULID)",
    )
    phase: str | None = Field(
        default=None,
        description="The current phase name",
    )
    extra: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional context fields",
    )

    def merge(
        self,
        *,
        run_id: str | None = None,
        phase: str | None = None,
        extra: dict[str, Any] | None = None,
    ) -> "LogContext":
        """Create a new context merged with the provided values.

        Values from this context are inherited unless overridden.
        Extra fields are merged (not replaced).

        Args:
            run_id: Override the run_id (or inherit from parent)
            phase: Override the phase (or inherit from parent)
            extra: Additional extra fields to merge

        Returns:
            A new LogContext with merged values
        """
        merged_extra = {**self.extra}
        if extra:
            merged_extra.update(extra)

        return LogContext(
            run_id=run_id if run_id is not None else self.run_id,
            phase=phase if phase is not None else self.phase,
            extra=merged_extra,
        )

    model_config = {
        "frozen": False,
        "validate_assignment": True,
        "json_schema_extra": {
            "example": {
                "run_id": "01HQ123ABC456DEF",
                "phase": "build",
                "extra": {"component": "executor"},
            }
        },
    }


def _utc_now() -> datetime:
    """Get current UTC timestamp."""
    return datetime.now(UTC)


class LogEvent(BaseModel):
    """A single structured log entry.

    LogEvent represents a complete log record with all metadata
    needed for multi-tier output (console, file, JSONL).

    Attributes:
        timestamp: When the event occurred (UTC)
        level: Severity level
        category: Event category for filtering
        message: Human-readable log message
        context: Contextual information

    Example:
        >>> event = LogEvent(
        ...     level=LogLevel.INFO,
        ...     category=LogCategory.PHASE,
        ...     message="Phase completed successfully",
        ...     context=LogContext(run_id="01HQ123ABC", phase="build"),
        ... )
        >>> event.model_dump_json()  # For JSONL output
    """

    timestamp: datetime = Field(
        default_factory=_utc_now,
        description="When the event occurred (UTC)",
    )
    level: LogLevel = Field(
        ...,
        description="Log severity level",
    )
    category: LogCategory = Field(
        ...,
        description="Log event category",
    )
    message: str = Field(
        ...,
        description="Human-readable log message",
    )
    context: LogContext = Field(
        default_factory=LogContext,
        description="Contextual information",
    )

    model_config = {
        "frozen": False,
        "validate_assignment": True,
        "json_schema_extra": {
            "example": {
                "timestamp": "2025-01-03T12:00:00Z",
                "level": "info",
                "category": "phase",
                "message": "Phase 'build' completed successfully",
                "context": {
                    "run_id": "01HQ123ABC",
                    "phase": "build",
                    "extra": {},
                },
            }
        },
    }


# ============================================================================
# LLM Capture Models (Story 7.3)
# ============================================================================


class StreamEventType(str, Enum):
    """Types of LLM stream events for capture.

    Used in LLMStreamEvent to categorize stream data:
    - TOKEN: A text token from the LLM response
    - TOOL_CALL_START: Beginning of a tool invocation
    - TOOL_CALL_END: Completion of a tool invocation
    - THINKING: Reasoning/thinking block content
    - COMPLETE: Stream completion with final stats
    - ERROR: An error during streaming
    """

    TOKEN = "token"
    TOOL_CALL_START = "tool_call_start"
    TOOL_CALL_END = "tool_call_end"
    THINKING = "thinking"
    COMPLETE = "complete"
    ERROR = "error"


class LLMStats(BaseModel):
    """Token usage and timing statistics for LLM interactions.

    Captures metrics for debugging and cost tracking.

    Attributes:
        input_tokens: Number of tokens in the request
        output_tokens: Number of tokens in the response
        duration_ms: Total execution time in milliseconds

    Example:
        >>> stats = LLMStats(input_tokens=4521, output_tokens=3892, duration_ms=47333)
    """

    input_tokens: int = Field(
        default=0,
        description="Number of tokens in the request",
    )
    output_tokens: int = Field(
        default=0,
        description="Number of tokens in the response",
    )
    duration_ms: int = Field(
        default=0,
        description="Total execution time in milliseconds",
    )


class LLMToolCall(BaseModel):
    """A tool call made during LLM execution for capture.

    Captures the details of tool invocations for debugging and replay.

    Attributes:
        id: Unique identifier for this tool call
        name: Name of the tool being called
        input: Arguments passed to the tool

    Example:
        >>> tool_call = LLMToolCall(
        ...     id="call_01",
        ...     name="create_file",
        ...     input={"path": "test.py", "content": "# test"}
        ... )
    """

    id: str = Field(
        ...,
        description="Unique identifier for this tool call",
    )
    name: str = Field(
        ...,
        description="Name of the tool being called",
    )
    input: dict[str, Any] = Field(
        default_factory=dict,
        description="Arguments passed to the tool",
    )


class LLMToolResult(BaseModel):
    """Result of a tool execution for capture.

    Captures tool execution outcomes for debugging.

    Attributes:
        id: Tool call ID this result corresponds to
        output: The output from the tool
        success: Whether the tool executed successfully
        duration_ms: Execution time in milliseconds

    Example:
        >>> result = LLMToolResult(
        ...     id="call_01",
        ...     output="File created successfully",
        ...     success=True,
        ...     duration_ms=45
        ... )
    """

    id: str = Field(
        ...,
        description="Tool call ID this result corresponds to",
    )
    output: str = Field(
        ...,
        description="The output from the tool",
    )
    success: bool = Field(
        default=True,
        description="Whether the tool executed successfully",
    )
    duration_ms: int = Field(
        default=0,
        description="Execution time in milliseconds",
    )


class LLMRequest(BaseModel):
    """Captured LLM request for debugging and replay.

    Saves the full request details before LLM execution.
    Written to `llm/<seq>_request.json`.

    Attributes:
        timestamp: When the request was made (UTC)
        prompt: The prompt sent to the LLM
        phase: The current execution phase (plan, build, etc.)
        params: LLM parameters (model, temperature, max_tokens, etc.)

    Example:
        >>> request = LLMRequest(
        ...     prompt="Generate a hello world program",
        ...     phase="build",
        ...     params={"model": "claude-sonnet-4-20250514", "temperature": 0}
        ... )
    """

    timestamp: datetime = Field(
        default_factory=_utc_now,
        description="When the request was made (UTC)",
    )
    prompt: str = Field(
        ...,
        description="The prompt sent to the LLM",
    )
    phase: str = Field(
        ...,
        description="The current execution phase",
    )
    params: dict[str, Any] = Field(
        default_factory=dict,
        description="LLM parameters (model, temperature, etc.)",
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "timestamp": "2026-01-03T10:23:45.123Z",
                "phase": "build",
                "prompt": "Generate code for...",
                "params": {
                    "model": "claude-sonnet-4-20250514",
                    "temperature": 0,
                    "max_tokens": 16000,
                },
            }
        }
    }


class LLMResponse(BaseModel):
    """Captured LLM response for debugging and replay.

    Saves the full response details after LLM execution.
    Written to `llm/<seq>_response.json`.

    Attributes:
        timestamp: When the response was received (UTC)
        content: The text content from the LLM
        phase: The current execution phase
        tool_calls: List of tool calls made during execution
        stats: Token usage and timing statistics

    Example:
        >>> response = LLMResponse(
        ...     content="Here's your code...",
        ...     phase="build",
        ...     stats=LLMStats(input_tokens=4521, output_tokens=3892, duration_ms=47333)
        ... )
    """

    timestamp: datetime = Field(
        default_factory=_utc_now,
        description="When the response was received (UTC)",
    )
    content: str = Field(
        ...,
        description="The text content from the LLM",
    )
    phase: str = Field(
        ...,
        description="The current execution phase",
    )
    tool_calls: list[LLMToolCall] = Field(
        default_factory=list,
        description="List of tool calls made during execution",
    )
    stats: LLMStats = Field(
        default_factory=LLMStats,
        description="Token usage and timing statistics",
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "timestamp": "2026-01-03T10:24:32.456Z",
                "phase": "build",
                "content": "Generated code...",
                "tool_calls": [],
                "stats": {
                    "input_tokens": 4521,
                    "output_tokens": 3892,
                    "duration_ms": 47333,
                },
            }
        }
    }


class LLMStreamEvent(BaseModel):
    """A single event from the LLM stream for capture.

    Captures stream events for token-by-token replay and debugging.
    Written to `llm/<seq>_stream.jsonl` as JSONL format.

    Attributes:
        t: Relative timestamp in milliseconds since stream start
        type: Type of stream event
        content: Text content (for token/thinking events)
        id: Tool call ID (for tool events)
        name: Tool name (for tool_call_start)
        input: Tool input (for tool_call_start)
        duration_ms: Tool duration (for tool_call_end)
        success: Tool success (for tool_call_end)
        stats: Final stats (for complete event)
        error: Error message (for error event)

    Examples:
        >>> # Token event
        >>> LLMStreamEvent(t=12, type=StreamEventType.TOKEN, content="Hello")

        >>> # Tool call start
        >>> LLMStreamEvent(
        ...     t=1250,
        ...     type=StreamEventType.TOOL_CALL_START,
        ...     id="call_01",
        ...     name="create_file",
        ...     input={"path": "test.py"}
        ... )

        >>> # Completion
        >>> LLMStreamEvent(
        ...     t=45230,
        ...     type=StreamEventType.COMPLETE,
        ...     stats=LLMStats(input_tokens=4521, output_tokens=3892)
        ... )
    """

    t: int = Field(
        ...,
        description="Relative timestamp in milliseconds since stream start",
    )
    type: StreamEventType = Field(
        ...,
        description="Type of stream event",
    )
    # Optional fields based on event type
    content: str | None = Field(
        default=None,
        description="Text content (for token/thinking events)",
    )
    id: str | None = Field(
        default=None,
        description="Tool call ID (for tool events)",
    )
    name: str | None = Field(
        default=None,
        description="Tool name (for tool_call_start)",
    )
    input: dict[str, Any] | None = Field(
        default=None,
        description="Tool input (for tool_call_start)",
    )
    duration_ms: int | None = Field(
        default=None,
        description="Tool duration (for tool_call_end)",
    )
    success: bool | None = Field(
        default=None,
        description="Tool success (for tool_call_end)",
    )
    stats: LLMStats | None = Field(
        default=None,
        description="Final stats (for complete event)",
    )
    error: str | None = Field(
        default=None,
        description="Error message (for error event)",
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {"t": 0, "type": "token", "content": "I'll"},
                {"t": 12, "type": "token", "content": " create"},
                {
                    "t": 1250,
                    "type": "tool_call_start",
                    "id": "call_01",
                    "name": "create_file",
                    "input": {"path": "test.py"},
                },
                {
                    "t": 1295,
                    "type": "tool_call_end",
                    "id": "call_01",
                    "duration_ms": 45,
                    "success": True,
                },
                {
                    "t": 45230,
                    "type": "complete",
                    "stats": {"input_tokens": 4521, "output_tokens": 3892},
                },
            ]
        }
    }
