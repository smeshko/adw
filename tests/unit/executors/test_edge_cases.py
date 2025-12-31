"""Edge case tests for MockExecutor."""

import pytest

from adw.exceptions import LLMTimeoutError
from adw.executors import MockExecutor
from adw.models.llm import ToolCall


class TestEmptyQueueEdgeCases:
    """Tests for empty queue behavior."""

    def test_empty_response_queue_returns_default(self) -> None:
        """Empty response queue returns default response."""
        executor = MockExecutor()
        # No configure_responses() call

        result = executor.execute("prompt")
        assert result.success is True
        assert "Mock" in result.content

    def test_exhausted_response_queue_returns_default(self) -> None:
        """Exhausted queue falls back to default."""
        executor = MockExecutor()
        executor.configure_responses([{"content": "only one"}])

        executor.execute("first")  # Consume
        result = executor.execute("second")  # Should get default

        assert "Mock" in result.content

    def test_empty_failure_queue_means_success(self) -> None:
        """Empty failure queue doesn't raise."""
        executor = MockExecutor()
        # No configure_failures() call

        result = executor.execute("prompt")
        assert result.success is True

    def test_exhausted_failure_queue_means_success(self) -> None:
        """Exhausted failure queue doesn't raise."""
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

        # First call fails
        with pytest.raises(LLMTimeoutError):
            executor.execute("first")

        # Second call succeeds (failure queue exhausted)
        result = executor.execute("second")
        assert result.success is True


class TestMixedSuccessFailure:
    """Tests for mixed success/failure scenarios."""

    def test_alternating_success_failure(self) -> None:
        """Alternating success and failure calls work correctly."""
        executor = MockExecutor()
        executor.configure_failures(
            [
                None,  # 1st: success
                LLMTimeoutError(
                    code="LLM_TIMEOUT",
                    message="fail",
                    timeout_seconds=300,
                    elapsed_seconds=300,
                ),  # 2nd: fail
                None,  # 3rd: success
            ]
        )
        executor.configure_responses(
            [
                {"content": "first success"},
                {"content": "second success"},
            ]
        )

        # 1st call: success
        r1 = executor.execute("p1")
        assert r1.content == "first success"

        # 2nd call: failure
        with pytest.raises(LLMTimeoutError):
            executor.execute("p2")

        # 3rd call: success
        r3 = executor.execute("p3")
        assert r3.content == "second success"

        # All 3 calls tracked
        assert executor.call_count == 3

    def test_failure_before_response_queue(self) -> None:
        """Failure checked before response queue."""
        executor = MockExecutor()
        executor.configure_failures(
            [
                LLMTimeoutError(
                    code="LLM_TIMEOUT",
                    message="fail",
                    timeout_seconds=300,
                    elapsed_seconds=300,
                ),
            ]
        )
        executor.configure_responses(
            [
                {"content": "never reached"},
            ]
        )

        with pytest.raises(LLMTimeoutError):
            executor.execute("prompt")

        # Response should still be in queue
        result = executor.execute("next")
        assert result.content == "never reached"


class TestConfigureReplacesQueue:
    """Tests that configure methods replace existing queue."""

    def test_configure_responses_replaces_queue(self) -> None:
        """configure_responses() clears and replaces queue."""
        executor = MockExecutor()
        executor.configure_responses([{"content": "first"}])
        executor.configure_responses([{"content": "replaced"}])

        result = executor.execute("prompt")
        assert result.content == "replaced"

    def test_configure_failures_replaces_queue(self) -> None:
        """configure_failures() clears and replaces queue."""
        executor = MockExecutor()
        executor.configure_failures(
            [
                LLMTimeoutError(
                    code="LLM_TIMEOUT",
                    message="first",
                    timeout_seconds=300,
                    elapsed_seconds=300,
                ),
            ]
        )
        executor.configure_failures([None])  # Replace with success

        result = executor.execute("prompt")
        assert result.success is True


class TestToolCallHandling:
    """Tests for tool call edge cases."""

    def test_empty_tool_calls_list(self) -> None:
        """Empty tool_calls list handled correctly."""
        executor = MockExecutor()
        executor.configure_responses(
            [
                {"content": "test", "tool_calls": []},
            ]
        )

        result = executor.execute("prompt")
        assert result.tool_calls == []

    def test_tool_call_from_dict(self) -> None:
        """Tool calls can be configured as dicts."""
        executor = MockExecutor()
        executor.configure_responses(
            [
                {
                    "content": "test",
                    "tool_calls": [
                        {"tool_name": "read", "arguments": {"path": "/test"}},
                    ],
                },
            ]
        )

        result = executor.execute("prompt")
        assert len(result.tool_calls) == 1
        assert isinstance(result.tool_calls[0], ToolCall)

    def test_tool_call_from_model(self) -> None:
        """Tool calls can be configured as ToolCall models."""
        executor = MockExecutor()
        tc = ToolCall(tool_name="write", arguments={"content": "data"})
        executor.configure_responses(
            [
                {"content": "test", "tool_calls": [tc]},
            ]
        )

        result = executor.execute("prompt")
        assert len(result.tool_calls) == 1
        assert result.tool_calls[0].tool_name == "write"


class TestPromptTracking:
    """Tests for prompt tracking edge cases."""

    def test_empty_prompt_tracked(self) -> None:
        """Empty string prompt is tracked."""
        executor = MockExecutor()
        executor.execute("")

        assert executor.call_count == 1
        assert executor.last_prompt == ""

    def test_long_prompt_tracked(self) -> None:
        """Very long prompts are tracked correctly."""
        executor = MockExecutor()
        long_prompt = "x" * 10000

        executor.execute(long_prompt)

        assert executor.last_prompt == long_prompt
        assert len(executor.all_prompts[0]) == 10000

    def test_unicode_prompt_tracked(self) -> None:
        """Unicode prompts are tracked correctly."""
        executor = MockExecutor()
        unicode_prompt = "Hello 世界 🌍"

        executor.execute(unicode_prompt)

        assert executor.last_prompt == unicode_prompt
