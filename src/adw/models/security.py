"""Security-related Pydantic models.

This module contains models for security configuration and tool call logging,
including blocked pattern definitions and security interceptor configuration.
"""

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
        category: Category of the pattern (destructive/permission/etc.)
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

    pattern: str = Field(description="Regex pattern to match against commands")
    description: str = Field(description="Human-readable description of pattern")
    severity: PatternSeverity = Field(
        default="warning", description="Severity level (critical/warning/info)"
    )
    category: PatternCategory = Field(
        description="Category (destructive/permission/git_dangerous/secret_access)"
    )
    alternative: str = Field(
        default="", description="Suggested safe alternative command or approach"
    )


class SecurityConfig(BaseModel):
    """Security configuration for the ADW runner.

    Configures which patterns are blocked and which files are
    protected from access.

    Attributes:
        blocked_patterns: Additional patterns to block (merged with defaults)
        blocked_env_files: File patterns to block (in addition to defaults)

    Example:
        >>> config = SecurityConfig(
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
    blocked_env_files: list[str] = Field(
        default_factory=list,
        description="Additional file patterns to block (in addition to defaults)",
    )


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
