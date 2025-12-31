"""Retry executor with exponential backoff.

This module provides a RetryExecutor that wraps any LLMExecutor and
handles transient failures through automatic retries with exponential
backoff and jitter.
"""

import asyncio
import logging
import random

from adw.exceptions import LLMError, LLMRateLimitError
from adw.executors.base import LLMExecutor
from adw.models.config import RetryConfig
from adw.models.llm import LLMResult

logger = logging.getLogger(__name__)


class RetryExecutor:
    """LLM executor wrapper that handles retries with exponential backoff.

    Wraps any LLMExecutor and automatically retries transient failures
    (timeouts, rate limits) with configurable exponential backoff.

    Example:
        >>> from adw.executors.mock import MockExecutor
        >>> mock = MockExecutor()
        >>> retry = RetryExecutor(executor=mock, config=RetryConfig(max_retries=5))
        >>> result = retry.execute("Hello, world!")
    """

    def __init__(
        self,
        executor: LLMExecutor,
        config: RetryConfig | None = None,
    ) -> None:
        """Initialize the retry executor.

        Args:
            executor: The underlying LLMExecutor to wrap.
            config: Retry configuration. Defaults to RetryConfig() if not provided.
        """
        self.executor = executor
        self.config = config if config is not None else RetryConfig()

    def execute(
        self,
        prompt: str,
        *,
        timeout: int | None = None,
    ) -> LLMResult:
        """Execute a prompt with automatic retry on transient failures.

        Args:
            prompt: The prompt to send to the LLM.
            timeout: Optional timeout in seconds.

        Returns:
            LLMResult with success status, content, and attempt count.

        Raises:
            LLMError: If all retry attempts fail or a non-retryable error occurs.
        """
        return asyncio.run(self._execute_with_retry(prompt, timeout))

    async def _execute_with_retry(
        self,
        prompt: str,
        timeout: int | None,
    ) -> LLMResult:
        """Execute prompt with retry logic (async implementation).

        Args:
            prompt: The prompt to send to the LLM.
            timeout: Optional timeout in seconds.

        Returns:
            LLMResult with attempt count set.

        Raises:
            LLMError: If all retries fail or non-retryable error occurs.
        """
        last_error: LLMError | None = None

        for attempt in range(1, self.config.max_retries + 1):
            try:
                result = self.executor.execute(prompt, timeout=timeout)
                result.attempt_count = attempt
                return result
            except LLMError as e:
                last_error = e

                # Check if retryable and not on last attempt
                if not self._is_retryable(e) or attempt == self.config.max_retries:
                    raise LLMError(
                        code=e.code,
                        message=f"{e.message} (after {attempt} attempt{'s' if attempt > 1 else ''})",
                        suggestion=e.suggestion,
                        recoverable=False,
                    ) from e

                # Calculate delay and wait
                delay = self._calculate_delay(attempt, e)
                logger.info(
                    "Retrying LLM call",
                    extra={
                        "attempt": attempt,
                        "max_attempts": self.config.max_retries,
                        "delay_seconds": delay,
                        "error_code": e.code,
                    },
                )
                await asyncio.sleep(delay)

        # Should never reach here, but satisfy type checker
        if last_error is not None:
            raise last_error
        raise LLMError(
            code="RETRY_EXHAUSTED",
            message="All retry attempts exhausted",
            recoverable=False,
        )

    def _is_retryable(self, error: LLMError) -> bool:
        """Check if an error is retryable.

        Uses the error's recoverable field to determine if retry is appropriate.

        Args:
            error: The LLMError to check.

        Returns:
            True if the error can be retried, False otherwise.
        """
        return error.recoverable

    def _calculate_delay(self, attempt: int, error: LLMError) -> float:
        """Calculate the delay before the next retry attempt.

        Uses exponential backoff with jitter. For rate limit errors,
        respects the retry_after value if available.

        Args:
            attempt: The current attempt number (1-indexed).
            error: The error that triggered the retry.

        Returns:
            Delay in seconds before the next attempt.
        """
        # Base exponential backoff: base_delay * (multiplier ^ (attempt - 1))
        base_delay = self.config.base_delay_seconds * (
            self.config.multiplier ** (attempt - 1)
        )

        # Respect rate limit retry_after if available
        if isinstance(error, LLMRateLimitError) and error.retry_after is not None:
            base_delay = max(base_delay, float(error.retry_after))
            logger.info(
                "Using rate limit delay",
                extra={
                    "calculated_delay": self.config.base_delay_seconds
                    * (self.config.multiplier ** (attempt - 1)),
                    "retry_after": error.retry_after,
                    "actual_delay": base_delay,
                },
            )

        # Add jitter (±25%) to prevent thundering herd
        jitter = base_delay * 0.25 * (random.random() * 2 - 1)
        delay = base_delay + jitter

        # Cap at max delay
        return min(delay, self.config.max_delay_seconds)
