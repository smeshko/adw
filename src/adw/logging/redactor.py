"""Secret redaction for log output.

This module provides the Redactor class for removing sensitive data from
log output, and RedactingFilter, which applies a Redactor to every record
a logging handler emits (console and live.log).

Redaction covers:
- API keys (Bearer tokens, OpenAI, AWS, GitHub)
- Environment variable values with sensitive names
- Custom user-defined patterns from project.yaml

Usage:
    >>> from adw.logging.redactor import Redactor, DEFAULT_REDACTION_PATTERNS
    >>> redactor = Redactor(DEFAULT_REDACTION_PATTERNS)
    >>> redactor.redact("Authorization: Bearer sk-abc123xyz")
    'Authorization: Bearer [REDACTED]'
"""

import logging
import re

# =============================================================================
# DEFAULT REDACTION PATTERNS
#
# These patterns cover common secret formats. Custom patterns can be added
# via project.yaml configuration.
# =============================================================================

DEFAULT_REDACTION_PATTERNS: list[str] = [
    # ==========================================================================
    # API Key Patterns
    # ==========================================================================
    # Bearer tokens (OAuth, JWT-style)
    r"Bearer\s+[A-Za-z0-9\-_\.]+",
    # OpenAI API keys (sk-...)
    r"sk-[A-Za-z0-9]{20,}",
    # AWS Access Key ID (starts with AKIA)
    r"AKIA[A-Z0-9]{16}",
    # AWS Secret Access Key (40 chars, base64-ish)
    r"(?<![A-Za-z0-9/+])[A-Za-z0-9/+]{40}(?![A-Za-z0-9/+=])",
    # GitHub Personal Access Token (classic)
    r"ghp_[A-Za-z0-9]{36}",
    # GitHub OAuth Token
    r"gho_[A-Za-z0-9]{36}",
    # GitHub App Token
    r"ghu_[A-Za-z0-9]{36}",
    # GitHub Server-to-Server Token
    r"ghs_[A-Za-z0-9]{36}",
    # GitHub Refresh Token
    r"ghr_[A-Za-z0-9]{36}",
    # GitHub Fine-Grained PAT
    r"github_pat_[A-Za-z0-9_]{82}",
    # Anthropic API keys (typically sk-ant-api03-xxx format, variable length)
    r"sk-ant-[A-Za-z0-9\-]{20,}",
    # ==========================================================================
    # Generic Secret Patterns (case-insensitive)
    # ==========================================================================
    # api_key = "value" or api-key: value patterns
    r"(?i)api[_-]?key['\"]?\s*[:=]\s*['\"]?[A-Za-z0-9\-_\.]{8,}['\"]?",
    # secret_key = "value" patterns
    r"(?i)secret[_-]?key['\"]?\s*[:=]\s*['\"]?[A-Za-z0-9\-_\.]{8,}['\"]?",
    # password = "value" patterns
    r"(?i)password['\"]?\s*[:=]\s*['\"]?[^\s'\"]{4,}['\"]?",
    # token = "value" patterns
    r"(?i)(?<!_)token['\"]?\s*[:=]\s*['\"]?[A-Za-z0-9\-_\.]{8,}['\"]?",
    # auth = "value" patterns
    r"(?i)auth[_-]?(?:key|token|secret)['\"]?\s*[:=]\s*['\"]?[A-Za-z0-9\-_\.]{8,}['\"]?",
]

# =============================================================================
# SENSITIVE ENVIRONMENT VARIABLE PATTERNS
#
# Environment variable names matching these patterns will have their values
# redacted when logging environment dictionaries.
# =============================================================================

SENSITIVE_ENV_PATTERNS: list[str] = [
    # Suffix patterns (e.g., DATABASE_PASSWORD, AWS_SECRET)
    r".*_KEY$",
    r".*_SECRET$",
    r".*_TOKEN$",
    r".*_PASSWORD$",
    r".*_API_KEY$",
    r".*_AUTH$",
    r".*_CREDENTIAL.*",
    # Exact matches (common standalone names)
    r"^API_KEY$",
    r"^APIKEY$",
    r"^SECRET$",
    r"^TOKEN$",
    r"^PASSWORD$",
    r"^AUTH$",
    r"^CREDENTIALS?$",
]

# Placeholder used for redacted content
REDACTED_PLACEHOLDER = "[REDACTED]"


class Redactor:
    """Redacts sensitive data from strings and environment dictionaries.

    The Redactor applies regex patterns to identify and replace sensitive
    content with a placeholder. It supports:
    - Pattern-based string redaction
    - Environment variable name matching

    Attributes:
        patterns: Compiled regex patterns for redaction
        env_patterns: Compiled patterns for sensitive env var names

    Example:
        >>> patterns = ["Bearer\\s+[A-Za-z0-9]+"]
        >>> redactor = Redactor(patterns)
        >>> redactor.redact("Auth: Bearer abc123")
        'Auth: [REDACTED]'
    """

    def __init__(
        self,
        patterns: list[str],
        env_patterns: list[str] | None = None,
    ) -> None:
        """Initialize the redactor with patterns.

        Args:
            patterns: List of regex patterns to redact
            env_patterns: List of patterns for sensitive env var names.
                Defaults to SENSITIVE_ENV_PATTERNS if not provided.
        """
        self._patterns: list[re.Pattern[str]] = [re.compile(p) for p in patterns]
        env_pats = env_patterns if env_patterns is not None else SENSITIVE_ENV_PATTERNS
        self._env_patterns: list[re.Pattern[str]] = [re.compile(p) for p in env_pats]

    @property
    def patterns(self) -> list[re.Pattern[str]]:
        """Get the compiled redaction patterns."""
        return list(self._patterns)

    @property
    def env_patterns(self) -> list[re.Pattern[str]]:
        """Get the compiled environment variable patterns."""
        return list(self._env_patterns)

    def redact(self, content: str) -> str:
        """Redact sensitive data from a string.

        Applies all configured patterns to the input string, replacing
        matches with [REDACTED].

        Args:
            content: The string to redact

        Returns:
            String with sensitive data replaced by [REDACTED]

        Example:
            >>> redactor = Redactor(DEFAULT_REDACTION_PATTERNS)
            >>> redactor.redact("API key is sk-abc123xyz")
            'API key is [REDACTED]'
        """
        result = content
        for pattern in self._patterns:
            result = pattern.sub(REDACTED_PLACEHOLDER, result)
        return result

    def should_redact_env(self, name: str) -> bool:
        """Check if an environment variable name is sensitive.

        Args:
            name: Environment variable name to check

        Returns:
            True if the name matches a sensitive pattern

        Example:
            >>> redactor = Redactor([])
            >>> redactor.should_redact_env("DATABASE_PASSWORD")
            True
            >>> redactor.should_redact_env("DEBUG_MODE")
            False
        """
        return any(pattern.match(name) for pattern in self._env_patterns)

    def redact_env_dict(self, env: dict[str, str]) -> dict[str, str]:
        """Redact values for sensitive environment variables.

        Creates a new dictionary with values redacted for any env var
        whose name matches a sensitive pattern.

        Args:
            env: Dictionary of environment variables

        Returns:
            New dictionary with sensitive values redacted

        Example:
            >>> redactor = Redactor([])
            >>> redactor.redact_env_dict({"API_KEY": "secret123", "DEBUG": "true"})
            {'API_KEY': '[REDACTED]', 'DEBUG': 'true'}
        """
        return {
            k: REDACTED_PLACEHOLDER if self.should_redact_env(k) else v
            for k, v in env.items()
        }


class RedactingFilter(logging.Filter):
    """Redacts every record a handler emits.

    Attach it to a handler rather than a logger: a logger's filters only see
    records logged on that logger, while a handler's filters see every record
    that propagates to it. The message is formatted with its args first, then
    redacted, and so is any exception or stack text. Filtering a record twice
    is harmless, because the placeholder matches no pattern.

    Example:
        >>> handler.addFilter(RedactingFilter(get_redactor()))
    """

    def __init__(self, redactor: Redactor) -> None:
        """Initialize the filter.

        Args:
            redactor: The redactor applied to each record's text
        """
        super().__init__()
        self._redactor = redactor

    def filter(self, record: logging.LogRecord) -> bool:
        """Redact the record's message, exception text and stack text in place.

        Args:
            record: The record about to be emitted

        Returns:
            Always True: redaction never drops a record
        """
        record.msg = self._redactor.redact(record.getMessage())
        record.args = None
        if record.exc_info and not record.exc_text:
            record.exc_text = logging.Formatter().formatException(record.exc_info)
        if record.exc_text:
            record.exc_text = self._redactor.redact(record.exc_text)
        if record.stack_info:
            record.stack_info = self._redactor.redact(record.stack_info)
        return True


# Module-level default redactor instance
_default_redactor: Redactor | None = None


def get_redactor() -> Redactor:
    """Get the default redactor instance.

    Returns a module-level Redactor instance initialized with
    DEFAULT_REDACTION_PATTERNS, creating it on first call.

    Returns:
        The default Redactor instance
    """
    global _default_redactor
    if _default_redactor is None:
        _default_redactor = Redactor(DEFAULT_REDACTION_PATTERNS)
    return _default_redactor


def reset_redactor() -> None:
    """Reset the default redactor instance.

    Clears the module-level default redactor, allowing a fresh instance
    to be created on the next get_redactor() call. Useful for testing.
    """
    global _default_redactor
    _default_redactor = None


def configure_redactor(
    patterns: list[str] | None = None,
    env_patterns: list[str] | None = None,
    disable_defaults: bool = False,
) -> Redactor:
    """Configure and return a new default redactor.

    Args:
        patterns: Additional patterns to add (merged with defaults unless
            disable_defaults is True)
        env_patterns: Custom env var patterns (replaces defaults if provided)
        disable_defaults: If True, only use provided patterns

    Returns:
        The configured Redactor instance
    """
    global _default_redactor

    if disable_defaults:
        all_patterns = patterns or []
    else:
        all_patterns = list(DEFAULT_REDACTION_PATTERNS)
        if patterns:
            all_patterns.extend(patterns)

    _default_redactor = Redactor(all_patterns, env_patterns)
    return _default_redactor
