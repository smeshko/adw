"""Unit tests for ClaudeCodeExecutor.

These tests validate the ClaudeCodeExecutor implementation against
the LLMExecutor Protocol, using mocked subprocess execution.
"""

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from adw.executors.base import LLMExecutor
from adw.executors.claude_code import ClaudeCodeExecutor
from adw.models.config import LLMConfig
from adw.models.llm import LLMResult


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
            process.stderr.read = AsyncMock(return_value=b"")
            process.wait = AsyncMock(return_value=None)
            process.returncode = 0

            # Mock create_subprocess_exec to return our process
            mock_asyncio.create_subprocess_exec = AsyncMock(return_value=process)
            mock_asyncio.subprocess = asyncio.subprocess

            # Make asyncio.run actually run the coroutine
            mock_asyncio.run = lambda coro: asyncio.get_event_loop().run_until_complete(
                coro
            )

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
        process.stderr.read = AsyncMock(return_value=b"Error occurred")

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
            process.stdout.readline = AsyncMock(side_effect=[b"", ])
            process.stderr.read = AsyncMock(return_value=b"")
            process.wait = AsyncMock(return_value=None)
            process.returncode = 0

            mock_asyncio.create_subprocess_exec = AsyncMock(return_value=process)
            mock_asyncio.subprocess = asyncio.subprocess
            mock_asyncio.run = asyncio.run

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
            process.stdout.readline = AsyncMock(side_effect=[b"", ])
            process.stderr.read = AsyncMock(return_value=b"")
            process.wait = AsyncMock(return_value=None)
            process.returncode = 0

            mock_asyncio.create_subprocess_exec = AsyncMock(return_value=process)
            mock_asyncio.subprocess = asyncio.subprocess
            mock_asyncio.run = asyncio.run

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
            process.stdout.readline = AsyncMock(side_effect=[b"", ])
            process.stderr.read = AsyncMock(return_value=b"")
            process.wait = AsyncMock(return_value=None)
            process.returncode = 0

            mock_asyncio.create_subprocess_exec = AsyncMock(return_value=process)
            mock_asyncio.subprocess = asyncio.subprocess
            mock_asyncio.run = asyncio.run

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
            process.stdout.readline = AsyncMock(side_effect=[b"", ])
            process.stderr.read = AsyncMock(return_value=b"")
            process.wait = AsyncMock(return_value=None)
            process.returncode = 0

            mock_asyncio.create_subprocess_exec = AsyncMock(return_value=process)
            mock_asyncio.subprocess = asyncio.subprocess
            mock_asyncio.run = asyncio.run

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
            process.stdout.readline = AsyncMock(side_effect=[b"", ])
            process.stderr.read = AsyncMock(return_value=b"")
            process.wait = AsyncMock(return_value=None)
            process.returncode = 0

            mock_asyncio.create_subprocess_exec = AsyncMock(return_value=process)
            mock_asyncio.subprocess = asyncio.subprocess

            # Track if asyncio.run was called
            run_called = False
            original_run = asyncio.run

            def track_run(coro):
                nonlocal run_called
                run_called = True
                return original_run(coro)

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
            process.stderr.read = AsyncMock(return_value=b"")
            process.wait = AsyncMock(return_value=None)
            process.returncode = 0

            mock_asyncio.create_subprocess_exec = AsyncMock(return_value=process)
            mock_asyncio.subprocess = asyncio.subprocess
            mock_asyncio.run = asyncio.run

            with patch("shutil.which", return_value="/usr/bin/claude"):
                result = executor.execute("Test prompt")

            # Verify readline was called multiple times
            assert process.stdout.readline.call_count >= 4
            # Verify content includes all lines
            assert "First line" in result.content
            assert "Second line" in result.content
            assert "Third line" in result.content

    def test_forwards_output_to_rich_console(
        self, executor: ClaudeCodeExecutor
    ) -> None:
        """Should forward output to Rich console in real-time."""
        from rich.console import Console
        from unittest.mock import MagicMock

        mock_console = MagicMock(spec=Console)
        executor.console = mock_console

        with patch("adw.executors.claude_code.asyncio") as mock_asyncio:
            process = AsyncMock()
            process.stdout = AsyncMock()
            process.stderr = AsyncMock()
            process.stdout.readline = AsyncMock(
                side_effect=[
                    b"Output line\n",
                    b"",  # EOF
                ]
            )
            process.stderr.read = AsyncMock(return_value=b"")
            process.wait = AsyncMock(return_value=None)
            process.returncode = 0

            mock_asyncio.create_subprocess_exec = AsyncMock(return_value=process)
            mock_asyncio.subprocess = asyncio.subprocess
            mock_asyncio.run = asyncio.run

            with patch("shutil.which", return_value="/usr/bin/claude"):
                executor.execute("Test prompt")

            # Verify console.print was called with output
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
            process.stderr.read = AsyncMock(return_value=b"")
            process.wait = AsyncMock(return_value=None)
            process.returncode = 0

            mock_asyncio.create_subprocess_exec = AsyncMock(return_value=process)
            mock_asyncio.subprocess = asyncio.subprocess
            mock_asyncio.run = asyncio.run

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
