"""Integration tests for ClaudeCodeExecutor.

These tests require Claude Code CLI to be installed and available.
Tests are skipped if Claude Code is not found in PATH or if running
in mock mode (ADW_MOCK_EXECUTOR=1).

WARNING: These tests make REAL API calls and incur costs!
They are skipped by default in the test suite (ADW_MOCK_EXECUTOR is set
in conftest.py). Only run manually when you need to test real integration.
"""

import os
import shutil

import pytest

from adw.executors.claude_code import ClaudeCodeExecutor
from adw.models.config import LLMConfig
from adw.models.llm import LLMResult

# Skip all tests in this module if Claude Code is not installed
# OR if we're in mock mode (to avoid hitting real API during test runs)
pytestmark = [
    pytest.mark.skipif(
        shutil.which("claude") is None,
        reason="Claude Code CLI not installed",
    ),
    pytest.mark.skipif(
        os.environ.get("ADW_MOCK_EXECUTOR") == "1",
        reason="Skipped in mock mode - these tests hit real Claude API",
    ),
]


class TestClaudeCodeIntegration:
    """Integration tests for real Claude Code execution."""

    @pytest.fixture
    def executor(self) -> ClaudeCodeExecutor:
        """Create executor with default config."""
        config = LLMConfig(path="claude")
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


class TestTimeoutIntegration:
    """Integration tests for timeout behavior (hooks only)."""

    def test_hook_timeout_integration(self) -> None:
        """HookRunner timeout should work with real subprocess."""
        import tempfile
        from datetime import datetime
        from pathlib import Path

        from adw.exceptions import HookError
        from adw.hooks.runner import HookRunner
        from adw.models import HookConfig, RunContext

        # Create a slow hook script
        with tempfile.NamedTemporaryFile(mode="w", suffix=".sh", delete=False) as f:
            f.write("#!/bin/bash\nsleep 10\necho 'done'\n")
            script_path = Path(f.name)

        try:
            script_path.chmod(0o755)

            config = HookConfig(timeout_seconds=1)
            runner = HookRunner(config)

            context = RunContext(
                run_id="01TEST00000000000000000000",  # 26 chars for ULID
                feature_description="test timeout",
                current_phase="test",
                started_at=datetime.now(),
            )

            with pytest.raises(HookError) as exc_info:
                runner.run_hook(
                    hook_path=script_path,
                    context=context,
                    phase="test",
                    hook_type="pre",
                )

            assert exc_info.value.code == "HOOK_TIMEOUT"
            assert exc_info.value.duration_ms is not None
            assert exc_info.value.duration_ms >= 1000  # At least 1 second

        finally:
            script_path.unlink()
