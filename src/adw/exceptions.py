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
