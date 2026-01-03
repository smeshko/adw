"""Security module for ADW tool call protection.

This module provides security checks for LLM tool calls to prevent
dangerous operations like destructive shell commands or sensitive
file access.

Example:
    >>> from adw.security import SecurityInterceptor, SecurityCheckResult
    >>> interceptor = SecurityInterceptor()
    >>> response = interceptor.check_tool_call("Bash", {"command": "rm -rf /"})
    >>> response.result == SecurityCheckResult.BLOCKED
    True
"""

from adw.security.interceptor import (
    SecurityCheckResponse,
    SecurityCheckResult,
    SecurityInterceptor,
)
from adw.security.patterns import (
    ALLOWED_FILE_PATTERNS,
    BLOCKED_FILE_PATTERNS,
    BLOCKED_SHELL_PATTERNS,
    is_allowed_env_file,
    match_file_pattern,
    match_shell_pattern,
)

__all__: list[str] = [
    # Interceptor
    "SecurityInterceptor",
    "SecurityCheckResult",
    "SecurityCheckResponse",
    # Pattern utilities
    "BLOCKED_SHELL_PATTERNS",
    "BLOCKED_FILE_PATTERNS",
    "ALLOWED_FILE_PATTERNS",
    "match_shell_pattern",
    "match_file_pattern",
    "is_allowed_env_file",
]
