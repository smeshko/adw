"""ADW Security module.

This package provides security interceptor functionality for blocking
dangerous LLM tool calls and logging tool execution.

Key components:
- defaults: Default blocked patterns for shell commands and file access
- patterns: Pattern matching engine for security checks
- suggestions: Alternative command suggestions for blocked patterns
"""

from adw.security.defaults import (
    ALLOWED_ENV_PATTERNS,
    DEFAULT_FILE_PATTERNS,
    DEFAULT_SHELL_PATTERNS,
    PATTERN_METADATA,
)

__all__: list[str] = [
    "ALLOWED_ENV_PATTERNS",
    "DEFAULT_FILE_PATTERNS",
    "DEFAULT_SHELL_PATTERNS",
    "PATTERN_METADATA",
]
