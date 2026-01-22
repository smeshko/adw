"""Logging-related models for ADW.

This module contains models for structured logging:
- LogLevel: Severity levels (TRACE, DEBUG, INFO, WARN, ERROR, FATAL)
- LogCategory: Log event categories (PHASE, LLM, HOOK, STATE, ERROR, PERFORMANCE)
- LogContext: Contextual information for scoped logging
- LogEvent: A single log entry with all metadata
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

# Level ordering for filtering comparisons
# Used by LogManager and ConsoleTransport for level checks
LEVEL_ORDER: dict[LogLevel, int] = {
    LogLevel.TRACE: 0,
    LogLevel.DEBUG: 1,
    LogLevel.INFO: 2,
    LogLevel.WARN: 3,
    LogLevel.ERROR: 4,
    LogLevel.FATAL: 5,
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
