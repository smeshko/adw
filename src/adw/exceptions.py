"""ADW Exception hierarchy.

This module defines the custom exception hierarchy for ADW with typed errors
that provide consistent error handling and actionable error messages.
"""

from typing import Any


class ADWError(Exception):
    """Base exception for all ADW errors.

    All ADW exceptions inherit from this class and provide:
    - code: A unique error code (e.g., "CONFIG_NOT_FOUND")
    - message: A human-readable error message
    - suggestion: An optional actionable suggestion for resolution
    - recoverable: Whether the error can be retried

    Example:
        >>> raise ADWError(
        ...     code="CONFIG_NOT_FOUND",
        ...     message="Configuration file not found",
        ...     suggestion="Create an adw.yaml file in the project root",
        ...     recoverable=False,
        ... )
    """

    def __init__(
        self,
        code: str,
        message: str,
        *,
        suggestion: str | None = None,
        recoverable: bool = False,
    ) -> None:
        """Initialize an ADWError.

        Args:
            code: Unique error code (e.g., "HOOK_FAILED").
            message: Human-readable error message.
            suggestion: Optional actionable next step.
            recoverable: Whether the operation can be retried.
        """
        self.code = code
        self.message = message
        self.suggestion = suggestion
        self.recoverable = recoverable
        super().__init__(self.message)

    def __str__(self) -> str:
        """Format error for user-friendly display.

        Returns:
            Formatted error string suitable for Rich Panel display.
        """
        parts = [f"[{self.code}] {self.message}"]
        if self.suggestion:
            parts.append(f"Suggestion: {self.suggestion}")
        return "\n".join(parts)

    def to_dict(self) -> dict[str, Any]:
        """Serialize error to dictionary for structured logging.

        Returns:
            Dictionary containing all error attributes.
        """
        return {
            "code": self.code,
            "message": self.message,
            "suggestion": self.suggestion,
            "recoverable": self.recoverable,
        }


class ConfigError(ADWError):
    """Exception for configuration-related errors.

    Used for issues with configuration files, missing settings,
    or invalid configuration values.

    Common error codes:
    - CONFIG_NOT_FOUND: Configuration file doesn't exist
    - INVALID_CONFIG: Configuration file has invalid content
    - COMMAND_NOT_FOUND: Requested command not found in config

    Example:
        >>> raise ConfigError(
        ...     code="CONFIG_NOT_FOUND",
        ...     message="Configuration file not found at ./adw.yaml",
        ...     suggestion="Create an adw.yaml file in the project root",
        ... )
    """

    def __init__(
        self,
        code: str,
        message: str,
        *,
        suggestion: str | None = None,
        recoverable: bool = False,
    ) -> None:
        """Initialize a ConfigError.

        Args:
            code: Unique error code (e.g., "CONFIG_NOT_FOUND").
            message: Human-readable error message.
            suggestion: Optional actionable next step.
            recoverable: Whether the operation can be retried (default False).
        """
        super().__init__(
            code=code,
            message=message,
            suggestion=suggestion,
            recoverable=recoverable,
        )


class HookError(ADWError):
    """Exception for hook script execution failures.

    Used when pre-hooks or post-hooks fail during phase execution.
    Includes additional context about the hook execution.

    Common error codes:
    - HOOK_FAILED: Hook script exited with non-zero status
    - HOOK_TIMEOUT: Hook script exceeded timeout

    Example:
        >>> raise HookError(
        ...     code="HOOK_FAILED",
        ...     message="Pre-hook exited with code 1",
        ...     suggestion="Check hook script for errors",
        ...     phase="build",
        ...     exit_code=1,
        ...     stderr="Permission denied",
        ... )
    """

    def __init__(
        self,
        code: str,
        message: str,
        *,
        phase: str,
        exit_code: int | None = None,
        stdout: str = "",
        stderr: str = "",
        suggestion: str | None = None,
        recoverable: bool = False,
    ) -> None:
        """Initialize a HookError.

        Args:
            code: Unique error code (e.g., "HOOK_FAILED").
            message: Human-readable error message.
            phase: The phase where the hook failed (e.g., "build").
            exit_code: The exit code of the hook script, if available.
            stdout: Captured stdout from the hook execution.
            stderr: Captured stderr from the hook execution.
            suggestion: Optional actionable next step.
            recoverable: Whether the operation can be retried (default False).
        """
        super().__init__(
            code=code,
            message=message,
            suggestion=suggestion,
            recoverable=recoverable,
        )
        self.phase = phase
        self.exit_code = exit_code
        self.stdout = stdout
        self.stderr = stderr

    def to_dict(self) -> dict[str, Any]:
        """Serialize error to dictionary for structured logging.

        Returns:
            Dictionary containing all error attributes including hook-specific fields.
        """
        d = super().to_dict()
        d.update({
            "phase": self.phase,
            "exit_code": self.exit_code,
            "stdout": self.stdout,
            "stderr": self.stderr,
        })
        return d


class LLMError(ADWError):
    """Base exception for LLM-related errors.

    Used for issues with Claude Code or other LLM interactions.
    Subclasses handle specific failure modes like timeouts and rate limits.

    Example:
        >>> raise LLMError(
        ...     code="LLM_ERROR",
        ...     message="LLM call failed unexpectedly",
        ...     suggestion="Check Claude Code configuration",
        ... )
    """

    def __init__(
        self,
        code: str,
        message: str,
        *,
        suggestion: str | None = None,
        recoverable: bool = False,
    ) -> None:
        """Initialize an LLMError.

        Args:
            code: Unique error code (e.g., "LLM_ERROR").
            message: Human-readable error message.
            suggestion: Optional actionable next step.
            recoverable: Whether the operation can be retried (default False).
        """
        super().__init__(
            code=code,
            message=message,
            suggestion=suggestion,
            recoverable=recoverable,
        )


class LLMTimeoutError(LLMError):
    """Exception for LLM call timeouts.

    Used when an LLM call exceeds the configured timeout.
    This error is recoverable by default since retrying may succeed.

    Example:
        >>> raise LLMTimeoutError(
        ...     code="LLM_TIMEOUT",
        ...     message="LLM call timed out after 300 seconds",
        ...     timeout_seconds=300,
        ...     elapsed_seconds=300,
        ...     suggestion="Consider increasing the timeout or simplifying the prompt",
        ... )
    """

    def __init__(
        self,
        code: str,
        message: str,
        *,
        timeout_seconds: int,
        elapsed_seconds: int,
        suggestion: str | None = None,
        recoverable: bool = True,
    ) -> None:
        """Initialize an LLMTimeoutError.

        Args:
            code: Unique error code (e.g., "LLM_TIMEOUT").
            message: Human-readable error message.
            timeout_seconds: The configured timeout in seconds.
            elapsed_seconds: How long the call ran before timing out.
            suggestion: Optional actionable next step.
            recoverable: Whether the operation can be retried (default True).
        """
        super().__init__(
            code=code,
            message=message,
            suggestion=suggestion,
            recoverable=recoverable,
        )
        self.timeout_seconds = timeout_seconds
        self.elapsed_seconds = elapsed_seconds

    def to_dict(self) -> dict[str, Any]:
        """Serialize error to dictionary for structured logging.

        Returns:
            Dictionary containing all error attributes including timeout fields.
        """
        d = super().to_dict()
        d.update({
            "timeout_seconds": self.timeout_seconds,
            "elapsed_seconds": self.elapsed_seconds,
        })
        return d


class LLMRateLimitError(LLMError):
    """Exception for LLM API rate limiting.

    Used when the LLM API returns a rate limit error.
    This error is recoverable by default since waiting and retrying may succeed.

    Example:
        >>> raise LLMRateLimitError(
        ...     code="LLM_RATE_LIMIT",
        ...     message="Rate limited by Claude API",
        ...     retry_after=60,
        ...     suggestion="Wait before retrying",
        ... )
    """

    def __init__(
        self,
        code: str,
        message: str,
        *,
        retry_after: int | None = None,
        suggestion: str | None = None,
        recoverable: bool = True,
    ) -> None:
        """Initialize an LLMRateLimitError.

        Args:
            code: Unique error code (e.g., "LLM_RATE_LIMIT").
            message: Human-readable error message.
            retry_after: Seconds to wait before retrying, if provided by API.
            suggestion: Optional actionable next step.
            recoverable: Whether the operation can be retried (default True).
        """
        super().__init__(
            code=code,
            message=message,
            suggestion=suggestion,
            recoverable=recoverable,
        )
        self.retry_after = retry_after

    def to_dict(self) -> dict[str, Any]:
        """Serialize error to dictionary for structured logging.

        Returns:
            Dictionary containing all error attributes including retry_after.
        """
        d = super().to_dict()
        d.update({
            "retry_after": self.retry_after,
        })
        return d
