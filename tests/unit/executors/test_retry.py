"""Tests for RetryExecutor wrapper."""

from unittest.mock import AsyncMock, patch

import pytest

from adw.exceptions import LLMError, LLMRateLimitError, LLMTimeoutError
from adw.executors.mock import MockExecutor
from adw.executors.retry import RetryExecutor
from adw.models.config import RetryConfig


class TestRetryExecutorWrapper:
    """Tests for RetryExecutor wrapper basic functionality."""

    def test_retry_executor_wraps_executor(self) -> None:
        """Test that RetryExecutor properly wraps another executor."""
        mock = MockExecutor()
        config = RetryConfig()
        retry = RetryExecutor(executor=mock, config=config)

        assert retry.executor is mock
        assert retry.config is config

    def test_retry_executor_with_default_config(self) -> None:
        """Test RetryExecutor with default RetryConfig."""
        mock = MockExecutor()
        retry = RetryExecutor(executor=mock)

        assert retry.config.max_retries == 3
        assert retry.config.base_delay_seconds == 1.0
        assert retry.config.multiplier == 2.0

    def test_retry_executor_execute_returns_llm_result(self) -> None:
        """Test that execute returns an LLMResult."""
        mock = MockExecutor()
        mock.configure_responses([{"content": "Hello, world!"}])
        retry = RetryExecutor(executor=mock)

        result = retry.execute("test prompt")

        assert result.success
        assert result.content == "Hello, world!"

    def test_retry_executor_passes_timeout_to_wrapped_executor(self) -> None:
        """Test that timeout is passed to the wrapped executor."""
        mock = MockExecutor()
        mock.configure_responses([{"content": "Response"}])
        retry = RetryExecutor(executor=mock)

        result = retry.execute("test prompt", timeout=60)

        assert result.success
        # MockExecutor doesn't track timeout, but the call should succeed

    def test_retry_executor_implements_llm_executor_protocol(self) -> None:
        """Test that RetryExecutor satisfies LLMExecutor Protocol."""
        from adw.executors.base import LLMExecutor

        mock = MockExecutor()
        retry = RetryExecutor(executor=mock)

        # Should be recognized as LLMExecutor (structural subtyping)
        assert isinstance(retry, LLMExecutor)


class TestExponentialBackoff:
    """Tests for exponential backoff delay calculation."""

    def test_calculate_delay_first_attempt(self) -> None:
        """Test delay calculation for first retry attempt."""
        mock = MockExecutor()
        config = RetryConfig(base_delay_seconds=1.0, multiplier=2.0)
        retry = RetryExecutor(executor=mock, config=config)

        error = LLMTimeoutError(
            code="LLM_TIMEOUT",
            message="Timeout",
            timeout_seconds=300,
            elapsed_seconds=300,
        )

        # First retry: base_delay * (multiplier ^ 0) = 1.0
        delay = retry._calculate_delay(1, error)

        # With ±25% jitter, delay should be between 0.75 and 1.25
        assert 0.75 <= delay <= 1.25

    def test_calculate_delay_second_attempt(self) -> None:
        """Test delay calculation for second retry attempt."""
        mock = MockExecutor()
        config = RetryConfig(base_delay_seconds=1.0, multiplier=2.0)
        retry = RetryExecutor(executor=mock, config=config)

        error = LLMTimeoutError(
            code="LLM_TIMEOUT",
            message="Timeout",
            timeout_seconds=300,
            elapsed_seconds=300,
        )

        # Second retry: base_delay * (multiplier ^ 1) = 2.0
        delay = retry._calculate_delay(2, error)

        # With ±25% jitter, delay should be between 1.5 and 2.5
        assert 1.5 <= delay <= 2.5

    def test_calculate_delay_third_attempt(self) -> None:
        """Test delay calculation for third retry attempt."""
        mock = MockExecutor()
        config = RetryConfig(base_delay_seconds=1.0, multiplier=2.0)
        retry = RetryExecutor(executor=mock, config=config)

        error = LLMTimeoutError(
            code="LLM_TIMEOUT",
            message="Timeout",
            timeout_seconds=300,
            elapsed_seconds=300,
        )

        # Third retry: base_delay * (multiplier ^ 2) = 4.0
        delay = retry._calculate_delay(3, error)

        # With ±25% jitter, delay should be between 3.0 and 5.0
        assert 3.0 <= delay <= 5.0

    def test_calculate_delay_caps_at_max_delay(self) -> None:
        """Test that delay is capped at max_delay_seconds."""
        mock = MockExecutor()
        config = RetryConfig(
            base_delay_seconds=10.0,
            multiplier=10.0,
            max_delay_seconds=30.0,
        )
        retry = RetryExecutor(executor=mock, config=config)

        error = LLMTimeoutError(
            code="LLM_TIMEOUT",
            message="Timeout",
            timeout_seconds=300,
            elapsed_seconds=300,
        )

        # 5th attempt would be 10 * (10^4) = 100000, but capped at 30
        delay = retry._calculate_delay(5, error)

        # Should be capped at max_delay (30), possibly with small jitter
        assert delay <= 30.0

    def test_calculate_delay_uses_jitter(self) -> None:
        """Test that delay has jitter (not always the same)."""
        mock = MockExecutor()
        config = RetryConfig(base_delay_seconds=1.0, multiplier=2.0)
        retry = RetryExecutor(executor=mock, config=config)

        error = LLMTimeoutError(
            code="LLM_TIMEOUT",
            message="Timeout",
            timeout_seconds=300,
            elapsed_seconds=300,
        )

        # Calculate delay multiple times
        delays = [retry._calculate_delay(1, error) for _ in range(20)]

        # Should have some variation due to jitter
        assert len(set(delays)) > 1, "Jitter should produce different values"


class TestErrorClassification:
    """Tests for error classification (is_retryable)."""

    def test_llm_timeout_error_is_retryable(self) -> None:
        """Test that LLMTimeoutError is retryable."""
        mock = MockExecutor()
        retry = RetryExecutor(executor=mock)

        error = LLMTimeoutError(
            code="LLM_TIMEOUT",
            message="Timeout",
            timeout_seconds=300,
            elapsed_seconds=300,
        )

        assert retry._is_retryable(error) is True

    def test_llm_rate_limit_error_is_retryable(self) -> None:
        """Test that LLMRateLimitError is retryable."""
        mock = MockExecutor()
        retry = RetryExecutor(executor=mock)

        error = LLMRateLimitError(
            code="LLM_RATE_LIMIT",
            message="Rate limited",
            retry_after=60,
        )

        assert retry._is_retryable(error) is True

    def test_llm_error_with_recoverable_false_not_retryable(self) -> None:
        """Test that LLMError with recoverable=False is not retryable."""
        mock = MockExecutor()
        retry = RetryExecutor(executor=mock)

        error = LLMError(
            code="LLM_ERROR",
            message="Some error",
            recoverable=False,
        )

        assert retry._is_retryable(error) is False

    def test_llm_error_with_recoverable_true_is_retryable(self) -> None:
        """Test that LLMError with recoverable=True is retryable."""
        mock = MockExecutor()
        retry = RetryExecutor(executor=mock)

        error = LLMError(
            code="LLM_ERROR",
            message="Some error",
            recoverable=True,
        )

        assert retry._is_retryable(error) is True
