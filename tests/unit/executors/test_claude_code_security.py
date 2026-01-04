"""Unit tests for ClaudeCodeExecutor security integration."""

from pathlib import Path

import pytest

from adw.exceptions import SecurityError
from adw.executors.claude_code import ClaudeCodeExecutor
from adw.models.config import LLMConfig
from adw.models.llm import ToolCall
from adw.security import SecurityInterceptor, ToolLogger


class TestExecutorSecurityIntegration:
    """Tests for security interceptor integration with executor."""

    def test_executor_accepts_security_interceptor(self) -> None:
        """Test that executor accepts security_interceptor parameter."""
        interceptor = SecurityInterceptor()
        executor = ClaudeCodeExecutor(
            config=LLMConfig(),
            security_interceptor=interceptor,
        )
        assert executor.security_interceptor is interceptor

    def test_executor_accepts_tool_logger(self, tmp_path: Path) -> None:
        """Test that executor accepts tool_logger parameter."""
        logger = ToolLogger(tmp_path)
        executor = ClaudeCodeExecutor(
            config=LLMConfig(),
            tool_logger=logger,
        )
        assert executor.tool_logger is logger

    def test_executor_accepts_allow_dangerous(self) -> None:
        """Test that executor accepts allow_dangerous parameter."""
        executor = ClaudeCodeExecutor(
            config=LLMConfig(),
            allow_dangerous=True,
        )
        assert executor.allow_dangerous is True

    def test_check_and_log_skipped_without_interceptor(self) -> None:
        """Test that security check is skipped without interceptor."""
        executor = ClaudeCodeExecutor(config=LLMConfig())
        tool_calls = [
            ToolCall(
                tool_name="Bash",
                arguments={"command": "rm -rf /"},
                result_summary="executed",
            )
        ]
        # Should not raise - no interceptor configured
        executor._check_and_log_tool_calls(tool_calls, 100)

    def test_blocked_tool_raises_security_error(self) -> None:
        """Test that blocked tool call raises SecurityError."""
        interceptor = SecurityInterceptor(allow_dangerous=False)
        executor = ClaudeCodeExecutor(
            config=LLMConfig(),
            security_interceptor=interceptor,
            allow_dangerous=False,
        )
        tool_calls = [
            ToolCall(
                tool_name="Bash",
                arguments={"command": "rm -rf /"},
                result_summary="executed",
            )
        ]
        with pytest.raises(SecurityError) as exc_info:
            executor._check_and_log_tool_calls(tool_calls, 100)

        assert exc_info.value.code == "DANGEROUS_COMMAND_BLOCKED"
        assert exc_info.value.tool_name == "Bash"

    def test_allow_dangerous_does_not_raise(self) -> None:
        """Test that allow_dangerous=True logs but doesn't raise."""
        interceptor = SecurityInterceptor(allow_dangerous=True)
        executor = ClaudeCodeExecutor(
            config=LLMConfig(),
            security_interceptor=interceptor,
            allow_dangerous=True,
        )
        tool_calls = [
            ToolCall(
                tool_name="Bash",
                arguments={"command": "rm -rf /"},
                result_summary="executed",
            )
        ]
        # Should not raise with allow_dangerous=True
        executor._check_and_log_tool_calls(tool_calls, 100)

    def test_tool_logger_logs_blocked_calls(self, tmp_path: Path) -> None:
        """Test that tool logger records blocked calls."""
        interceptor = SecurityInterceptor(allow_dangerous=True)
        logger = ToolLogger(tmp_path)
        executor = ClaudeCodeExecutor(
            config=LLMConfig(),
            security_interceptor=interceptor,
            tool_logger=logger,
            allow_dangerous=True,
        )
        tool_calls = [
            ToolCall(
                tool_name="Bash",
                arguments={"command": "rm -rf /"},
                result_summary="executed",
            )
        ]
        executor._check_and_log_tool_calls(tool_calls, 100)

        # Check that log was written
        entries = logger.get_tool_history()
        assert len(entries) == 1
        assert entries[0].tool_name == "Bash"
        # blocked=False because allow_dangerous=True makes it WARNING not BLOCKED
        assert entries[0].block_reason is not None
        assert "Warning" in entries[0].block_reason

    def test_tool_logger_logs_allowed_calls(self, tmp_path: Path) -> None:
        """Test that tool logger records allowed calls."""
        interceptor = SecurityInterceptor()
        logger = ToolLogger(tmp_path)
        executor = ClaudeCodeExecutor(
            config=LLMConfig(),
            security_interceptor=interceptor,
            tool_logger=logger,
        )
        tool_calls = [
            ToolCall(
                tool_name="Bash",
                arguments={"command": "ls -la"},
                result_summary="executed",
            )
        ]
        executor._check_and_log_tool_calls(tool_calls, 100)

        # Check that log was written
        entries = logger.get_tool_history()
        assert len(entries) == 1
        assert entries[0].tool_name == "Bash"
        assert entries[0].blocked is False
        assert entries[0].block_reason is None
