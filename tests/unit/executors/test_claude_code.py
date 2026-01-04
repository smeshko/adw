"""Unit tests for ClaudeCodeExecutor.

These tests validate the ClaudeCodeExecutor implementation against
the LLMExecutor Protocol, using mocked subprocess execution.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from adw.executors.base import LLMExecutor
from adw.executors.claude_code import ClaudeCodeExecutor
from adw.models.config import LLMConfig
from adw.models.llm import LLMResult


def _run_async(coro):
    """Helper to run async code without deprecation warnings."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


class TestClaudeCodeExecutorClass:
    """Tests for ClaudeCodeExecutor class structure."""

    def test_executor_exists(self) -> None:
        """ClaudeCodeExecutor class should exist and be importable."""
        assert ClaudeCodeExecutor is not None

    def test_implements_llm_executor_protocol(self) -> None:
        """ClaudeCodeExecutor should implement LLMExecutor Protocol."""
        config = LLMConfig(path="claude")
        executor = ClaudeCodeExecutor(config)
        assert isinstance(executor, LLMExecutor)

    def test_constructor_accepts_llm_config(self) -> None:
        """Constructor should accept LLMConfig."""
        config = LLMConfig(
            path="/usr/bin/claude",
            timeout_seconds=600,
            max_retries=5,
        )
        executor = ClaudeCodeExecutor(config)
        assert executor.config == config

    def test_has_execute_method(self) -> None:
        """Executor should have execute method with correct signature."""
        config = LLMConfig(path="claude")
        executor = ClaudeCodeExecutor(config)
        assert hasattr(executor, "execute")
        assert callable(executor.execute)


class TestClaudeCodeExecutorExecute:
    """Tests for ClaudeCodeExecutor.execute() method."""

    @pytest.fixture
    def executor(self) -> ClaudeCodeExecutor:
        """Create executor with default config."""
        config = LLMConfig(path="claude")
        return ClaudeCodeExecutor(config)

    @pytest.fixture
    def mock_subprocess(self):
        """Mock asyncio subprocess for deterministic tests."""
        with patch("adw.executors.claude_code.asyncio") as mock_asyncio:
            # Create mock process
            process = AsyncMock()
            process.stdout = AsyncMock()
            process.stderr = AsyncMock()
            process.stdout.readline = AsyncMock(
                side_effect=[
                    b"Line 1\n",
                    b"Line 2\n",
                    b"",  # EOF
                ]
            )
            process.stderr.readline = AsyncMock(side_effect=[b""])  # EOF for stderr
            process.wait = AsyncMock(return_value=None)
            process.returncode = 0

            # Mock create_subprocess_exec to return our process
            mock_asyncio.create_subprocess_exec = AsyncMock(return_value=process)
            mock_asyncio.subprocess = asyncio.subprocess

            # Make asyncio.run use our helper to avoid deprecation
            mock_asyncio.run = _run_async

            # Passthrough for create_task, gather, wait_for
            mock_asyncio.create_task = asyncio.create_task
            mock_asyncio.gather = asyncio.gather
            mock_asyncio.wait_for = asyncio.wait_for
            mock_asyncio.TimeoutError = asyncio.TimeoutError

            yield mock_asyncio, process

    def test_execute_returns_llm_result(
        self, executor: ClaudeCodeExecutor, mock_subprocess
    ) -> None:
        """execute() should return an LLMResult."""
        mock_asyncio, process = mock_subprocess

        with patch("shutil.which", return_value="/usr/bin/claude"):
            result = executor.execute("Test prompt")

        assert isinstance(result, LLMResult)

    def test_execute_with_timeout_parameter(
        self, executor: ClaudeCodeExecutor, mock_subprocess
    ) -> None:
        """execute() should accept optional timeout parameter."""
        mock_asyncio, process = mock_subprocess

        with patch("shutil.which", return_value="/usr/bin/claude"):
            result = executor.execute("Test prompt", timeout=60)

        assert isinstance(result, LLMResult)

    def test_execute_captures_content(
        self, executor: ClaudeCodeExecutor, mock_subprocess
    ) -> None:
        """execute() should capture subprocess output as content."""
        mock_asyncio, process = mock_subprocess

        with patch("shutil.which", return_value="/usr/bin/claude"):
            result = executor.execute("Test prompt")

        assert "Line 1" in result.content
        assert "Line 2" in result.content

    def test_execute_returns_success_on_zero_exit(
        self, executor: ClaudeCodeExecutor, mock_subprocess
    ) -> None:
        """execute() should return success=True when process exits with 0."""
        mock_asyncio, process = mock_subprocess
        process.returncode = 0

        with patch("shutil.which", return_value="/usr/bin/claude"):
            result = executor.execute("Test prompt")

        assert result.success is True

    def test_execute_returns_failure_on_non_zero_exit(
        self, executor: ClaudeCodeExecutor, mock_subprocess
    ) -> None:
        """execute() should return success=False when process exits non-zero."""
        mock_asyncio, process = mock_subprocess
        process.returncode = 1
        process.stderr.readline = AsyncMock(side_effect=[b"Error occurred\n", b""])

        with patch("shutil.which", return_value="/usr/bin/claude"):
            result = executor.execute("Test prompt")

        assert result.success is False
        assert result.error is not None

    def test_execute_includes_duration_ms(
        self, executor: ClaudeCodeExecutor, mock_subprocess
    ) -> None:
        """execute() should include execution duration in result."""
        mock_asyncio, process = mock_subprocess

        with patch("shutil.which", return_value="/usr/bin/claude"):
            result = executor.execute("Test prompt")

        assert result.duration_ms >= 0


class TestSubprocessExecution:
    """Tests for subprocess execution (Task 2)."""

    @pytest.fixture
    def executor(self) -> ClaudeCodeExecutor:
        """Create executor with default config."""
        config = LLMConfig(path="claude")
        return ClaudeCodeExecutor(config)

    def test_uses_create_subprocess_exec(self, executor: ClaudeCodeExecutor) -> None:
        """Should use asyncio.create_subprocess_exec for spawning."""
        with patch("adw.executors.claude_code.asyncio") as mock_asyncio:
            # Create mock process
            process = AsyncMock()
            process.stdout = AsyncMock()
            process.stderr = AsyncMock()
            process.stdout.readline = AsyncMock(side_effect=[b""])
            process.stderr.readline = AsyncMock(side_effect=[b""])
            process.wait = AsyncMock(return_value=None)
            process.returncode = 0

            mock_asyncio.create_subprocess_exec = AsyncMock(return_value=process)
            mock_asyncio.subprocess = asyncio.subprocess
            mock_asyncio.run = _run_async
            mock_asyncio.create_task = asyncio.create_task
            mock_asyncio.gather = asyncio.gather
            mock_asyncio.wait_for = asyncio.wait_for

            with patch("shutil.which", return_value="/usr/bin/claude"):
                executor.execute("Test prompt")

            # Verify create_subprocess_exec was called
            mock_asyncio.create_subprocess_exec.assert_called_once()

    def test_passes_print_flag(self, executor: ClaudeCodeExecutor) -> None:
        """Should pass --print flag for machine-readable output."""
        with patch("adw.executors.claude_code.asyncio") as mock_asyncio:
            # Create mock process
            process = AsyncMock()
            process.stdout = AsyncMock()
            process.stderr = AsyncMock()
            process.stdout.readline = AsyncMock(side_effect=[b""])
            process.stderr.readline = AsyncMock(side_effect=[b""])
            process.wait = AsyncMock(return_value=None)
            process.returncode = 0

            mock_asyncio.create_subprocess_exec = AsyncMock(return_value=process)
            mock_asyncio.subprocess = asyncio.subprocess
            mock_asyncio.run = _run_async
            mock_asyncio.create_task = asyncio.create_task
            mock_asyncio.gather = asyncio.gather
            mock_asyncio.wait_for = asyncio.wait_for

            with patch("shutil.which", return_value="/usr/bin/claude"):
                executor.execute("Test prompt")

            # Verify --print flag was passed
            call_args = mock_asyncio.create_subprocess_exec.call_args
            args = call_args[0]  # positional args
            assert "--print" in args

    def test_sets_up_stdout_pipe(self, executor: ClaudeCodeExecutor) -> None:
        """Should set up stdout pipe for capture."""
        with patch("adw.executors.claude_code.asyncio") as mock_asyncio:
            # Create mock process
            process = AsyncMock()
            process.stdout = AsyncMock()
            process.stderr = AsyncMock()
            process.stdout.readline = AsyncMock(side_effect=[b""])
            process.stderr.readline = AsyncMock(side_effect=[b""])
            process.wait = AsyncMock(return_value=None)
            process.returncode = 0

            mock_asyncio.create_subprocess_exec = AsyncMock(return_value=process)
            mock_asyncio.subprocess = asyncio.subprocess
            mock_asyncio.run = _run_async
            mock_asyncio.create_task = asyncio.create_task
            mock_asyncio.gather = asyncio.gather
            mock_asyncio.wait_for = asyncio.wait_for

            with patch("shutil.which", return_value="/usr/bin/claude"):
                executor.execute("Test prompt")

            # Verify stdout pipe was set up
            call_kwargs = mock_asyncio.create_subprocess_exec.call_args[1]
            assert call_kwargs.get("stdout") == asyncio.subprocess.PIPE

    def test_sets_up_stderr_pipe(self, executor: ClaudeCodeExecutor) -> None:
        """Should set up stderr pipe for capture."""
        with patch("adw.executors.claude_code.asyncio") as mock_asyncio:
            # Create mock process
            process = AsyncMock()
            process.stdout = AsyncMock()
            process.stderr = AsyncMock()
            process.stdout.readline = AsyncMock(side_effect=[b""])
            process.stderr.readline = AsyncMock(side_effect=[b""])
            process.wait = AsyncMock(return_value=None)
            process.returncode = 0

            mock_asyncio.create_subprocess_exec = AsyncMock(return_value=process)
            mock_asyncio.subprocess = asyncio.subprocess
            mock_asyncio.run = _run_async
            mock_asyncio.create_task = asyncio.create_task
            mock_asyncio.gather = asyncio.gather
            mock_asyncio.wait_for = asyncio.wait_for

            with patch("shutil.which", return_value="/usr/bin/claude"):
                executor.execute("Test prompt")

            # Verify stderr pipe was set up
            call_kwargs = mock_asyncio.create_subprocess_exec.call_args[1]
            assert call_kwargs.get("stderr") == asyncio.subprocess.PIPE

    def test_uses_asyncio_run_wrapper(self, executor: ClaudeCodeExecutor) -> None:
        """execute() should use asyncio.run() to wrap async execution."""
        with patch("adw.executors.claude_code.asyncio") as mock_asyncio:
            # Create mock process
            process = AsyncMock()
            process.stdout = AsyncMock()
            process.stderr = AsyncMock()
            process.stdout.readline = AsyncMock(side_effect=[b""])
            process.stderr.readline = AsyncMock(side_effect=[b""])
            process.wait = AsyncMock(return_value=None)
            process.returncode = 0

            mock_asyncio.create_subprocess_exec = AsyncMock(return_value=process)
            mock_asyncio.subprocess = asyncio.subprocess
            mock_asyncio.create_task = asyncio.create_task
            mock_asyncio.gather = asyncio.gather
            mock_asyncio.wait_for = asyncio.wait_for

            # Track if asyncio.run was called
            run_called = False

            def track_run(coro):
                nonlocal run_called
                run_called = True
                return _run_async(coro)

            mock_asyncio.run = track_run

            with patch("shutil.which", return_value="/usr/bin/claude"):
                executor.execute("Test prompt")

            assert run_called, "asyncio.run() was not called"


class TestRealTimeStreaming:
    """Tests for real-time streaming output (Task 3)."""

    @pytest.fixture
    def executor(self) -> ClaudeCodeExecutor:
        """Create executor with default config."""
        config = LLMConfig(path="claude")
        return ClaudeCodeExecutor(config)

    def test_reads_stdout_line_by_line(self, executor: ClaudeCodeExecutor) -> None:
        """Should read stdout line by line as it becomes available."""
        with patch("adw.executors.claude_code.asyncio") as mock_asyncio:
            process = AsyncMock()
            process.stdout = AsyncMock()
            process.stderr = AsyncMock()
            # Simulate multiple lines being read
            process.stdout.readline = AsyncMock(
                side_effect=[
                    b"First line\n",
                    b"Second line\n",
                    b"Third line\n",
                    b"",  # EOF
                ]
            )
            process.stderr.readline = AsyncMock(side_effect=[b""])
            process.wait = AsyncMock(return_value=None)
            process.returncode = 0

            mock_asyncio.create_subprocess_exec = AsyncMock(return_value=process)
            mock_asyncio.subprocess = asyncio.subprocess
            mock_asyncio.run = _run_async
            mock_asyncio.create_task = asyncio.create_task
            mock_asyncio.gather = asyncio.gather
            mock_asyncio.wait_for = asyncio.wait_for

            with patch("shutil.which", return_value="/usr/bin/claude"):
                result = executor.execute("Test prompt")

            # Verify readline was called multiple times
            assert process.stdout.readline.call_count >= 4
            # Verify content includes all lines
            assert "First line" in result.content
            assert "Second line" in result.content
            assert "Third line" in result.content

    def test_forwards_output_to_rich_console_when_enabled(self) -> None:
        """Should forward output to Rich console when show_llm_output=True.

        Note: As of Story UX-FIX-ISS-001, show_llm_output defaults to False.
        This test verifies output is forwarded when explicitly enabled.
        """
        import json

        from rich.console import Console

        # Create executor with show_llm_output=True to test console forwarding
        config = LLMConfig(path="claude")
        executor = ClaudeCodeExecutor(config, show_llm_output=True)

        mock_console = MagicMock(spec=Console)
        executor.console = mock_console

        # Use valid stream-json format with content_block_delta
        stream_json = json.dumps({
            "type": "content_block_delta",
            "delta": {"type": "text_delta", "text": "Hello world"}
        })

        with patch("adw.executors.claude_code.asyncio") as mock_asyncio:
            process = AsyncMock()
            process.stdout = AsyncMock()
            process.stderr = AsyncMock()
            process.stdout.readline = AsyncMock(
                side_effect=[
                    (stream_json + "\n").encode(),
                    b"",  # EOF
                ]
            )
            process.stderr.readline = AsyncMock(side_effect=[b""])
            process.wait = AsyncMock(return_value=None)
            process.returncode = 0

            mock_asyncio.create_subprocess_exec = AsyncMock(return_value=process)
            mock_asyncio.subprocess = asyncio.subprocess
            mock_asyncio.run = _run_async
            mock_asyncio.create_task = asyncio.create_task
            mock_asyncio.gather = asyncio.gather
            mock_asyncio.wait_for = asyncio.wait_for

            with patch("shutil.which", return_value="/usr/bin/claude"):
                executor.execute("Test prompt")

            # Verify console.print was called with the extracted text
            mock_console.print.assert_called()

    def test_streaming_does_not_block_on_empty_lines(
        self, executor: ClaudeCodeExecutor
    ) -> None:
        """Streaming should handle empty lines without blocking."""
        with patch("adw.executors.claude_code.asyncio") as mock_asyncio:
            process = AsyncMock()
            process.stdout = AsyncMock()
            process.stderr = AsyncMock()
            # Include empty lines in output
            process.stdout.readline = AsyncMock(
                side_effect=[
                    b"Line 1\n",
                    b"\n",  # Empty line
                    b"Line 2\n",
                    b"",  # EOF
                ]
            )
            process.stderr.readline = AsyncMock(side_effect=[b""])
            process.wait = AsyncMock(return_value=None)
            process.returncode = 0

            mock_asyncio.create_subprocess_exec = AsyncMock(return_value=process)
            mock_asyncio.subprocess = asyncio.subprocess
            mock_asyncio.run = _run_async
            mock_asyncio.create_task = asyncio.create_task
            mock_asyncio.gather = asyncio.gather
            mock_asyncio.wait_for = asyncio.wait_for

            with patch("shutil.which", return_value="/usr/bin/claude"):
                result = executor.execute("Test prompt")

            # Should complete without blocking
            assert result.success is True
            assert "Line 1" in result.content
            assert "Line 2" in result.content

    def test_accepts_custom_console(self) -> None:
        """Executor should accept custom Rich console."""
        from rich.console import Console

        custom_console = Console(force_terminal=True)
        config = LLMConfig(path="claude")
        executor = ClaudeCodeExecutor(config, console=custom_console)

        assert executor.console is custom_console

    def test_uses_create_task_for_concurrent_processing(
        self, executor: ClaudeCodeExecutor
    ) -> None:
        """Should use asyncio.create_task() for concurrent stdout/stderr processing."""
        with patch("adw.executors.claude_code.asyncio") as mock_asyncio:
            process = AsyncMock()
            process.stdout = AsyncMock()
            process.stderr = AsyncMock()
            process.stdout.readline = AsyncMock(side_effect=[b"Output\n", b""])
            process.stderr.readline = AsyncMock(side_effect=[b""])
            process.wait = AsyncMock(return_value=None)
            process.returncode = 0

            mock_asyncio.create_subprocess_exec = AsyncMock(return_value=process)
            mock_asyncio.subprocess = asyncio.subprocess
            mock_asyncio.run = _run_async
            mock_asyncio.gather = asyncio.gather
            mock_asyncio.wait_for = asyncio.wait_for

            # Track create_task calls
            create_task_calls = []
            real_create_task = asyncio.create_task

            def track_create_task(coro):
                create_task_calls.append(coro)
                return real_create_task(coro)

            mock_asyncio.create_task = track_create_task

            with patch("shutil.which", return_value="/usr/bin/claude"):
                executor.execute("Test prompt")

            # Should have created 2 tasks (stdout and stderr)
            assert len(create_task_calls) == 2


class TestTimeoutEnforcement:
    """Tests for timeout enforcement."""

    @pytest.fixture
    def executor(self) -> ClaudeCodeExecutor:
        """Create executor with short timeout."""
        config = LLMConfig(path="claude", timeout_seconds=1)
        return ClaudeCodeExecutor(config)

    def test_timeout_raises_llm_timeout_error(
        self, executor: ClaudeCodeExecutor
    ) -> None:
        """Should raise LLMTimeoutError with elapsed and configured timeout."""
        from adw.exceptions import LLMTimeoutError

        with patch("adw.executors.claude_code.asyncio") as mock_asyncio:
            process = AsyncMock()
            process.stdout = AsyncMock()
            process.stderr = AsyncMock()
            process.returncode = None  # Not completed
            process.terminate = MagicMock()
            process.kill = MagicMock()

            # Simulate slow readline that will timeout
            async def slow_readline():
                await asyncio.sleep(10)  # Much longer than timeout
                return b""

            process.stdout.readline = slow_readline
            process.stderr.readline = slow_readline
            process.wait = AsyncMock(return_value=None)

            mock_asyncio.create_subprocess_exec = AsyncMock(return_value=process)
            mock_asyncio.subprocess = asyncio.subprocess
            mock_asyncio.run = _run_async
            mock_asyncio.create_task = asyncio.create_task
            mock_asyncio.gather = asyncio.gather
            mock_asyncio.TimeoutError = asyncio.TimeoutError

            # Use real wait_for to trigger actual timeout
            mock_asyncio.wait_for = asyncio.wait_for

            with (
                patch("shutil.which", return_value="/usr/bin/claude"),
                pytest.raises(LLMTimeoutError) as exc_info,
            ):
                executor.execute("Test prompt", timeout=1)

            assert exc_info.value.code == "LLM_TIMEOUT"
            assert "timed out" in exc_info.value.message
            assert exc_info.value.timeout_seconds == 1
            assert exc_info.value.elapsed_seconds >= 0
            assert exc_info.value.recoverable is True

    def test_timeout_kills_process(self, executor: ClaudeCodeExecutor) -> None:
        """Should kill process on timeout to ensure cleanup."""
        from adw.exceptions import LLMTimeoutError

        with patch("adw.executors.claude_code.asyncio") as mock_asyncio:
            process = AsyncMock()
            process.stdout = AsyncMock()
            process.stderr = AsyncMock()
            process.returncode = None
            process.terminate = MagicMock()
            process.kill = MagicMock()

            # Simulate slow readline
            async def slow_readline():
                await asyncio.sleep(10)
                return b""

            process.stdout.readline = slow_readline
            process.stderr.readline = slow_readline
            process.wait = AsyncMock(return_value=None)

            mock_asyncio.create_subprocess_exec = AsyncMock(return_value=process)
            mock_asyncio.subprocess = asyncio.subprocess
            mock_asyncio.run = _run_async
            mock_asyncio.create_task = asyncio.create_task
            mock_asyncio.gather = asyncio.gather
            mock_asyncio.wait_for = asyncio.wait_for
            mock_asyncio.TimeoutError = asyncio.TimeoutError

            with (
                patch("shutil.which", return_value="/usr/bin/claude"),
                pytest.raises(LLMTimeoutError),
            ):
                executor.execute("Test prompt", timeout=1)

            # Verify process was killed (not just terminated)
            process.kill.assert_called_once()
            # Verify wait was called to clean up zombie process
            process.wait.assert_awaited()


class TestOutputParsing:
    """Tests for Claude Code output parsing (Task 4)."""

    @pytest.fixture
    def executor(self) -> ClaudeCodeExecutor:
        """Create executor with default config."""
        config = LLMConfig(path="claude")
        return ClaudeCodeExecutor(config)

    def test_parses_plain_text_content(self, executor: ClaudeCodeExecutor) -> None:
        """Should handle plain text that isn't JSON."""
        raw_output = "Hello, World!\nThis is plain text."
        parsed = executor._parse_output(raw_output)

        assert "Hello, World!" in parsed["content"]
        assert "This is plain text." in parsed["content"]
        assert parsed["tool_calls"] == []
        assert parsed["tokens_used"] == 0

    def test_parses_assistant_message_text(self, executor: ClaudeCodeExecutor) -> None:
        """Should extract text from assistant message."""
        import json

        raw_output = json.dumps(
            {
                "type": "assistant",
                "message": {
                    "content": [{"type": "text", "text": "Hello from Claude!"}]
                },
            }
        )
        parsed = executor._parse_output(raw_output)

        assert parsed["content"] == "Hello from Claude!"

    def test_parses_tool_calls(self, executor: ClaudeCodeExecutor) -> None:
        """Should extract tool calls from assistant message."""
        import json

        raw_output = json.dumps(
            {
                "type": "assistant",
                "message": {
                    "content": [
                        {
                            "type": "tool_use",
                            "name": "read_file",
                            "input": {"path": "/src/main.py"},
                        }
                    ]
                },
            }
        )
        parsed = executor._parse_output(raw_output)

        assert len(parsed["tool_calls"]) == 1
        assert parsed["tool_calls"][0].tool_name == "read_file"
        assert parsed["tool_calls"][0].arguments == {"path": "/src/main.py"}

    def test_parses_multiple_tool_calls(self, executor: ClaudeCodeExecutor) -> None:
        """Should extract multiple tool calls."""
        import json

        raw_output = json.dumps(
            {
                "type": "assistant",
                "message": {
                    "content": [
                        {
                            "type": "tool_use",
                            "name": "read_file",
                            "input": {"path": "/src/a.py"},
                        },
                        {"type": "text", "text": "Reading files..."},
                        {
                            "type": "tool_use",
                            "name": "write_file",
                            "input": {"path": "/src/b.py", "content": "..."},
                        },
                    ]
                },
            }
        )
        parsed = executor._parse_output(raw_output)

        assert len(parsed["tool_calls"]) == 2
        assert parsed["tool_calls"][0].tool_name == "read_file"
        assert parsed["tool_calls"][1].tool_name == "write_file"
        assert "Reading files..." in parsed["content"]

    def test_parses_token_usage_from_result(self, executor: ClaudeCodeExecutor) -> None:
        """Should extract token usage from result message."""
        import json

        raw_output = json.dumps(
            {
                "type": "result",
                "usage": {"input_tokens": 100, "output_tokens": 200},
            }
        )
        parsed = executor._parse_output(raw_output)

        assert parsed["tokens_used"] == 300

    def test_parses_content_block_delta(self, executor: ClaudeCodeExecutor) -> None:
        """Should extract text from streaming content_block_delta."""
        import json

        lines = [
            json.dumps(
                {
                    "type": "content_block_delta",
                    "delta": {"type": "text_delta", "text": "Hello "},
                }
            ),
            json.dumps(
                {
                    "type": "content_block_delta",
                    "delta": {"type": "text_delta", "text": "World!"},
                }
            ),
        ]
        raw_output = "\n".join(lines)
        parsed = executor._parse_output(raw_output)

        assert parsed["content"] == "Hello World!"

    def test_parses_message_delta_usage(self, executor: ClaudeCodeExecutor) -> None:
        """Should extract usage from message_delta."""
        import json

        raw_output = json.dumps(
            {
                "type": "message_delta",
                "usage": {"input_tokens": 50, "output_tokens": 150},
            }
        )
        parsed = executor._parse_output(raw_output)

        assert parsed["tokens_used"] == 200

    def test_handles_empty_output(self, executor: ClaudeCodeExecutor) -> None:
        """Should handle empty output gracefully."""
        parsed = executor._parse_output("")

        assert parsed["content"] == ""
        assert parsed["tool_calls"] == []
        assert parsed["tokens_used"] == 0

    def test_handles_mixed_json_and_text(self, executor: ClaudeCodeExecutor) -> None:
        """Should handle output with both JSON and plain text lines."""
        import json

        lines = [
            "Some debug output",
            json.dumps(
                {
                    "type": "assistant",
                    "message": {"content": [{"type": "text", "text": "Response"}]},
                }
            ),
            "More debug info",
        ]
        raw_output = "\n".join(lines)
        parsed = executor._parse_output(raw_output)

        # All content should be captured
        assert "Some debug output" in parsed["content"]
        assert "Response" in parsed["content"]
        assert "More debug info" in parsed["content"]


class TestErrorHandling:
    """Tests for error handling (Task 5)."""

    @pytest.fixture
    def executor(self) -> ClaudeCodeExecutor:
        """Create executor with default config."""
        config = LLMConfig(path="claude")
        return ClaudeCodeExecutor(config)

    def test_raises_llm_error_when_path_not_found(self) -> None:
        """Should raise LLMError with CLAUDE_NOT_FOUND when path doesn't exist."""
        from adw.exceptions import LLMError

        config = LLMConfig(path="nonexistent-claude-binary")
        executor = ClaudeCodeExecutor(config)

        with patch("shutil.which", return_value=None):
            with pytest.raises(LLMError) as exc_info:
                executor.execute("Test prompt")

            assert exc_info.value.code == "CLAUDE_NOT_FOUND"
            assert "nonexistent-claude-binary" in exc_info.value.message

    def test_error_includes_suggestion(self) -> None:
        """Error should include helpful suggestion."""
        from adw.exceptions import LLMError

        config = LLMConfig(path="claude")
        executor = ClaudeCodeExecutor(config)

        with patch("shutil.which", return_value=None):
            with pytest.raises(LLMError) as exc_info:
                executor.execute("Test prompt")

            assert exc_info.value.suggestion is not None
            assert "adw.yaml" in exc_info.value.suggestion

    def test_error_is_not_recoverable(self) -> None:
        """CLAUDE_NOT_FOUND error should not be recoverable."""
        from adw.exceptions import LLMError

        config = LLMConfig(path="claude")
        executor = ClaudeCodeExecutor(config)

        with patch("shutil.which", return_value=None):
            with pytest.raises(LLMError) as exc_info:
                executor.execute("Test prompt")

            assert exc_info.value.recoverable is False

    def test_handles_absolute_path_not_found(self) -> None:
        """Should handle absolute paths that don't exist."""
        from adw.exceptions import LLMError

        config = LLMConfig(path="/nonexistent/path/to/claude")
        executor = ClaudeCodeExecutor(config)

        with pytest.raises(LLMError) as exc_info:
            executor.execute("Test prompt")

        assert exc_info.value.code == "CLAUDE_NOT_FOUND"
        assert "/nonexistent/path/to/claude" in exc_info.value.message

    def test_subprocess_error_returns_failure_result(
        self, executor: ClaudeCodeExecutor
    ) -> None:
        """Subprocess errors should return LLMResult with success=False."""
        with patch("adw.executors.claude_code.asyncio") as mock_asyncio:
            process = AsyncMock()
            process.stdout = AsyncMock()
            process.stderr = AsyncMock()
            process.stdout.readline = AsyncMock(side_effect=[b""])
            process.stderr.readline = AsyncMock(side_effect=[b"Process crashed\n", b""])
            process.wait = AsyncMock(return_value=None)
            process.returncode = 1  # Non-zero exit

            mock_asyncio.create_subprocess_exec = AsyncMock(return_value=process)
            mock_asyncio.subprocess = asyncio.subprocess
            mock_asyncio.run = _run_async
            mock_asyncio.create_task = asyncio.create_task
            mock_asyncio.gather = asyncio.gather
            mock_asyncio.wait_for = asyncio.wait_for

            with patch("shutil.which", return_value="/usr/bin/claude"):
                result = executor.execute("Test prompt")

            assert result.success is False
            assert result.error is not None

    def test_stderr_included_in_error_message(
        self, executor: ClaudeCodeExecutor
    ) -> None:
        """stderr content should be included in error message."""
        with patch("adw.executors.claude_code.asyncio") as mock_asyncio:
            process = AsyncMock()
            process.stdout = AsyncMock()
            process.stderr = AsyncMock()
            process.stdout.readline = AsyncMock(side_effect=[b""])
            process.stderr.readline = AsyncMock(
                side_effect=[b"Error: Rate limit exceeded\n", b""]
            )
            process.wait = AsyncMock(return_value=None)
            process.returncode = 1

            mock_asyncio.create_subprocess_exec = AsyncMock(return_value=process)
            mock_asyncio.subprocess = asyncio.subprocess
            mock_asyncio.run = _run_async
            mock_asyncio.create_task = asyncio.create_task
            mock_asyncio.gather = asyncio.gather
            mock_asyncio.wait_for = asyncio.wait_for

            with patch("shutil.which", return_value="/usr/bin/claude"):
                result = executor.execute("Test prompt")

            assert "Rate limit exceeded" in result.error

    def test_fallback_error_message_when_no_stderr(
        self, executor: ClaudeCodeExecutor
    ) -> None:
        """Should provide fallback error message when stderr is empty."""
        with patch("adw.executors.claude_code.asyncio") as mock_asyncio:
            process = AsyncMock()
            process.stdout = AsyncMock()
            process.stderr = AsyncMock()
            process.stdout.readline = AsyncMock(side_effect=[b""])
            process.stderr.readline = AsyncMock(side_effect=[b""])  # Empty stderr
            process.wait = AsyncMock(return_value=None)
            process.returncode = 42

            mock_asyncio.create_subprocess_exec = AsyncMock(return_value=process)
            mock_asyncio.subprocess = asyncio.subprocess
            mock_asyncio.run = _run_async
            mock_asyncio.create_task = asyncio.create_task
            mock_asyncio.gather = asyncio.gather
            mock_asyncio.wait_for = asyncio.wait_for

            with patch("shutil.which", return_value="/usr/bin/claude"):
                result = executor.execute("Test prompt")

            assert result.success is False
            assert "42" in result.error  # Exit code in fallback message


class TestPathConfiguration:
    """Tests for path configuration (Task 6)."""

    def test_uses_llm_config_path(self) -> None:
        """Should use LLMConfig.path for Claude executable."""
        config = LLMConfig(path="/custom/path/to/claude")
        executor = ClaudeCodeExecutor(config)

        assert executor.config.path == "/custom/path/to/claude"

    def test_default_path_is_claude(self) -> None:
        """Default path should be 'claude' (assumes in PATH)."""
        config = LLMConfig()

        assert config.path == "claude"

    def test_uses_shutil_which_for_path_lookup(self) -> None:
        """Should use shutil.which() to find executable in PATH."""
        config = LLMConfig(path="claude")
        executor = ClaudeCodeExecutor(config)

        with patch("shutil.which") as mock_which:
            mock_which.return_value = "/usr/local/bin/claude"

            with patch("adw.executors.claude_code.asyncio") as mock_asyncio:
                process = AsyncMock()
                process.stdout = AsyncMock()
                process.stderr = AsyncMock()
                process.stdout.readline = AsyncMock(side_effect=[b""])
                process.stderr.readline = AsyncMock(side_effect=[b""])
                process.wait = AsyncMock(return_value=None)
                process.returncode = 0

                mock_asyncio.create_subprocess_exec = AsyncMock(return_value=process)
                mock_asyncio.subprocess = asyncio.subprocess
                mock_asyncio.run = _run_async
                mock_asyncio.create_task = asyncio.create_task
                mock_asyncio.gather = asyncio.gather
                mock_asyncio.wait_for = asyncio.wait_for

                executor.execute("Test prompt")

            # Verify shutil.which was called with the path
            mock_which.assert_called_once_with("claude")

    def test_supports_absolute_paths(self) -> None:
        """Should support absolute paths from config."""
        import os
        import tempfile
        from pathlib import Path as PathlibPath

        # Create a temporary file to act as the executable
        with tempfile.NamedTemporaryFile(delete=False) as f:
            temp_path = f.name

        try:
            config = LLMConfig(path=temp_path)
            executor = ClaudeCodeExecutor(config)

            # The path should be checked directly (file exists)
            path = executor._verify_claude_path()
            assert path == PathlibPath(temp_path)
        finally:
            os.unlink(temp_path)

    def test_absolute_path_bypasses_which(self) -> None:
        """Absolute paths should not call shutil.which()."""
        import os
        import tempfile

        # Create a temporary file to act as the executable
        with tempfile.NamedTemporaryFile(delete=False) as f:
            temp_path = f.name

        try:
            config = LLMConfig(path=temp_path)
            executor = ClaudeCodeExecutor(config)

            with patch("shutil.which") as mock_which:
                executor._verify_claude_path()
                # shutil.which should NOT be called for absolute paths
                mock_which.assert_not_called()
        finally:
            os.unlink(temp_path)

    def test_relative_path_uses_which(self) -> None:
        """Relative paths (like 'claude') should use shutil.which()."""
        config = LLMConfig(path="claude")
        executor = ClaudeCodeExecutor(config)

        with patch("shutil.which", return_value="/found/path/claude"):
            path = executor._verify_claude_path()

            assert str(path) == "/found/path/claude"


class TestModelConfiguration:
    """Tests for model configuration."""

    def test_passes_model_flag_when_configured(self) -> None:
        """Should pass --model flag when model is configured."""
        config = LLMConfig(path="claude", model="claude-3-opus")
        executor = ClaudeCodeExecutor(config)

        with patch("adw.executors.claude_code.asyncio") as mock_asyncio:
            process = AsyncMock()
            process.stdout = AsyncMock()
            process.stderr = AsyncMock()
            process.stdout.readline = AsyncMock(side_effect=[b""])
            process.stderr.readline = AsyncMock(side_effect=[b""])
            process.wait = AsyncMock(return_value=None)
            process.returncode = 0

            mock_asyncio.create_subprocess_exec = AsyncMock(return_value=process)
            mock_asyncio.subprocess = asyncio.subprocess
            mock_asyncio.run = _run_async
            mock_asyncio.create_task = asyncio.create_task
            mock_asyncio.gather = asyncio.gather
            mock_asyncio.wait_for = asyncio.wait_for

            with patch("shutil.which", return_value="/usr/bin/claude"):
                executor.execute("Test prompt")

            # Verify --model flag was passed
            call_args = mock_asyncio.create_subprocess_exec.call_args
            args = call_args[0]  # positional args
            assert "--model" in args
            assert "claude-3-opus" in args

    def test_no_model_flag_when_not_configured(self) -> None:
        """Should not pass --model flag when model is not configured."""
        config = LLMConfig(path="claude")  # No model specified
        executor = ClaudeCodeExecutor(config)

        with patch("adw.executors.claude_code.asyncio") as mock_asyncio:
            process = AsyncMock()
            process.stdout = AsyncMock()
            process.stderr = AsyncMock()
            process.stdout.readline = AsyncMock(side_effect=[b""])
            process.stderr.readline = AsyncMock(side_effect=[b""])
            process.wait = AsyncMock(return_value=None)
            process.returncode = 0

            mock_asyncio.create_subprocess_exec = AsyncMock(return_value=process)
            mock_asyncio.subprocess = asyncio.subprocess
            mock_asyncio.run = _run_async
            mock_asyncio.create_task = asyncio.create_task
            mock_asyncio.gather = asyncio.gather
            mock_asyncio.wait_for = asyncio.wait_for

            with patch("shutil.which", return_value="/usr/bin/claude"):
                executor.execute("Test prompt")

            # Verify --model flag was NOT passed
            call_args = mock_asyncio.create_subprocess_exec.call_args
            args = call_args[0]  # positional args
            assert "--model" not in args


class TestAdditionalParsingCoverage:
    """Additional parsing tests for full coverage."""

    @pytest.fixture
    def executor(self) -> ClaudeCodeExecutor:
        """Create executor with default config."""
        config = LLMConfig(path="claude")
        return ClaudeCodeExecutor(config)

    def test_result_message_with_text(self, executor: ClaudeCodeExecutor) -> None:
        """Should extract text from result message."""
        import json

        raw_output = json.dumps(
            {
                "type": "result",
                "text": "Final result text",
                "usage": {"input_tokens": 10, "output_tokens": 20},
            }
        )
        parsed = executor._parse_output(raw_output)

        assert "Final result text" in parsed["content"]
        assert parsed["tokens_used"] == 30

    def test_content_block_delta_non_text_delta(
        self, executor: ClaudeCodeExecutor
    ) -> None:
        """Should handle content_block_delta with non-text delta type."""
        import json

        raw_output = json.dumps(
            {
                "type": "content_block_delta",
                "delta": {"type": "tool_use_delta", "data": "something"},
            }
        )
        parsed = executor._parse_output(raw_output)

        # No text should be extracted
        assert parsed["content"] == ""

    def test_message_delta_without_usage(self, executor: ClaudeCodeExecutor) -> None:
        """Should handle message_delta without usage field."""
        import json

        raw_output = json.dumps(
            {
                "type": "message_delta",
                # No usage field
            }
        )
        parsed = executor._parse_output(raw_output)

        # Tokens should remain 0
        assert parsed["tokens_used"] == 0

    def test_handles_non_dict_json(self, executor: ClaudeCodeExecutor) -> None:
        """Should handle valid JSON that is not a dict (e.g., number)."""
        raw_output = "4"  # Valid JSON, but just a number
        parsed = executor._parse_output(raw_output)

        # Should be treated as content
        assert "4" in parsed["content"]
        assert parsed["tool_calls"] == []
        assert parsed["tokens_used"] == 0

    def test_handles_json_array(self, executor: ClaudeCodeExecutor) -> None:
        """Should handle JSON arrays as content."""
        import json

        raw_output = json.dumps([1, 2, 3])
        parsed = executor._parse_output(raw_output)

        # Array should be converted to string content
        assert parsed["content"] != ""


class TestTimeoutResolution:
    """Tests for _resolve_timeout helper (Story 3-4)."""

    def test_timeout_parameter_takes_precedence(self) -> None:
        """Timeout parameter should override config.timeout_seconds."""
        config = LLMConfig(path="claude", timeout_seconds=300)
        executor = ClaudeCodeExecutor(config)

        # Parameter should override config
        result = executor._resolve_timeout(60)
        assert result == 60

    def test_config_timeout_used_when_no_parameter(self) -> None:
        """Config timeout_seconds should be used when no parameter provided."""
        config = LLMConfig(path="claude", timeout_seconds=180)
        executor = ClaudeCodeExecutor(config)

        result = executor._resolve_timeout(None)
        assert result == 180

    def test_default_timeout_used_when_config_is_zero(self) -> None:
        """DEFAULT_LLM_TIMEOUT should be used when config.timeout_seconds is 0."""
        from adw.executors.claude_code import DEFAULT_LLM_TIMEOUT

        config = LLMConfig(path="claude", timeout_seconds=0)
        executor = ClaudeCodeExecutor(config)

        result = executor._resolve_timeout(None)
        assert result == DEFAULT_LLM_TIMEOUT
        assert result == 600  # Verify the constant value

    def test_timeout_zero_parameter_uses_zero(self) -> None:
        """Timeout of 0 passed as parameter should be used (even if falsy)."""
        config = LLMConfig(path="claude", timeout_seconds=300)
        executor = ClaudeCodeExecutor(config)

        # When timeout=0 is explicitly passed, it should use 0
        # This is because 0 is not None
        result = executor._resolve_timeout(0)
        assert result == 0

    def test_default_llm_timeout_constant_value(self) -> None:
        """DEFAULT_LLM_TIMEOUT should be 600 seconds (10 minutes)."""
        from adw.executors.claude_code import DEFAULT_LLM_TIMEOUT

        assert DEFAULT_LLM_TIMEOUT == 600


class TestHookRunnerTimeoutResolution:
    """Tests for HookRunner._resolve_timeout helper (Story 3-4)."""

    def test_timeout_parameter_takes_precedence(self) -> None:
        """Timeout parameter should override config.timeout_seconds."""
        from adw.hooks.runner import HookRunner
        from adw.models import HookConfig

        config = HookConfig(timeout_seconds=60)
        runner = HookRunner(config)

        result = runner._resolve_timeout(30)
        assert result == 30

    def test_config_timeout_used_when_no_parameter(self) -> None:
        """Config timeout_seconds should be used when no parameter provided."""
        from adw.hooks.runner import HookRunner
        from adw.models import HookConfig

        config = HookConfig(timeout_seconds=45)
        runner = HookRunner(config)

        result = runner._resolve_timeout(None)
        assert result == 45

    def test_default_timeout_used_when_config_is_zero(self) -> None:
        """DEFAULT_HOOK_TIMEOUT should be used when config.timeout_seconds is 0."""
        from adw.hooks.runner import DEFAULT_HOOK_TIMEOUT, HookRunner
        from adw.models import HookConfig

        config = HookConfig(timeout_seconds=0)
        runner = HookRunner(config)

        result = runner._resolve_timeout(None)
        assert result == DEFAULT_HOOK_TIMEOUT
        assert result == 60  # Verify the constant value

    def test_default_hook_timeout_constant_value(self) -> None:
        """DEFAULT_HOOK_TIMEOUT should be 60 seconds (1 minute)."""
        from adw.hooks.runner import DEFAULT_HOOK_TIMEOUT

        assert DEFAULT_HOOK_TIMEOUT == 60


class TestDurationOnFailure:
    """Tests for duration_ms being set even on failure (Story 3-4 Task 6)."""

    @pytest.fixture
    def executor(self) -> ClaudeCodeExecutor:
        """Create executor with default config."""
        config = LLMConfig(path="claude")
        return ClaudeCodeExecutor(config)

    def test_duration_ms_set_on_subprocess_failure(
        self, executor: ClaudeCodeExecutor
    ) -> None:
        """duration_ms should be set even when subprocess returns non-zero exit."""
        with patch("adw.executors.claude_code.asyncio") as mock_asyncio:
            process = AsyncMock()
            process.stdout = AsyncMock()
            process.stderr = AsyncMock()
            process.stdout.readline = AsyncMock(side_effect=[b"partial output\n", b""])
            process.stderr.readline = AsyncMock(
                side_effect=[b"Error: something failed\n", b""]
            )
            process.wait = AsyncMock(return_value=None)
            process.returncode = 1  # Non-zero exit code

            mock_asyncio.create_subprocess_exec = AsyncMock(return_value=process)
            mock_asyncio.subprocess = asyncio.subprocess
            mock_asyncio.run = _run_async
            mock_asyncio.create_task = asyncio.create_task
            mock_asyncio.gather = asyncio.gather
            mock_asyncio.wait_for = asyncio.wait_for

            with patch("shutil.which", return_value="/usr/bin/claude"):
                result = executor.execute("Test prompt")

            # Even on failure, duration_ms should be set
            assert result.success is False
            assert result.duration_ms >= 0
            assert result.error is not None


class TestExceptionCleanup:
    """Tests for exception handling and process cleanup (Story 3-4 H2)."""

    @pytest.fixture
    def executor(self) -> ClaudeCodeExecutor:
        """Create executor with default config."""
        config = LLMConfig(path="claude")
        return ClaudeCodeExecutor(config)

    def test_process_killed_on_general_exception(
        self, executor: ClaudeCodeExecutor
    ) -> None:
        """Process should be killed when a general exception occurs during streaming."""
        with patch("adw.executors.claude_code.asyncio") as mock_asyncio:
            process = AsyncMock()
            process.stdout = AsyncMock()
            process.stderr = AsyncMock()
            process.returncode = None  # Process still running
            process.kill = MagicMock()
            process.wait = AsyncMock(return_value=None)

            # Simulate an exception during stdout reading
            async def raise_exception():
                raise RuntimeError("Simulated stream error")

            process.stdout.readline = raise_exception
            process.stderr.readline = AsyncMock(side_effect=[b""])

            mock_asyncio.create_subprocess_exec = AsyncMock(return_value=process)
            mock_asyncio.subprocess = asyncio.subprocess
            mock_asyncio.run = _run_async
            mock_asyncio.create_task = asyncio.create_task
            mock_asyncio.gather = asyncio.gather
            mock_asyncio.wait_for = asyncio.wait_for

            with (
                patch("shutil.which", return_value="/usr/bin/claude"),
                pytest.raises(RuntimeError, match="Simulated stream error"),
            ):
                executor.execute("Test prompt")

            # Verify process was killed and waited for cleanup
            process.kill.assert_called_once()
            process.wait.assert_awaited()

    def test_no_kill_when_process_already_exited(
        self, executor: ClaudeCodeExecutor
    ) -> None:
        """Process should not be killed if it already exited (returncode is set)."""
        with patch("adw.executors.claude_code.asyncio") as mock_asyncio:
            process = AsyncMock()
            process.stdout = AsyncMock()
            process.stderr = AsyncMock()
            process.returncode = 0  # Process already exited
            process.kill = MagicMock()
            process.wait = AsyncMock(return_value=None)

            # Simulate an exception after process already exited
            call_count = 0

            async def raise_after_exit():
                nonlocal call_count
                call_count += 1
                if call_count == 1:
                    return b"output\n"
                raise RuntimeError("Late error")

            process.stdout.readline = raise_after_exit
            process.stderr.readline = AsyncMock(side_effect=[b""])

            mock_asyncio.create_subprocess_exec = AsyncMock(return_value=process)
            mock_asyncio.subprocess = asyncio.subprocess
            mock_asyncio.run = _run_async
            mock_asyncio.create_task = asyncio.create_task
            mock_asyncio.gather = asyncio.gather
            mock_asyncio.wait_for = asyncio.wait_for

            with (
                patch("shutil.which", return_value="/usr/bin/claude"),
                pytest.raises(RuntimeError, match="Late error"),
            ):
                executor.execute("Test prompt")

            # Since returncode is set, kill should NOT be called
            process.kill.assert_not_called()


class TestStreamLoggerIntegration:
    """Tests for StreamLogger integration with ClaudeCodeExecutor (Story 7.3 Task 4)."""

    @pytest.fixture
    def executor(self) -> ClaudeCodeExecutor:
        """Create executor with default config."""
        config = LLMConfig(path="claude")
        return ClaudeCodeExecutor(config)

    def test_execute_accepts_stream_logger_parameter(
        self, executor: ClaudeCodeExecutor
    ) -> None:
        """execute() should accept an optional stream_logger parameter."""
        from adw.logging.stream import StreamLogger

        stream_logger = StreamLogger()

        with patch("adw.executors.claude_code.asyncio") as mock_asyncio:
            process = AsyncMock()
            process.stdout = AsyncMock()
            process.stderr = AsyncMock()
            process.stdout.readline = AsyncMock(side_effect=[b"Output\n", b""])
            process.stderr.readline = AsyncMock(side_effect=[b""])
            process.wait = AsyncMock(return_value=None)
            process.returncode = 0

            mock_asyncio.create_subprocess_exec = AsyncMock(return_value=process)
            mock_asyncio.subprocess = asyncio.subprocess
            mock_asyncio.run = _run_async
            mock_asyncio.create_task = asyncio.create_task
            mock_asyncio.gather = asyncio.gather
            mock_asyncio.wait_for = asyncio.wait_for

            with patch("shutil.which", return_value="/usr/bin/claude"):
                # Should not raise - stream_logger is a valid parameter
                result = executor.execute("Test prompt", stream_logger=stream_logger)

            assert isinstance(result, LLMResult)

    def test_stream_logger_captures_tokens(
        self, executor: ClaudeCodeExecutor
    ) -> None:
        """StreamLogger should capture tokens when provided."""
        from adw.logging.stream import StreamLogger
        from adw.models.logging import StreamEventType

        stream_logger = StreamLogger()

        with patch("adw.executors.claude_code.asyncio") as mock_asyncio:
            process = AsyncMock()
            process.stdout = AsyncMock()
            process.stderr = AsyncMock()
            process.stdout.readline = AsyncMock(
                side_effect=[
                    b"Hello ",
                    b"World!\n",
                    b"",  # EOF
                ]
            )
            process.stderr.readline = AsyncMock(side_effect=[b""])
            process.wait = AsyncMock(return_value=None)
            process.returncode = 0

            mock_asyncio.create_subprocess_exec = AsyncMock(return_value=process)
            mock_asyncio.subprocess = asyncio.subprocess
            mock_asyncio.run = _run_async
            mock_asyncio.create_task = asyncio.create_task
            mock_asyncio.gather = asyncio.gather
            mock_asyncio.wait_for = asyncio.wait_for

            with patch("shutil.which", return_value="/usr/bin/claude"):
                executor.execute("Test prompt", stream_logger=stream_logger)

            events = stream_logger.get_events()
            # Should have captured token events
            assert len(events) >= 1
            token_events = [e for e in events if e.type == StreamEventType.TOKEN]
            assert len(token_events) >= 1

    def test_stream_logger_none_by_default(
        self, executor: ClaudeCodeExecutor
    ) -> None:
        """stream_logger should be None by default (no capturing)."""
        with patch("adw.executors.claude_code.asyncio") as mock_asyncio:
            process = AsyncMock()
            process.stdout = AsyncMock()
            process.stderr = AsyncMock()
            process.stdout.readline = AsyncMock(side_effect=[b"Output\n", b""])
            process.stderr.readline = AsyncMock(side_effect=[b""])
            process.wait = AsyncMock(return_value=None)
            process.returncode = 0

            mock_asyncio.create_subprocess_exec = AsyncMock(return_value=process)
            mock_asyncio.subprocess = asyncio.subprocess
            mock_asyncio.run = _run_async
            mock_asyncio.create_task = asyncio.create_task
            mock_asyncio.gather = asyncio.gather
            mock_asyncio.wait_for = asyncio.wait_for

            with patch("shutil.which", return_value="/usr/bin/claude"):
                # Should work without stream_logger
                result = executor.execute("Test prompt")

            assert isinstance(result, LLMResult)

    def test_stream_logger_captures_complete_event(
        self, executor: ClaudeCodeExecutor
    ) -> None:
        """StreamLogger should capture completion event with stats."""
        import json

        from adw.logging.stream import StreamLogger
        from adw.models.logging import StreamEventType

        stream_logger = StreamLogger()

        with patch("adw.executors.claude_code.asyncio") as mock_asyncio:
            process = AsyncMock()
            process.stdout = AsyncMock()
            process.stderr = AsyncMock()
            # Return JSONL with token usage
            result_json = json.dumps(
                {
                    "type": "result",
                    "usage": {"input_tokens": 100, "output_tokens": 50},
                }
            )
            process.stdout.readline = AsyncMock(
                side_effect=[result_json.encode() + b"\n", b""]
            )
            process.stderr.readline = AsyncMock(side_effect=[b""])
            process.wait = AsyncMock(return_value=None)
            process.returncode = 0

            mock_asyncio.create_subprocess_exec = AsyncMock(return_value=process)
            mock_asyncio.subprocess = asyncio.subprocess
            mock_asyncio.run = _run_async
            mock_asyncio.create_task = asyncio.create_task
            mock_asyncio.gather = asyncio.gather
            mock_asyncio.wait_for = asyncio.wait_for

            with patch("shutil.which", return_value="/usr/bin/claude"):
                executor.execute("Test prompt", stream_logger=stream_logger)

            events = stream_logger.get_events()
            complete_events = [e for e in events if e.type == StreamEventType.COMPLETE]
            assert len(complete_events) == 1
            assert complete_events[0].stats is not None

    def test_stream_logger_captures_error_on_failure(
        self, executor: ClaudeCodeExecutor
    ) -> None:
        """StreamLogger should capture error event on failure."""
        from adw.logging.stream import StreamLogger
        from adw.models.logging import StreamEventType

        stream_logger = StreamLogger()

        with patch("adw.executors.claude_code.asyncio") as mock_asyncio:
            process = AsyncMock()
            process.stdout = AsyncMock()
            process.stderr = AsyncMock()
            process.stdout.readline = AsyncMock(side_effect=[b""])
            process.stderr.readline = AsyncMock(
                side_effect=[b"Error: Something went wrong\n", b""]
            )
            process.wait = AsyncMock(return_value=None)
            process.returncode = 1  # Failure

            mock_asyncio.create_subprocess_exec = AsyncMock(return_value=process)
            mock_asyncio.subprocess = asyncio.subprocess
            mock_asyncio.run = _run_async
            mock_asyncio.create_task = asyncio.create_task
            mock_asyncio.gather = asyncio.gather
            mock_asyncio.wait_for = asyncio.wait_for

            with patch("shutil.which", return_value="/usr/bin/claude"):
                result = executor.execute("Test prompt", stream_logger=stream_logger)

            assert result.success is False
            events = stream_logger.get_events()
            error_events = [e for e in events if e.type == StreamEventType.ERROR]
            assert len(error_events) == 1
            assert "Something went wrong" in (error_events[0].error or "")


class TestShowLLMOutputFlag:
    """Tests for show_llm_output flag (Story UX-FIX-ISS-001).

    By default, LLM streaming output should NOT be printed to the terminal.
    Users can enable it with --show-llm-output or --trace verbosity.
    """

    @pytest.fixture
    def executor_with_show_output(self) -> ClaudeCodeExecutor:
        """Create executor with show_llm_output=True."""
        config = LLMConfig(path="claude")
        return ClaudeCodeExecutor(config, show_llm_output=True)

    @pytest.fixture
    def executor_without_show_output(self) -> ClaudeCodeExecutor:
        """Create executor with show_llm_output=False (default)."""
        config = LLMConfig(path="claude")
        return ClaudeCodeExecutor(config, show_llm_output=False)

    def test_show_llm_output_defaults_to_false(self) -> None:
        """show_llm_output should default to False."""
        config = LLMConfig(path="claude")
        executor = ClaudeCodeExecutor(config)
        assert executor.show_llm_output is False

    def test_console_print_not_called_when_show_llm_output_false(
        self, executor_without_show_output: ClaudeCodeExecutor
    ) -> None:
        """Console.print should NOT be called when show_llm_output=False."""
        import json

        from rich.console import Console

        mock_console = MagicMock(spec=Console)
        executor_without_show_output.console = mock_console

        # Use valid stream-json format with content_block_delta
        stream_json = json.dumps({
            "type": "content_block_delta",
            "delta": {"type": "text_delta", "text": "Hello world"}
        })

        with patch("adw.executors.claude_code.asyncio") as mock_asyncio:
            process = AsyncMock()
            process.stdout = AsyncMock()
            process.stderr = AsyncMock()
            process.stdout.readline = AsyncMock(
                side_effect=[
                    (stream_json + "\n").encode(),
                    b"",  # EOF
                ]
            )
            process.stderr.readline = AsyncMock(side_effect=[b""])
            process.wait = AsyncMock(return_value=None)
            process.returncode = 0

            mock_asyncio.create_subprocess_exec = AsyncMock(return_value=process)
            mock_asyncio.subprocess = asyncio.subprocess
            mock_asyncio.run = _run_async
            mock_asyncio.create_task = asyncio.create_task
            mock_asyncio.gather = asyncio.gather
            mock_asyncio.wait_for = asyncio.wait_for

            with patch("shutil.which", return_value="/usr/bin/claude"):
                result = executor_without_show_output.execute("Test prompt")

            # Content should still be captured
            assert "Hello world" in result.content
            # But console.print should NOT have been called
            mock_console.print.assert_not_called()

    def test_console_print_called_when_show_llm_output_true(
        self, executor_with_show_output: ClaudeCodeExecutor
    ) -> None:
        """Console.print should be called when show_llm_output=True."""
        import json

        from rich.console import Console

        mock_console = MagicMock(spec=Console)
        executor_with_show_output.console = mock_console

        # Use valid stream-json format with content_block_delta
        stream_json = json.dumps({
            "type": "content_block_delta",
            "delta": {"type": "text_delta", "text": "Hello world"}
        })

        with patch("adw.executors.claude_code.asyncio") as mock_asyncio:
            process = AsyncMock()
            process.stdout = AsyncMock()
            process.stderr = AsyncMock()
            process.stdout.readline = AsyncMock(
                side_effect=[
                    (stream_json + "\n").encode(),
                    b"",  # EOF
                ]
            )
            process.stderr.readline = AsyncMock(side_effect=[b""])
            process.wait = AsyncMock(return_value=None)
            process.returncode = 0

            mock_asyncio.create_subprocess_exec = AsyncMock(return_value=process)
            mock_asyncio.subprocess = asyncio.subprocess
            mock_asyncio.run = _run_async
            mock_asyncio.create_task = asyncio.create_task
            mock_asyncio.gather = asyncio.gather
            mock_asyncio.wait_for = asyncio.wait_for

            with patch("shutil.which", return_value="/usr/bin/claude"):
                result = executor_with_show_output.execute("Test prompt")

            # Content should be captured
            assert "Hello world" in result.content
            # Console.print SHOULD have been called
            mock_console.print.assert_called()

    def test_stream_logger_still_captures_when_console_suppressed(
        self, executor_without_show_output: ClaudeCodeExecutor
    ) -> None:
        """StreamLogger should still capture tokens even when console is suppressed."""
        from adw.logging.stream import StreamLogger
        from adw.models.logging import StreamEventType

        stream_logger = StreamLogger()

        with patch("adw.executors.claude_code.asyncio") as mock_asyncio:
            process = AsyncMock()
            process.stdout = AsyncMock()
            process.stderr = AsyncMock()
            process.stdout.readline = AsyncMock(
                side_effect=[
                    b"Hello ",
                    b"World!\n",
                    b"",  # EOF
                ]
            )
            process.stderr.readline = AsyncMock(side_effect=[b""])
            process.wait = AsyncMock(return_value=None)
            process.returncode = 0

            mock_asyncio.create_subprocess_exec = AsyncMock(return_value=process)
            mock_asyncio.subprocess = asyncio.subprocess
            mock_asyncio.run = _run_async
            mock_asyncio.create_task = asyncio.create_task
            mock_asyncio.gather = asyncio.gather
            mock_asyncio.wait_for = asyncio.wait_for

            with patch("shutil.which", return_value="/usr/bin/claude"):
                executor_without_show_output.execute(
                    "Test prompt", stream_logger=stream_logger
                )

            events = stream_logger.get_events()
            # Should have captured token events even though console is suppressed
            token_events = [e for e in events if e.type == StreamEventType.TOKEN]
            assert len(token_events) >= 1


class TestToolLogging:
    """Tests for tool call logging integration (Story 3.8)."""

    @pytest.fixture
    def executor(self) -> ClaudeCodeExecutor:
        """Create executor with default config."""
        config = LLMConfig(path="claude")
        return ClaudeCodeExecutor(config)

    def test_accepts_optional_tool_logger(self, tmp_path) -> None:
        """Executor should accept optional tool_logger parameter."""
        from adw.security.tool_logger import ToolLogger

        run_dir = tmp_path / "runs" / "test-run"
        run_dir.mkdir(parents=True)
        tool_logger = ToolLogger(run_dir)

        config = LLMConfig(path="claude")
        executor = ClaudeCodeExecutor(config, tool_logger=tool_logger)

        assert executor.tool_logger is tool_logger

    def test_tool_logger_defaults_to_none(self, executor: ClaudeCodeExecutor) -> None:
        """Tool logger should default to None."""
        assert executor.tool_logger is None

    def test_logs_tool_calls_when_logger_provided(self, tmp_path) -> None:
        """Should log tool calls when tool_logger is configured."""
        import json

        from adw.security.tool_logger import ToolLogger

        run_dir = tmp_path / "runs" / "test-run"
        run_dir.mkdir(parents=True)
        tool_logger = ToolLogger(run_dir)

        config = LLMConfig(path="claude")
        executor = ClaudeCodeExecutor(config, tool_logger=tool_logger)

        # Mock subprocess with tool use output
        tool_use_output = json.dumps(
            {
                "type": "assistant",
                "message": {
                    "content": [
                        {"type": "text", "text": "Let me read that file."},
                        {
                            "type": "tool_use",
                            "name": "Read",
                            "input": {"file_path": "/src/main.py"},
                        },
                    ]
                },
            }
        )

        with patch("adw.executors.claude_code.asyncio") as mock_asyncio:
            process = AsyncMock()
            process.stdout = AsyncMock()
            process.stderr = AsyncMock()
            process.stdout.readline = AsyncMock(
                side_effect=[tool_use_output.encode() + b"\n", b""]
            )
            process.stderr.readline = AsyncMock(side_effect=[b""])
            process.wait = AsyncMock(return_value=None)
            process.returncode = 0

            mock_asyncio.create_subprocess_exec = AsyncMock(return_value=process)
            mock_asyncio.subprocess = asyncio.subprocess
            mock_asyncio.run = _run_async
            mock_asyncio.create_task = asyncio.create_task
            mock_asyncio.gather = asyncio.gather
            mock_asyncio.wait_for = asyncio.wait_for

            with patch("shutil.which", return_value="/usr/bin/claude"):
                result = executor.execute("Test prompt")

        # Verify tool call was captured in result
        assert len(result.tool_calls) == 1
        assert result.tool_calls[0].tool_name == "Read"

        # Verify tool call was logged
        history = tool_logger.get_tool_history()
        assert len(history) == 1
        assert history[0].tool_name == "Read"
        assert history[0].arguments == {"file_path": "/src/main.py"}

    def test_logs_multiple_tool_calls(self, tmp_path) -> None:
        """Should log all tool calls from execution."""
        import json

        from adw.security.tool_logger import ToolLogger

        run_dir = tmp_path / "runs" / "test-run"
        run_dir.mkdir(parents=True)
        tool_logger = ToolLogger(run_dir)

        config = LLMConfig(path="claude")
        executor = ClaudeCodeExecutor(config, tool_logger=tool_logger)

        # Mock subprocess with multiple tool uses
        output_lines = [
            json.dumps(
                {
                    "type": "assistant",
                    "message": {
                        "content": [
                            {
                                "type": "tool_use",
                                "name": "Read",
                                "input": {"file_path": "/file1.py"},
                            },
                        ]
                    },
                }
            ),
            json.dumps(
                {
                    "type": "assistant",
                    "message": {
                        "content": [
                            {
                                "type": "tool_use",
                                "name": "Write",
                                "input": {"file_path": "/file2.py", "content": "test"},
                            },
                        ]
                    },
                }
            ),
            json.dumps(
                {
                    "type": "assistant",
                    "message": {
                        "content": [
                            {
                                "type": "tool_use",
                                "name": "Bash",
                                "input": {"command": "npm test"},
                            },
                        ]
                    },
                }
            ),
        ]

        with patch("adw.executors.claude_code.asyncio") as mock_asyncio:
            process = AsyncMock()
            process.stdout = AsyncMock()
            process.stderr = AsyncMock()
            process.stdout.readline = AsyncMock(
                side_effect=[line.encode() + b"\n" for line in output_lines] + [b""]
            )
            process.stderr.readline = AsyncMock(side_effect=[b""])
            process.wait = AsyncMock(return_value=None)
            process.returncode = 0

            mock_asyncio.create_subprocess_exec = AsyncMock(return_value=process)
            mock_asyncio.subprocess = asyncio.subprocess
            mock_asyncio.run = _run_async
            mock_asyncio.create_task = asyncio.create_task
            mock_asyncio.gather = asyncio.gather
            mock_asyncio.wait_for = asyncio.wait_for

            with patch("shutil.which", return_value="/usr/bin/claude"):
                executor.execute("Test prompt")

        # Verify all tool calls were logged
        history = tool_logger.get_tool_history()
        assert len(history) == 3
        assert history[0].tool_name == "Read"
        assert history[1].tool_name == "Write"
        assert history[2].tool_name == "Bash"

    def test_no_logging_when_logger_not_provided(
        self, executor: ClaudeCodeExecutor
    ) -> None:
        """Should not fail when no tool_logger is configured."""
        import json

        # Mock subprocess with tool use output
        tool_use_output = json.dumps(
            {
                "type": "assistant",
                "message": {
                    "content": [
                        {
                            "type": "tool_use",
                            "name": "Read",
                            "input": {"file_path": "/src/main.py"},
                        },
                    ]
                },
            }
        )

        with patch("adw.executors.claude_code.asyncio") as mock_asyncio:
            process = AsyncMock()
            process.stdout = AsyncMock()
            process.stderr = AsyncMock()
            process.stdout.readline = AsyncMock(
                side_effect=[tool_use_output.encode() + b"\n", b""]
            )
            process.stderr.readline = AsyncMock(side_effect=[b""])
            process.wait = AsyncMock(return_value=None)
            process.returncode = 0

            mock_asyncio.create_subprocess_exec = AsyncMock(return_value=process)
            mock_asyncio.subprocess = asyncio.subprocess
            mock_asyncio.run = _run_async
            mock_asyncio.create_task = asyncio.create_task
            mock_asyncio.gather = asyncio.gather
            mock_asyncio.wait_for = asyncio.wait_for

            with patch("shutil.which", return_value="/usr/bin/claude"):
                result = executor.execute("Test prompt")

        # Should still capture tool calls in result
        assert len(result.tool_calls) == 1
        assert executor.tool_logger is None
