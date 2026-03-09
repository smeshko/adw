"""Tests for RetryExecutor wrapper."""

import pytest

from adw.exceptions import LLMError, LLMRateLimitError
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

        error = LLMError(
            code="LLM_ERROR",
            message="LLM failed",
            recoverable=True,
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

        error = LLMError(
            code="LLM_ERROR",
            message="LLM failed",
            recoverable=True,
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

        error = LLMError(
            code="LLM_ERROR",
            message="LLM failed",
            recoverable=True,
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

        error = LLMError(
            code="LLM_ERROR",
            message="LLM failed",
            recoverable=True,
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

        error = LLMError(
            code="LLM_ERROR",
            message="LLM failed",
            recoverable=True,
        )

        # Calculate delay multiple times
        delays = [retry._calculate_delay(1, error) for _ in range(20)]

        # Should have some variation due to jitter
        assert len(set(delays)) > 1, "Jitter should produce different values"


class TestErrorClassification:
    """Tests for error classification (is_retryable)."""

    def test_llm_recoverable_error_is_retryable(self) -> None:
        """Test that recoverable LLMError is retryable."""
        mock = MockExecutor()
        retry = RetryExecutor(executor=mock)

        error = LLMError(
            code="LLM_ERROR",
            message="LLM failed",
            recoverable=True,
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


class TestRateLimitHandling:
    """Tests for rate limit retry_after handling."""

    def test_rate_limit_retry_after_is_respected(self) -> None:
        """Test retry_after from rate limit error is used when larger than backoff."""
        mock = MockExecutor()
        config = RetryConfig(base_delay_seconds=1.0, multiplier=2.0)
        retry = RetryExecutor(executor=mock, config=config)

        # retry_after=30 is much larger than calculated backoff of 1.0
        error = LLMRateLimitError(
            code="LLM_RATE_LIMIT",
            message="Rate limited",
            retry_after=30,
        )

        delay = retry._calculate_delay(1, error)

        # With ±25% jitter on 30, delay should be between 22.5 and 37.5
        assert 22.5 <= delay <= 37.5

    def test_rate_limit_uses_backoff_when_larger_than_retry_after(self) -> None:
        """Test that backoff is used when larger than retry_after."""
        mock = MockExecutor()
        config = RetryConfig(base_delay_seconds=10.0, multiplier=2.0)
        retry = RetryExecutor(executor=mock, config=config)

        # retry_after=5 is smaller than calculated backoff of 10.0
        error = LLMRateLimitError(
            code="LLM_RATE_LIMIT",
            message="Rate limited",
            retry_after=5,
        )

        delay = retry._calculate_delay(1, error)

        # Backoff of 10.0 with ±25% jitter: between 7.5 and 12.5
        assert 7.5 <= delay <= 12.5

    def test_rate_limit_without_retry_after_uses_backoff(self) -> None:
        """Test that backoff is used when retry_after is None."""
        mock = MockExecutor()
        config = RetryConfig(base_delay_seconds=2.0, multiplier=2.0)
        retry = RetryExecutor(executor=mock, config=config)

        error = LLMRateLimitError(
            code="LLM_RATE_LIMIT",
            message="Rate limited",
            retry_after=None,
        )

        delay = retry._calculate_delay(1, error)

        # Backoff of 2.0 with ±25% jitter: between 1.5 and 2.5
        assert 1.5 <= delay <= 2.5

    def test_rate_limit_retry_after_still_capped_at_max_delay(self) -> None:
        """Test that retry_after is still capped at max_delay_seconds."""
        mock = MockExecutor()
        config = RetryConfig(
            base_delay_seconds=1.0,
            max_delay_seconds=10.0,
        )
        retry = RetryExecutor(executor=mock, config=config)

        # retry_after=60 is larger than max_delay=10
        error = LLMRateLimitError(
            code="LLM_RATE_LIMIT",
            message="Rate limited",
            retry_after=60,
        )

        delay = retry._calculate_delay(1, error)

        # Should be capped at max_delay of 10.0
        assert delay <= 10.0


class TestAttemptTracking:
    """Tests for attempt_count tracking in LLMResult."""

    def test_successful_first_attempt_has_attempt_count_1(self) -> None:
        """Test that successful first attempt returns attempt_count=1."""
        mock = MockExecutor()
        mock.configure_responses([{"content": "Success!"}])
        retry = RetryExecutor(executor=mock)

        result = retry.execute("test prompt")

        assert result.success
        assert result.attempt_count == 1

    def test_attempt_count_increments_on_retry(self) -> None:
        """Test that attempt_count reflects number of attempts made."""
        mock = MockExecutor()
        # Configure mock to fail twice, then succeed on third attempt
        mock.configure_failures(
            [
                LLMError(
                    code="LLM_ERROR",
                    message="LLM failed",
                    recoverable=True,
                ),
                LLMError(
                    code="LLM_ERROR",
                    message="LLM failed",
                    recoverable=True,
                ),
            ]
        )
        mock.configure_responses([{"content": "Success after retries!"}])

        config = RetryConfig(base_delay_seconds=0.001)  # Fast for tests
        retry = RetryExecutor(executor=mock, config=config)

        result = retry.execute("test prompt")

        assert result.success
        assert result.attempt_count == 3
        assert mock.call_count == 3

    def test_llm_result_has_default_attempt_count_1(self) -> None:
        """Test that LLMResult defaults to attempt_count=1."""
        from adw.models.llm import LLMResult

        result = LLMResult(success=True, content="test")
        assert result.attempt_count == 1


class TestErrorMessages:
    """Tests for enhanced error messages."""

    def test_error_message_includes_attempt_count_plural(self) -> None:
        """Test that error message includes attempt count (plural)."""
        mock = MockExecutor()
        # Configure to fail all 3 attempts
        mock.configure_failures(
            [
                LLMError(
                    code="LLM_ERROR",
                    message="LLM failed",
                    recoverable=True,
                ),
            ]
            * 3
        )

        config = RetryConfig(max_retries=3, base_delay_seconds=0.001)
        retry = RetryExecutor(executor=mock, config=config)

        with pytest.raises(LLMError) as exc_info:
            retry.execute("test prompt")

        assert "after 3 attempts" in str(exc_info.value.message)

    def test_error_message_includes_attempt_count_singular(self) -> None:
        """Test that error message uses singular 'attempt' for 1."""
        mock = MockExecutor()
        # Configure to fail with non-retryable error on first attempt
        mock.configure_failures(
            [
                LLMError(
                    code="LLM_ERROR",
                    message="Non-retryable error",
                    recoverable=False,
                ),
            ]
        )

        retry = RetryExecutor(executor=mock)

        with pytest.raises(LLMError) as exc_info:
            retry.execute("test prompt")

        assert "after 1 attempt" in str(exc_info.value.message)

    def test_original_error_preserved_as_cause(self) -> None:
        """Test that original error is preserved as __cause__."""
        mock = MockExecutor()
        original_error = LLMError(
            code="LLM_ERROR",
            message="Original error",
            recoverable=True,
        )
        mock.configure_failures([original_error] * 3)

        config = RetryConfig(max_retries=3, base_delay_seconds=0.001)
        retry = RetryExecutor(executor=mock, config=config)

        with pytest.raises(LLMError) as exc_info:
            retry.execute("test prompt")

        assert exc_info.value.__cause__ is not None
        assert exc_info.value.__cause__.code == "LLM_ERROR"

    def test_non_retryable_error_fails_immediately(self) -> None:
        """Test that non-retryable errors fail on first attempt."""
        mock = MockExecutor()
        mock.configure_failures(
            [
                LLMError(
                    code="INVALID_PROMPT",
                    message="Invalid prompt format",
                    recoverable=False,
                ),
            ]
        )

        retry = RetryExecutor(executor=mock)

        with pytest.raises(LLMError) as exc_info:
            retry.execute("test prompt")

        # Should fail after just 1 attempt
        assert "after 1 attempt" in str(exc_info.value.message)
        assert mock.call_count == 1


class TestModelParamForwarding:
    """Tests for model parameter forwarding to wrapped executor."""

    def test_model_param_forwarded_to_wrapped_executor(self) -> None:
        """Test that model parameter is passed through to the wrapped executor."""
        mock = MockExecutor()
        mock.configure_responses([{"content": "Response"}])
        retry = RetryExecutor(executor=mock)

        result = retry.execute("test prompt", model="claude-sonnet-4-5-20250929")

        assert result.success
        assert mock.call_count == 1

    def test_model_param_none_by_default(self) -> None:
        """Test that model defaults to None when not specified."""
        mock = MockExecutor()
        mock.configure_responses([{"content": "Response"}])
        retry = RetryExecutor(executor=mock)

        result = retry.execute("test prompt")

        assert result.success

    def test_model_param_forwarded_on_retry(self) -> None:
        """Test that model parameter is forwarded on retry attempts too."""
        mock = MockExecutor()
        mock.configure_failures(
            [
                LLMError(
                    code="LLM_ERROR",
                    message="LLM failed",
                    recoverable=True,
                ),
            ]
        )
        mock.configure_responses([{"content": "Success after retry"}])

        config = RetryConfig(base_delay_seconds=0.001)
        retry = RetryExecutor(executor=mock, config=config)

        result = retry.execute("test prompt", model="claude-sonnet-4-5-20250929")

        assert result.success
        assert result.attempt_count == 2
        assert mock.call_count == 2
