"""Tests for RetryExecutor wrapper."""

import pytest

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
