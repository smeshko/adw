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


class CommandError(ADWError):
    """Exception for command resolution failures.

    Used when a command cannot be found or resolved from the
    three-tier resolution system (project → user → bundled).

    Common error codes:
    - COMMAND_NOT_FOUND: Requested command doesn't exist
    - COMMAND_INVALID: Command exists but has invalid configuration
    - COMMAND_LOAD_FAILED: Command directory exists but failed to load

    Example:
        >>> raise CommandError(
        ...     code="COMMAND_NOT_FOUND",
        ...     message="Command 'deploy' not found",
        ...     suggestion="Check available commands with 'adw list-commands'",
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
        """Initialize a CommandError.

        Args:
            code: Unique error code (e.g., "COMMAND_NOT_FOUND").
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
        d.update(
            {
                "phase": self.phase,
                "exit_code": self.exit_code,
                "stdout": self.stdout,
                "stderr": self.stderr,
            }
        )
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
        d.update(
            {
                "timeout_seconds": self.timeout_seconds,
                "elapsed_seconds": self.elapsed_seconds,
            }
        )
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
        d.update(
            {
                "retry_after": self.retry_after,
            }
        )
        return d


class PhaseError(ADWError):
    """Exception for phase execution failures.

    Used when a phase fails to execute properly, distinct from
    hook failures or LLM errors.

    Common error codes:
    - PHASE_FAILED: Phase execution failed
    - PHASE_TIMEOUT: Phase exceeded timeout
    - PHASE_SKIPPED: Phase was skipped due to dependency failure
    - PHASE_INVALID: Invalid phase configuration

    Example:
        >>> raise PhaseError(
        ...     code="PHASE_FAILED",
        ...     message="Phase 'build' failed after 3 retries",
        ...     phase="build",
        ...     suggestion="Check the phase logs for details",
        ... )
    """

    def __init__(
        self,
        code: str,
        message: str,
        *,
        phase: str,
        suggestion: str | None = None,
        recoverable: bool = False,
    ) -> None:
        """Initialize a PhaseError.

        Args:
            code: Unique error code (e.g., "PHASE_FAILED").
            message: Human-readable error message.
            phase: The phase that failed (e.g., "build", "verify").
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

    def to_dict(self) -> dict[str, Any]:
        """Serialize error to dictionary for structured logging.

        Returns:
            Dictionary containing all error attributes including phase.
        """
        d = super().to_dict()
        d.update(
            {
                "phase": self.phase,
            }
        )
        return d


class StateError(ADWError):
    """Exception for state persistence and loading errors.

    Used for issues with run state, context files, and snapshots.

    Common error codes:
    - CONTEXT_CORRUPTED: State file is corrupted or invalid
    - SNAPSHOT_FAILED: Failed to create or load state snapshot
    - RUN_NOT_FOUND: Specified run ID doesn't exist

    Example:
        >>> raise StateError(
        ...     code="RUN_NOT_FOUND",
        ...     message="Run 'abc123' not found",
        ...     suggestion="Use 'adw list' to see available runs",
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
        """Initialize a StateError.

        Args:
            code: Unique error code (e.g., "RUN_NOT_FOUND").
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


class ValidationError(ADWError):
    """Exception for schema validation failures.

    Used when LLM output or configuration fails to match expected schema.
    Includes detailed field-level error information.

    Example:
        >>> raise ValidationError(
        ...     code="VALIDATION_FAILED",
        ...     message="LLM output failed schema validation",
        ...     field_errors=[
        ...         {"field": "name", "error": "required field missing"},
        ...         {"field": "age", "error": "must be a positive integer"},
        ...     ],
        ...     schema_path="schemas/output.json",
        ...     suggestion="Check the prompt or adjust the schema",
        ... )
    """

    def __init__(
        self,
        code: str,
        message: str,
        *,
        field_errors: list[dict[str, str]] | None = None,
        schema_path: str | None = None,
        suggestion: str | None = None,
        recoverable: bool = False,
    ) -> None:
        """Initialize a ValidationError.

        Args:
            code: Unique error code (e.g., "VALIDATION_FAILED").
            message: Human-readable error message.
            field_errors: List of field-level validation errors.
            schema_path: Path to the schema that failed validation.
            suggestion: Optional actionable next step.
            recoverable: Whether the operation can be retried (default False).
        """
        super().__init__(
            code=code,
            message=message,
            suggestion=suggestion,
            recoverable=recoverable,
        )
        self.field_errors = field_errors if field_errors is not None else []
        self.schema_path = schema_path

    def to_dict(self) -> dict[str, Any]:
        """Serialize error to dictionary for structured logging.

        Returns:
            Dictionary containing all error attributes including validation fields.
        """
        d = super().to_dict()
        d.update(
            {
                "field_errors": self.field_errors,
                "schema_path": self.schema_path,
            }
        )
        return d
