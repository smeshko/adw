"""Security-related Pydantic models.

This module contains models for security configuration and tool call logging,
including blocked pattern definitions and security interceptor configuration.
"""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


# Valid pattern categories for security blocking
PatternCategory = Literal["destructive", "permission", "git_dangerous", "secret_access"]

# Valid severity levels for security patterns
PatternSeverity = Literal["critical", "warning", "info"]


class BlockedPattern(BaseModel):
    """Configuration for a blocked shell command or file pattern.

    Blocked patterns define dangerous operations that should be prevented
    by the security interceptor. Each pattern includes metadata to help
    users understand why it was blocked and what alternatives exist.

    Attributes:
        pattern: Regex pattern to match against commands/paths
        description: Human-readable description of what this pattern blocks
        severity: How severe the security risk is (critical/warning/info)
        category: Category of the pattern (destructive/permission/git_dangerous/secret_access)
        alternative: Suggested safe alternative command or approach

    Example:
        >>> pattern = BlockedPattern(
        ...     pattern=r"rm\\s+-rf\\s+/",
        ...     description="Recursive delete of root directory",
        ...     severity="critical",
        ...     category="destructive",
        ...     alternative="Use specific paths: rm -rf ./node_modules",
        ... )
    """

    pattern: str = Field(description="Regex pattern to match against commands/paths")
    description: str = Field(description="Human-readable description of what this blocks")
    severity: PatternSeverity = Field(
        default="warning", description="Severity level (critical/warning/info)"
    )
    category: PatternCategory = Field(
        description="Category of the pattern (destructive/permission/git_dangerous/secret_access)"
    )
    alternative: str = Field(
        default="", description="Suggested safe alternative command or approach"
    )


class SecurityConfig(BaseModel):
    """Security configuration for the ADW runner.

    Configures which patterns are blocked, whether blocking is enforced,
    and which files are protected from access.

    Attributes:
        blocked_patterns: Additional patterns to block (merged with defaults)
        allow_dangerous: If True, log warnings instead of blocking
        blocked_env_files: File patterns to block (in addition to defaults)

    Example:
        >>> config = SecurityConfig(
        ...     allow_dangerous=False,
        ...     blocked_patterns=[
        ...         BlockedPattern(
        ...             pattern=r"npm\\s+publish",
        ...             description="Publishing to npm",
        ...             category="permission",
        ...         )
        ...     ],
        ... )
    """

    blocked_patterns: list[BlockedPattern] = Field(
        default_factory=list,
        description="Additional patterns to block (merged with defaults)",
    )
    allow_dangerous: bool = Field(
        default=False, description="If True, log warnings instead of blocking"
    )
    blocked_env_files: list[str] = Field(
        default_factory=list,
        description="Additional file patterns to block (in addition to defaults)",
    )


class ToolCallLog(BaseModel):
    """Log entry for a tool call execution.

    Records details about every tool call made by the LLM, including
    whether it was blocked and why. Written to tools.jsonl.

    Attributes:
        timestamp: When the tool call occurred
        tool_name: Name of the tool (e.g., "Bash", "Read", "Write")
        arguments: Arguments passed to the tool
        result_summary: Brief summary of the result or "blocked"
        duration_ms: Time taken to execute (0 if blocked)
        blocked: Whether the call was blocked by security
        block_reason: Why it was blocked (if blocked)

    Example:
        >>> log = ToolCallLog(
        ...     timestamp=datetime.now(),
        ...     tool_name="Bash",
        ...     arguments={"command": "rm -rf /tmp/test"},
        ...     result_summary="blocked",
        ...     duration_ms=0,
        ...     blocked=True,
        ...     block_reason="Matches dangerous pattern: rm -rf",
        ... )
    """

    timestamp: datetime = Field(default_factory=datetime.now)
    tool_name: str = Field(description="Name of the tool called")
    arguments: dict[str, Any] = Field(
        default_factory=dict, description="Arguments passed to the tool"
    )
    result_summary: str = Field(
        default="", description="Brief summary of the result or 'blocked'"
    )
    duration_ms: int = Field(default=0, description="Time taken to execute (0 if blocked)")
    blocked: bool = Field(default=False, description="Whether the call was blocked")
    block_reason: str | None = Field(
        default=None, description="Why it was blocked (if blocked)"
    )
