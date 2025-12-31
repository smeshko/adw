"""Claude Code CLI Executor.

This module provides the ClaudeCodeExecutor that implements the LLMExecutor
protocol by invoking the Claude Code CLI as a subprocess with real-time
streaming output.
"""

import asyncio
import shutil
import time
from pathlib import Path

from rich.console import Console

from adw.exceptions import LLMError
from adw.models.config import LLMConfig
from adw.models.llm import LLMResult


class ClaudeCodeExecutor:
    """LLM Executor using Claude Code CLI.

    Executes prompts by spawning the Claude Code CLI as a subprocess,
    streaming output in real-time, and returning structured results.

    Implements the LLMExecutor Protocol for interchangeability with
    MockExecutor in tests.

    Example:
        >>> config = LLMConfig(path="claude", timeout_seconds=300)
        >>> executor = ClaudeCodeExecutor(config)
        >>> result = executor.execute("Generate a hello world program")
        >>> print(result.content)
    """

    def __init__(
        self,
        config: LLMConfig,
        *,
        console: Console | None = None,
    ) -> None:
        """Initialize the ClaudeCodeExecutor.

        Args:
            config: LLM configuration containing path, timeout, and other settings.
            console: Optional Rich console for streaming output. If not provided,
                     a new Console instance is created.
        """
        self.config = config
        self.console = console or Console()

    def execute(
        self,
        prompt: str,
        *,
        timeout: int | None = None,
    ) -> LLMResult:
        """Execute a prompt using Claude Code CLI.

        Spawns Claude Code as a subprocess, streams output in real-time,
        and returns a structured result.

        Args:
            prompt: The prompt to send to Claude Code.
            timeout: Optional timeout in seconds. If None, uses config default.

        Returns:
            LLMResult with success status, content, tool calls, and metrics.

        Raises:
            LLMError: If Claude Code is not found or execution fails.
        """
        effective_timeout = (
            timeout if timeout is not None else self.config.timeout_seconds
        )
        return asyncio.run(self._stream_subprocess(prompt, effective_timeout))

    async def _stream_subprocess(
        self,
        prompt: str,
        timeout: int,
    ) -> LLMResult:
        """Execute Claude Code subprocess with streaming output.

        Args:
            prompt: The prompt to send to Claude Code.
            timeout: Timeout in seconds.

        Returns:
            LLMResult with execution results.
        """
        start_time = time.monotonic()

        # Verify Claude path exists
        claude_path = self._verify_claude_path()

        # Build command arguments
        args = [str(claude_path), "--print", prompt]

        # Add model if configured
        if self.config.model:
            args.extend(["--model", self.config.model])

        # Create subprocess
        process = await asyncio.create_subprocess_exec(
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        # Stream stdout in real-time
        content_lines: list[str] = []
        while True:
            line = await process.stdout.readline()
            if not line:
                break
            decoded = line.decode()
            content_lines.append(decoded)
            # Stream to console in real-time
            self.console.print(decoded, end="")

        # Wait for process to complete
        await process.wait()

        # Read any stderr
        stderr_bytes = await process.stderr.read()
        stderr = stderr_bytes.decode() if stderr_bytes else ""

        duration_ms = int((time.monotonic() - start_time) * 1000)
        content = "".join(content_lines)

        # Build result
        if process.returncode == 0:
            return LLMResult(
                success=True,
                content=content,
                tool_calls=[],
                tokens_used=0,  # Will be parsed from output in Task 4
                duration_ms=duration_ms,
            )
        else:
            return LLMResult(
                success=False,
                content=content,
                tool_calls=[],
                tokens_used=0,
                duration_ms=duration_ms,
                error=stderr or f"Claude Code exited with code {process.returncode}",
            )

    def _verify_claude_path(self) -> Path:
        """Verify Claude Code executable exists.

        Returns:
            Path to the Claude executable.

        Raises:
            LLMError: If Claude Code is not found.
        """
        path = self.config.path

        # Check if it's an absolute path
        if Path(path).is_absolute():
            if Path(path).exists():
                return Path(path)
            raise LLMError(
                code="CLAUDE_NOT_FOUND",
                message=f"Claude Code CLI not found at '{path}'",
                suggestion=(
                    "Install Claude Code or configure llm.claude_code.path in adw.yaml"
                ),
                recoverable=False,
            )

        # Check if it's in PATH
        which_result = shutil.which(path)
        if which_result:
            return Path(which_result)

        raise LLMError(
            code="CLAUDE_NOT_FOUND",
            message=f"Claude Code CLI '{path}' not found in PATH",
            suggestion=(
                "Install Claude Code or configure llm.claude_code.path in adw.yaml"
            ),
            recoverable=False,
        )
