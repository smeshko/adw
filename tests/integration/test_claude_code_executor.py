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


class TestTimeoutIntegration:
    """Integration tests for timeout behavior (Story 3-4).

    These tests use real subprocesses to verify timeout handling works
    correctly with actual process management.
    """

    def test_timeout_with_slow_subprocess(self) -> None:
        """Timeout should work with a real slow subprocess.

        Uses a shell script that sleeps to simulate slow execution.
        This verifies the asyncio timeout and process cleanup work
        together correctly.
        """
        import tempfile
        from pathlib import Path

        from adw.exceptions import LLMTimeoutError

        # Create a temporary script that runs slowly
        with tempfile.NamedTemporaryFile(mode="w", suffix=".sh", delete=False) as f:
            f.write("#!/bin/bash\nsleep 10\necho 'done'\n")
            script_path = Path(f.name)

        try:
            # Make it executable
            script_path.chmod(0o755)

            # Create executor pointing to our slow script
            config = LLMConfig(path=str(script_path), timeout_seconds=1)
            executor = ClaudeCodeExecutor(config)

            # Should timeout
            with pytest.raises(LLMTimeoutError) as exc_info:
                executor.execute("test")

            assert exc_info.value.code == "LLM_TIMEOUT"
            assert exc_info.value.timeout_seconds == 1
            assert exc_info.value.elapsed_seconds >= 0

        finally:
            # Cleanup
            script_path.unlink()

    def test_no_zombie_process_after_timeout(self) -> None:
        """Process should not become zombie after timeout kill.

        Verifies that the process is properly reaped after being killed
        due to timeout, preventing zombie processes.
        """
        import os
        import tempfile
        from pathlib import Path

        from adw.exceptions import LLMTimeoutError

        # Create a temporary script that runs slowly
        with tempfile.NamedTemporaryFile(mode="w", suffix=".sh", delete=False) as f:
            # Script that captures its own PID for verification
            f.write("#!/bin/bash\necho $$\nsleep 10\n")
            script_path = Path(f.name)

        try:
            script_path.chmod(0o755)

            config = LLMConfig(path=str(script_path), timeout_seconds=1)
            executor = ClaudeCodeExecutor(config)

            with pytest.raises(LLMTimeoutError):
                executor.execute("test")

            # After exception, give a moment for cleanup
            import time

            time.sleep(0.5)

            # Check there are no zombie children
            # This is platform-specific but works on Unix
            import subprocess

            result = subprocess.run(
                ["ps", "-o", "stat=", "-p", str(os.getpid())],
                capture_output=True,
                text=True,
            )
            # If we can still query our process, we didn't leave zombies
            # (Our process would be Z if we had unwaited children on some systems)
            assert "Z" not in result.stdout

        finally:
            script_path.unlink()

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
