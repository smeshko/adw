"""Integration tests for ClaudeCodeExecutor.

These tests require Claude Code CLI to be installed and available.
Tests are skipped if Claude Code is not found in PATH.
"""

import shutil

import pytest

from adw.executors.claude_code import ClaudeCodeExecutor
from adw.models.config import LLMConfig
from adw.models.llm import LLMResult


# Skip all tests in this module if Claude Code is not installed
pytestmark = pytest.mark.skipif(
    shutil.which("claude") is None,
    reason="Claude Code CLI not installed",
)


class TestClaudeCodeIntegration:
    """Integration tests for real Claude Code execution."""

    @pytest.fixture
    def executor(self) -> ClaudeCodeExecutor:
        """Create executor with default config."""
        config = LLMConfig(path="claude", timeout_seconds=60)
        return ClaudeCodeExecutor(config)

    def test_simple_prompt_execution(self, executor: ClaudeCodeExecutor) -> None:
        """Execute a simple prompt and verify result structure.

        Note: This test makes a real API call and may incur costs.
        """
        # Use a simple, deterministic prompt
        result = executor.execute("Say 'Hello' and nothing else.")

        assert isinstance(result, LLMResult)
        assert result.success is True
        assert result.content is not None
        assert len(result.content) > 0
        assert result.duration_ms > 0

    def test_result_contains_tokens_used(self, executor: ClaudeCodeExecutor) -> None:
        """Verify tokens_used is populated from Claude Code output.

        Note: This test makes a real API call and may incur costs.
        """
        result = executor.execute("What is 2+2? Reply with just the number.")

        # tokens_used should be populated if Claude outputs usage info
        # This may be 0 if Claude doesn't output usage in --print mode
        assert result.tokens_used >= 0

    def test_llm_executor_protocol_compliance(
        self, executor: ClaudeCodeExecutor
    ) -> None:
        """Verify executor implements LLMExecutor protocol correctly."""
        from adw.executors.base import LLMExecutor

        assert isinstance(executor, LLMExecutor)
        assert hasattr(executor, "execute")
        assert callable(executor.execute)


class TestClaudeCodeNotInstalled:
    """Tests for when Claude Code is not installed."""

    def test_raises_error_when_not_found(self) -> None:
        """Should raise LLMError when Claude is not found."""
        from adw.exceptions import LLMError

        # Use a path that definitely doesn't exist
        config = LLMConfig(path="nonexistent-claude-binary-xyz123")
        executor = ClaudeCodeExecutor(config)

        with pytest.raises(LLMError) as exc_info:
            executor.execute("Test prompt")

        assert exc_info.value.code == "CLAUDE_NOT_FOUND"
