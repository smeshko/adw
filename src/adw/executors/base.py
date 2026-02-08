"""LLM Executor Protocol definition.

This module defines the Protocol for LLM execution backends, providing
a consistent interface for different LLM implementations (Claude Code,
MockExecutor for testing, etc.).
"""

from pathlib import Path
from typing import Protocol, runtime_checkable

from adw.models.llm import LLMResult


@runtime_checkable
class LLMExecutor(Protocol):
    """Protocol for LLM execution backends.

    This Protocol defines the interface that all LLM executors must implement.
    Using Protocol-based abstraction enables:
    - Dependency injection for testing (MockExecutor)
    - Multiple LLM backend support
    - Structural subtyping (no explicit inheritance required)

    Example:
        >>> class MyExecutor:
        ...     def execute(
        ...         self, prompt: str, *, timeout: int | None = None
        ...     ) -> LLMResult:
        ...         ...
        >>>
        >>> executor: LLMExecutor = MyExecutor()  # Type checks!
    """

    def execute(
        self,
        prompt: str,
        *,
        timeout: int | None = None,
        phase: str | None = None,
        cwd: Path | None = None,
        model: str | None = None,
    ) -> LLMResult:
        """Execute a prompt and return the result.

        Args:
            prompt: The prompt to send to the LLM.
            timeout: Optional timeout in seconds. If None, uses executor's default.
            phase: Optional phase name for logging and debugging purposes.
            cwd: Optional working directory for subprocess execution.
                 If None, uses current working directory (legacy mode).
                 Used for worktree isolation support (Story 10.5).
            model: Optional model identifier to use for this call.
                 If None, uses executor's default (no --model flag).

        Returns:
            LLMResult with success status, content, tool calls, and metrics.

        Raises:
            LLMTimeoutError: If execution times out.
            LLMRateLimitError: If rate limited by the API.
            LLMError: For other LLM-related errors.
        """
        ...
