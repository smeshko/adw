"""Tests for MockExecutor implementation."""

import contextlib

import pytest

from adw.exceptions import LLMRateLimitError, LLMTimeoutError
from adw.executors import LLMExecutor, MockExecutor
from adw.models import LLMResult


class TestMockExecutorProtocolCompliance:
    """Tests verifying MockExecutor implements LLMExecutor protocol."""

    def test_mock_executor_is_llm_executor(self) -> None:
        """MockExecutor is an instance of LLMExecutor protocol."""
        executor = MockExecutor()
        assert isinstance(executor, LLMExecutor)

    def test_mock_executor_has_execute_method(self) -> None:
        """MockExecutor has execute() method with correct signature."""
        executor = MockExecutor()
        assert hasattr(executor, "execute")
        assert callable(executor.execute)


class TestMockExecutorDefaultBehavior:
    """Tests for MockExecutor default response behavior."""

    def test_default_response_is_success(self) -> None:
        """MockExecutor returns success by default."""
        executor = MockExecutor()
        result = executor.execute("test prompt")
        assert result.success is True

    def test_default_response_has_content(self) -> None:
        """MockExecutor returns content by default."""
        executor = MockExecutor()
        result = executor.execute("test prompt")
        assert "Mock" in result.content

    def test_default_response_is_llm_result(self) -> None:
        """MockExecutor returns LLMResult instance."""
        executor = MockExecutor()
        result = executor.execute("test prompt")
        assert isinstance(result, LLMResult)


class TestMockExecutorConfiguredResponses:
    """Tests for MockExecutor.configure_responses()."""

    def test_configured_responses_returned_in_order(self) -> None:
        """MockExecutor returns configured responses in FIFO order."""
        executor = MockExecutor()
        executor.configure_responses(
            [
                {"content": "first"},
                {"content": "second"},
                {"content": "third"},
            ]
        )

        r1 = executor.execute("prompt 1")
        r2 = executor.execute("prompt 2")
        r3 = executor.execute("prompt 3")

        assert r1.content == "first"
        assert r2.content == "second"
        assert r3.content == "third"

    def test_configured_response_with_tokens(self) -> None:
        """MockExecutor respects tokens_used in response config."""
        executor = MockExecutor()
        executor.configure_responses(
            [
                {"content": "test", "tokens_used": 500},
            ]
        )

        result = executor.execute("prompt")
        assert result.tokens_used == 500

    def test_configured_response_with_duration(self) -> None:
        """MockExecutor respects duration_ms in response config."""
        executor = MockExecutor()
        executor.configure_responses(
            [
                {"content": "test", "duration_ms": 2500},
            ]
        )

        result = executor.execute("prompt")
        assert result.duration_ms == 2500

    def test_configured_response_with_tool_calls(self) -> None:
        """MockExecutor respects tool_calls in response config."""
        executor = MockExecutor()
        executor.configure_responses(
            [
                {
                    "content": "test",
                    "tool_calls": [
                        {"tool_name": "read_file", "arguments": {"path": "/tmp/test"}},
                    ],
                },
            ]
        )

        result = executor.execute("prompt")
        assert len(result.tool_calls) == 1
        assert result.tool_calls[0].tool_name == "read_file"

    def test_falls_back_to_default_when_queue_empty(self) -> None:
        """MockExecutor returns default after configured responses exhausted."""
        executor = MockExecutor()
        executor.configure_responses([{"content": "only one"}])

        executor.execute("first")  # Consume the configured response
        result = executor.execute("second")  # Should get default

        assert "Mock" in result.content


class TestMockExecutorConfiguredFailures:
    """Tests for MockExecutor.configure_failures()."""

    def test_configured_failure_raises(self) -> None:
        """MockExecutor raises configured LLMError."""
        executor = MockExecutor()
        executor.configure_failures(
            [
                LLMTimeoutError(
                    code="LLM_TIMEOUT",
                    message="Timeout",
                    timeout_seconds=300,
                    elapsed_seconds=300,
                ),
            ]
        )

        with pytest.raises(LLMTimeoutError):
            executor.execute("prompt")

    def test_none_failure_means_success(self) -> None:
        """None in failures list means success."""
        executor = MockExecutor()
        executor.configure_failures([None])

        result = executor.execute("prompt")
        assert result.success is True

    def test_mixed_failures_and_successes(self) -> None:
        """MockExecutor handles mixed failure/success sequence."""
        executor = MockExecutor()
        executor.configure_failures(
            [
                LLMTimeoutError(
                    code="LLM_TIMEOUT",
                    message="First fails",
                    timeout_seconds=300,
                    elapsed_seconds=300,
                ),
                None,  # Second succeeds
            ]
        )
        executor.configure_responses([{"content": "success after retry"}])

        # First call should raise
        with pytest.raises(LLMTimeoutError):
            executor.execute("prompt 1")

        # Second call should succeed
        result = executor.execute("prompt 2")
        assert result.success is True
        assert result.content == "success after retry"

    def test_rate_limit_error(self) -> None:
        """MockExecutor can raise LLMRateLimitError."""
        executor = MockExecutor()
        executor.configure_failures(
            [
                LLMRateLimitError(
                    code="LLM_RATE_LIMIT",
                    message="Rate limited",
                    retry_after=60,
                ),
            ]
        )

        with pytest.raises(LLMRateLimitError) as exc_info:
            executor.execute("prompt")

        assert exc_info.value.retry_after == 60


class TestMockExecutorCallTracking:
    """Tests for MockExecutor call tracking."""

    def test_call_count_starts_at_zero(self) -> None:
        """New MockExecutor has call_count of 0."""
        executor = MockExecutor()
        assert executor.call_count == 0

    def test_call_count_increments(self) -> None:
        """call_count increments with each execute() call."""
        executor = MockExecutor()

        executor.execute("first")
        assert executor.call_count == 1

        executor.execute("second")
        assert executor.call_count == 2

        executor.execute("third")
        assert executor.call_count == 3

    def test_call_count_increments_on_failure(self) -> None:
        """call_count increments even when execute() raises."""
        executor = MockExecutor()
        executor.configure_failures(
            [
                LLMTimeoutError(
                    code="LLM_TIMEOUT",
                    message="Timeout",
                    timeout_seconds=300,
                    elapsed_seconds=300,
                ),
            ]
        )

        with contextlib.suppress(LLMTimeoutError):
            executor.execute("prompt")

        assert executor.call_count == 1

    def test_last_prompt_is_none_initially(self) -> None:
        """last_prompt is None before any calls."""
        executor = MockExecutor()
        assert executor.last_prompt is None

    def test_last_prompt_tracks_most_recent(self) -> None:
        """last_prompt returns the most recent prompt."""
        executor = MockExecutor()

        executor.execute("first prompt")
        assert executor.last_prompt == "first prompt"

        executor.execute("second prompt")
        assert executor.last_prompt == "second prompt"

    def test_all_prompts_is_empty_initially(self) -> None:
        """all_prompts is empty list before any calls."""
        executor = MockExecutor()
        assert executor.all_prompts == []

    def test_all_prompts_collects_all(self) -> None:
        """all_prompts returns all prompts in order."""
        executor = MockExecutor()

        executor.execute("first")
        executor.execute("second")
        executor.execute("third")

        assert executor.all_prompts == ["first", "second", "third"]

    def test_all_prompts_returns_copy(self) -> None:
        """all_prompts returns a copy, not the internal list."""
        executor = MockExecutor()
        executor.execute("prompt")

        prompts = executor.all_prompts
        prompts.append("modified")

        assert executor.all_prompts == ["prompt"]


class TestMockExecutorTimeout:
    """Tests for MockExecutor timeout parameter handling."""

    def test_timeout_parameter_accepted(self) -> None:
        """MockExecutor accepts timeout parameter."""
        executor = MockExecutor()
        # Should not raise
        result = executor.execute("prompt", timeout=300)
        assert result.success is True

    def test_timeout_parameter_is_ignored(self) -> None:
        """MockExecutor ignores timeout (it's for interface compatibility)."""
        executor = MockExecutor()
        executor.configure_responses([{"content": "test"}])

        # Different timeout values should not affect behavior
        r1 = executor.execute("prompt", timeout=1)
        executor.configure_responses([{"content": "test"}])
        r2 = executor.execute("prompt", timeout=1000)

        assert r1.content == r2.content
