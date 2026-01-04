"""Mock LLM Executor for testing.

This module provides a MockExecutor that implements the LLMExecutor protocol
for deterministic testing without calling Claude Code.
"""

from collections import deque
from typing import Any

from adw.exceptions import LLMError
from adw.models.llm import LLMResult, ToolCall


class MockExecutor:
    """Mock LLM executor for testing.

    Provides deterministic responses for testing LLM-dependent code
    without making actual LLM calls. Supports:
    - Configurable response queuing
    - Failure injection
    - Call tracking for assertions

    Example:
        >>> executor = MockExecutor()
        >>> executor.configure_responses([{"content": "Hello, World!"}])
        >>> result = executor.execute("Say hello")
        >>> result.content
        'Hello, World!'
        >>> executor.call_count
        1
    """

    def __init__(self) -> None:
        """Initialize the MockExecutor with empty queues."""
        self._responses: deque[LLMResult] = deque()
        self._failures: deque[LLMError | None] = deque()
        self._all_prompts: list[str] = []

    def configure_responses(self, responses: list[dict[str, Any]]) -> None:
        """Queue responses for subsequent execute() calls.

        Each response dict should contain fields matching LLMResult:
        - content: str (required)
        - tool_calls: list[dict] (optional)
        - tokens_used: int (optional, default 100)
        - duration_ms: int (optional, default 1000)

        Args:
            responses: List of response dictionaries to queue.

        Example:
            >>> executor.configure_responses([
            ...     {"content": "First response"},
            ...     {"content": "Second response", "tokens_used": 200},
            ... ])
        """
        self._responses.clear()
        for r in responses:
            tool_calls = [
                ToolCall(**tc) if isinstance(tc, dict) else tc
                for tc in r.get("tool_calls", [])
            ]
            self._responses.append(
                LLMResult(
                    success=True,
                    content=r.get("content", ""),
                    tool_calls=tool_calls,
                    tokens_used=r.get("tokens_used", 100),
                    duration_ms=r.get("duration_ms", 1000),
                )
            )

    def configure_failures(self, failures: list[LLMError | None]) -> None:
        """Queue failures for subsequent execute() calls.

        Each entry can be:
        - None: Success (use configured response or default)
        - LLMError subclass: Raise this exception

        Args:
            failures: List of failures or None for success.

        Example:
            >>> executor.configure_failures([
            ...     LLMTimeoutError(...),  # First call fails
            ...     None,  # Second call succeeds
            ... ])
        """
        self._failures.clear()
        self._failures.extend(failures)

    def execute(
        self, prompt: str, *, timeout: int | None = None, phase: str | None = None
    ) -> LLMResult:
        """Execute a mock prompt.

        Args:
            prompt: The prompt being "sent" (stored for tracking).
            timeout: Ignored in mock (for interface compatibility).
            phase: Ignored in mock (for interface compatibility).

        Returns:
            LLMResult from configured responses or a default.

        Raises:
            LLMError: If a failure was configured for this call.
        """
        self._all_prompts.append(prompt)

        # Check for configured failure
        if self._failures:
            failure = self._failures.popleft()
            if failure is not None:
                raise failure

        # Return configured response
        if self._responses:
            return self._responses.popleft()

        # Default response
        return LLMResult(
            success=True,
            content="Mock response",
            tokens_used=50,
            duration_ms=100,
        )

    @property
    def call_count(self) -> int:
        """Return the number of times execute() has been called."""
        return len(self._all_prompts)

    @property
    def last_prompt(self) -> str | None:
        """Return the most recent prompt, or None if no calls made."""
        return self._all_prompts[-1] if self._all_prompts else None

    @property
    def all_prompts(self) -> list[str]:
        """Return a copy of all prompts received."""
        return self._all_prompts.copy()

    def assert_called_once(self) -> None:
        """Assert that execute() was called exactly once.

        Raises:
            AssertionError: If call count is not 1.
        """
        if self.call_count != 1:
            msg = f"Expected 1 call, got {self.call_count}"
            raise AssertionError(msg)

    def assert_called_with(self, prompt: str) -> None:
        """Assert that the last call used the given prompt.

        Args:
            prompt: The expected prompt string.

        Raises:
            AssertionError: If no calls made or prompt doesn't match.
        """
        if self.last_prompt is None:
            msg = "Expected a call, but execute() was never called"
            raise AssertionError(msg)
        if self.last_prompt != prompt:
            msg = f"Expected prompt '{prompt}', got '{self.last_prompt}'"
            raise AssertionError(msg)

    def reset(self) -> None:
        """Reset all state (responses, failures, call tracking)."""
        self._responses.clear()
        self._failures.clear()
        self._all_prompts.clear()
