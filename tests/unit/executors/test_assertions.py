"""Tests for MockExecutor assertion helpers."""

import pytest

from adw.executors import MockExecutor


class TestAssertCalledOnce:
    """Tests for MockExecutor.assert_called_once()."""

    def test_passes_when_called_exactly_once(self) -> None:
        """assert_called_once() passes when execute() called once."""
        executor = MockExecutor()
        executor.execute("prompt")

        # Should not raise
        executor.assert_called_once()

    def test_fails_when_never_called(self) -> None:
        """assert_called_once() fails when execute() never called."""
        executor = MockExecutor()

        with pytest.raises(AssertionError) as exc_info:
            executor.assert_called_once()

        assert "Expected 1 call, got 0" in str(exc_info.value)

    def test_fails_when_called_multiple_times(self) -> None:
        """assert_called_once() fails when execute() called multiple times."""
        executor = MockExecutor()
        executor.execute("first")
        executor.execute("second")

        with pytest.raises(AssertionError) as exc_info:
            executor.assert_called_once()

        assert "Expected 1 call, got 2" in str(exc_info.value)


class TestAssertCalledWith:
    """Tests for MockExecutor.assert_called_with()."""

    def test_passes_when_prompt_matches(self) -> None:
        """assert_called_with() passes when prompt matches last call."""
        executor = MockExecutor()
        executor.execute("expected prompt")

        # Should not raise
        executor.assert_called_with("expected prompt")

    def test_matches_last_prompt_only(self) -> None:
        """assert_called_with() checks only the last prompt."""
        executor = MockExecutor()
        executor.execute("first prompt")
        executor.execute("second prompt")

        # Should pass - matches last call
        executor.assert_called_with("second prompt")

    def test_fails_when_prompt_differs(self) -> None:
        """assert_called_with() fails when prompt doesn't match."""
        executor = MockExecutor()
        executor.execute("actual prompt")

        with pytest.raises(AssertionError) as exc_info:
            executor.assert_called_with("expected prompt")

        assert "Expected prompt 'expected prompt'" in str(exc_info.value)
        assert "actual prompt" in str(exc_info.value)

    def test_fails_when_never_called(self) -> None:
        """assert_called_with() fails when execute() never called."""
        executor = MockExecutor()

        with pytest.raises(AssertionError) as exc_info:
            executor.assert_called_with("any prompt")

        assert "execute() was never called" in str(exc_info.value)


class TestReset:
    """Tests for MockExecutor.reset()."""

    def test_reset_clears_call_count(self) -> None:
        """reset() clears call_count to 0."""
        executor = MockExecutor()
        executor.execute("prompt 1")
        executor.execute("prompt 2")

        executor.reset()

        assert executor.call_count == 0

    def test_reset_clears_last_prompt(self) -> None:
        """reset() clears last_prompt to None."""
        executor = MockExecutor()
        executor.execute("some prompt")

        executor.reset()

        assert executor.last_prompt is None

    def test_reset_clears_all_prompts(self) -> None:
        """reset() clears all_prompts to empty list."""
        executor = MockExecutor()
        executor.execute("first")
        executor.execute("second")

        executor.reset()

        assert executor.all_prompts == []

    def test_reset_clears_configured_responses(self) -> None:
        """reset() clears configured responses."""
        executor = MockExecutor()
        executor.configure_responses([
            {"content": "configured"},
        ])

        executor.reset()

        # Should get default response after reset
        result = executor.execute("prompt")
        assert "Mock" in result.content

    def test_reset_clears_configured_failures(self) -> None:
        """reset() clears configured failures."""
        from adw.exceptions import LLMTimeoutError

        executor = MockExecutor()
        executor.configure_failures([
            LLMTimeoutError(
                code="LLM_TIMEOUT",
                message="Timeout",
                timeout_seconds=300,
                elapsed_seconds=300,
            ),
        ])

        executor.reset()

        # Should succeed after reset (no failure configured)
        result = executor.execute("prompt")
        assert result.success is True

    def test_reset_allows_fresh_start(self) -> None:
        """reset() allows clean configuration for new test."""
        executor = MockExecutor()

        # First test scenario
        executor.configure_responses([{"content": "first scenario"}])
        result1 = executor.execute("test 1")
        assert result1.content == "first scenario"

        # Reset for second scenario
        executor.reset()

        # Second test scenario
        executor.configure_responses([{"content": "second scenario"}])
        result2 = executor.execute("test 2")
        assert result2.content == "second scenario"

        # Verify clean state
        assert executor.call_count == 1
        assert executor.last_prompt == "test 2"
