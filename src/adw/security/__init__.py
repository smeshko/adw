"""ADW Security module.

This package provides security interceptor functionality for blocking
dangerous LLM tool calls.

Key components:
- defaults: Default blocked patterns for shell commands and file access
- patterns: Pattern matching engine for security checks
- interceptor: Security interceptor for blocking dangerous operations
- suggestions: Alternative command suggestions for blocked patterns
- override: Override logging for --allow-dangerous mode
"""

from adw.security.defaults import (
    ALLOWED_ENV_PATTERNS,
    DEFAULT_FILE_PATTERNS,
    DEFAULT_SHELL_PATTERNS,
    PATTERN_METADATA,
)
from adw.security.interceptor import (
    SecurityCheckResponse,
    SecurityCheckResult,
    SecurityInterceptor,
)
from adw.security.override import (
    OverrideLogger,
    get_override_logger,
    reset_override_logger,
)
from adw.security.patterns import (
    PatternMatch,
    PatternMatcher,
)
from adw.security.suggestions import (
    SuggestionFormatter,
    get_category_examples,
    get_override_instruction,
)

__all__: list[str] = [
    # Interceptor (Story 3.6)
    "SecurityCheckResponse",
    "SecurityCheckResult",
    "SecurityInterceptor",
    # Defaults
    "ALLOWED_ENV_PATTERNS",
    "DEFAULT_FILE_PATTERNS",
    "DEFAULT_SHELL_PATTERNS",
    "PATTERN_METADATA",
    # Override logging
    "OverrideLogger",
    "get_override_logger",
    "reset_override_logger",
    # Pattern matching
    "PatternMatch",
    "PatternMatcher",
    # Suggestions
    "SuggestionFormatter",
    "get_category_examples",
    "get_override_instruction",
]
