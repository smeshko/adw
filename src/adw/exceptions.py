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
