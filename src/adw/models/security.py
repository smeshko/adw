"""Security models for ADW tool call protection.

This module contains models for security configuration, blocked patterns,
and tool call logging. Used by the security interceptor to validate
and log LLM tool calls.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class SecuritySeverity(str, Enum):
    """Severity level for blocked patterns.

    Determines the urgency and logging level when a pattern is matched.
    """

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class BlockedPattern(BaseModel):
    """A pattern that should be blocked by the security interceptor.

    Attributes:
        pattern: Regex pattern to match against commands or file paths.
        description: Human-readable description of why this is blocked.
        severity: Severity level of the security issue.

    Example:
        >>> pattern = BlockedPattern(
        ...     pattern=r"rm\\s+-rf",
        ...     description="Recursive delete command",
        ...     severity=SecuritySeverity.CRITICAL,
        ... )
        >>> pattern.pattern
        'rm\\\\s+-rf'
    """

    pattern: str = Field(
        ...,
        description="Regex pattern to match against commands or file paths",
    )
    description: str = Field(
        ...,
        description="Human-readable description of why this is blocked",
    )
    severity: SecuritySeverity = Field(
        default=SecuritySeverity.HIGH,
        description="Severity level of the security issue",
    )


class SecurityConfig(BaseModel):
    """Configuration for security features.

    Controls which commands and file access patterns are blocked,
    and allows overriding security checks when explicitly permitted.

    Attributes:
        blocked_patterns: List of custom patterns to block.
        allow_dangerous: If True, log warnings instead of blocking.
        blocked_env_files: File patterns that should be blocked from reading.
        allowed_env_patterns: Exception patterns that are safe to read.

    Example:
        >>> config = SecurityConfig(
        ...     blocked_patterns=[
        ...         BlockedPattern(
        ...             pattern=r"rm\\s+-rf",
        ...             description="Dangerous delete",
        ...             severity=SecuritySeverity.CRITICAL,
        ...         )
        ...     ]
        ... )
        >>> config.allow_dangerous
        False
    """

    blocked_patterns: list[BlockedPattern] = Field(
        default_factory=list,
        description="List of custom patterns to block",
    )
    allow_dangerous: bool = Field(
        default=False,
        description="If True, log warnings instead of blocking",
    )
    blocked_env_files: list[str] = Field(
        default_factory=lambda: [".env", ".adw.env"],
        description="File patterns that should be blocked from reading",
    )
    allowed_env_patterns: list[str] = Field(
        default_factory=lambda: [".env.example", ".env.sample", ".env.template"],
        description="Exception patterns that are safe to read",
    )


class ToolCallLog(BaseModel):
    """Log entry for a tool call made by the LLM.

    Captures all relevant information about tool calls for
    audit trail and debugging purposes.

    Attributes:
        timestamp: When the tool call was made.
        tool_name: Name of the tool being called (e.g., "Bash", "Read").
        arguments: Arguments passed to the tool.
        result_summary: Brief summary of the result (e.g., "success", "blocked").
        duration_ms: How long the tool call took in milliseconds.
        blocked: Whether the tool call was blocked by security.
        block_reason: Why the tool call was blocked, if applicable.

    Example:
        >>> log_entry = ToolCallLog(
        ...     tool_name="Bash",
        ...     arguments={"command": "ls -la"},
        ...     result_summary="success",
        ...     duration_ms=150,
        ... )
        >>> log_entry.blocked
        False
    """

    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When the tool call was made",
    )
    tool_name: str = Field(
        ...,
        description="Name of the tool being called",
    )
    arguments: dict[str, Any] = Field(
        ...,
        description="Arguments passed to the tool",
    )
    result_summary: str = Field(
        ...,
        description="Brief summary of the result",
    )
    duration_ms: int = Field(
        ...,
        ge=0,
        description="How long the tool call took in milliseconds",
    )
    blocked: bool = Field(
        default=False,
        description="Whether the tool call was blocked by security",
    )
    block_reason: str | None = Field(
        default=None,
        description="Why the tool call was blocked, if applicable",
    )
