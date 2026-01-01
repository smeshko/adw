"""Claude Code CLI Executor.

This module provides the ClaudeCodeExecutor that implements the LLMExecutor
protocol by invoking the Claude Code CLI as a subprocess with real-time
streaming output.

Timeout Hierarchy:
    1. timeout parameter passed to execute() - highest priority
    2. config.timeout_seconds from LLMConfig
    3. DEFAULT_LLM_TIMEOUT constant - fallback default
"""

import asyncio
import json
import logging
import shutil
import time
from pathlib import Path
from typing import Any

from rich.console import Console

from adw.exceptions import LLMError, LLMTimeoutError
from adw.models.config import LLMConfig
from adw.models.llm import LLMResult, ToolCall

logger = logging.getLogger(__name__)

# Default timeout for LLM execution in seconds (10 minutes)
DEFAULT_LLM_TIMEOUT = 600


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

    def _resolve_timeout(self, timeout: int | None) -> int:
        """Resolve timeout using 3-tier hierarchy.

        Resolution order:
            1. Explicit timeout parameter - highest priority
            2. config.timeout_seconds from LLMConfig
            3. DEFAULT_LLM_TIMEOUT constant - fallback default

        Args:
            timeout: Optional timeout override in seconds.

        Returns:
            Resolved timeout in seconds.
        """
        if timeout is not None:
            return timeout
        if self.config.timeout_seconds:
            return self.config.timeout_seconds
        return DEFAULT_LLM_TIMEOUT

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
            LLMError: If Claude Code is not found, execution fails, or timeout.
        """
        effective_timeout = self._resolve_timeout(timeout)
        return asyncio.run(self._stream_subprocess(prompt, effective_timeout))

    async def _stream_subprocess(
        self,
        prompt: str,
        timeout: int,
    ) -> LLMResult:
        """Execute Claude Code subprocess with streaming output.

        Uses concurrent tasks for stdout/stderr to prevent deadlocks,
        and enforces timeout on the entire operation.

        Args:
            prompt: The prompt to send to Claude Code.
            timeout: Timeout in seconds.

        Returns:
            LLMResult with execution results.

        Raises:
            LLMError: If timeout is exceeded.
        """
        start_time = time.monotonic()

        # Verify Claude path exists
        claude_path = self._verify_claude_path()

        # Build command arguments
        args = [str(claude_path), "--print", prompt]

        # Add model if configured
        if self.config.model:
            args.extend(["--model", self.config.model])

        logger.debug(
            "Executing Claude Code",
            extra={
                "path": str(claude_path),
                "model": self.config.model,
                "timeout": timeout,
                "prompt_length": len(prompt),
            },
        )

        # Create subprocess
        process = await asyncio.create_subprocess_exec(
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        try:
            # Use concurrent tasks to read stdout and stderr to prevent deadlocks
            result = await asyncio.wait_for(
                self._read_process_output(process),
                timeout=timeout,
            )
            return self._build_result(result, start_time)

        except TimeoutError:
            # Calculate elapsed time before cleanup
            elapsed_seconds = int(time.monotonic() - start_time)

            # Capture partial output before killing process
            partial_output = await self._capture_partial_output(process)

            # Terminate the process gracefully first
            process.kill()
            await process.wait()

            # Log timeout event with context including partial output
            logger.warning(
                "Claude Code execution timed out",
                extra={
                    "timeout": timeout,
                    "elapsed_seconds": elapsed_seconds,
                    "prompt_length": len(prompt),
                    "partial_output_length": len(partial_output),
                },
            )

            raise LLMTimeoutError(
                code="LLM_TIMEOUT",
                message=(
                    f"LLM execution timed out after {elapsed_seconds}s "
                    f"(limit: {timeout}s)"
                ),
                timeout_seconds=timeout,
                elapsed_seconds=elapsed_seconds,
                suggestion="Consider increasing timeout or simplifying prompt",
            ) from None

        except Exception as e:
            # Cleanup process on any error
            logger.error(
                "Claude Code execution failed",
                extra={"error": str(e), "prompt_length": len(prompt)},
            )
            if process.returncode is None:
                # Kill the process immediately for error cleanup
                process.kill()
                await process.wait()
            raise

    async def _capture_partial_output(
        self,
        process: asyncio.subprocess.Process,
    ) -> str:
        """Capture any buffered output from process before killing.

        Attempts to read any remaining data from stdout that was buffered
        but not yet consumed before the timeout. This helps with debugging
        by preserving partial progress.

        Args:
            process: The subprocess to read from.

        Returns:
            String containing any partial output captured, empty if none.
        """
        partial_content: list[str] = []

        if process.stdout is None:
            return ""

        try:
            # Try to read any buffered data with a very short timeout
            while True:
                try:
                    line = await asyncio.wait_for(
                        process.stdout.readline(),
                        timeout=0.1,  # Very short timeout to drain buffer
                    )
                    if not line:
                        break
                    partial_content.append(line.decode("utf-8", errors="replace"))
                except TimeoutError:
                    # No more data available in buffer
                    break
        except Exception:
            # Ignore errors during partial capture - this is best-effort
            pass

        return "".join(partial_content)

    async def _read_process_output(
        self,
        process: asyncio.subprocess.Process,
    ) -> dict[str, Any]:
        """Read stdout and stderr concurrently to prevent deadlocks.

        Uses asyncio.create_task() for concurrent processing as required
        by NFR3 (artifact writes don't block stream).

        Args:
            process: The subprocess to read from.

        Returns:
            Dictionary with stdout_lines, stderr, and returncode.
        """
        content_lines: list[str] = []
        stderr_lines: list[str] = []

        # These are guaranteed to be set since we passed stdout=PIPE and stderr=PIPE
        assert process.stdout is not None
        assert process.stderr is not None
        stdout = process.stdout
        stderr = process.stderr

        async def read_stdout() -> None:
            """Read stdout line-by-line and stream to console."""
            while True:
                line = await stdout.readline()
                if not line:
                    break
                decoded = line.decode()
                content_lines.append(decoded)
                # Stream to console in real-time
                self.console.print(decoded, end="")

        async def read_stderr() -> None:
            """Read stderr line-by-line."""
            while True:
                line = await stderr.readline()
                if not line:
                    break
                stderr_lines.append(line.decode())

        # Create concurrent tasks for stdout and stderr
        stdout_task = asyncio.create_task(read_stdout())
        stderr_task = asyncio.create_task(read_stderr())

        # Wait for both to complete
        await asyncio.gather(stdout_task, stderr_task)

        # Wait for process to complete
        await process.wait()

        logger.debug(
            "Claude Code process completed",
            extra={
                "returncode": process.returncode,
                "stdout_lines": len(content_lines),
                "stderr_lines": len(stderr_lines),
            },
        )

        return {
            "stdout": "".join(content_lines),
            "stderr": "".join(stderr_lines),
            "returncode": process.returncode,
        }

    def _build_result(
        self,
        process_output: dict[str, Any],
        start_time: float,
    ) -> LLMResult:
        """Build LLMResult from process output.

        Args:
            process_output: Dictionary with stdout, stderr, returncode.
            start_time: Time when execution started.

        Returns:
            LLMResult instance.
        """
        duration_ms = int((time.monotonic() - start_time) * 1000)
        raw_output = process_output["stdout"]
        stderr = process_output["stderr"]
        returncode = process_output["returncode"]

        # Parse the output to extract content, tool calls, and tokens
        parsed = self._parse_output(raw_output)

        logger.debug(
            "Parsed Claude Code output",
            extra={
                "content_length": len(parsed["content"]),
                "tool_calls": len(parsed["tool_calls"]),
                "tokens_used": parsed["tokens_used"],
                "duration_ms": duration_ms,
            },
        )

        # Build result
        if returncode == 0:
            return LLMResult(
                success=True,
                content=parsed["content"],
                tool_calls=parsed["tool_calls"],
                tokens_used=parsed["tokens_used"],
                duration_ms=duration_ms,
            )
        else:
            return LLMResult(
                success=False,
                content=parsed["content"],
                tool_calls=parsed["tool_calls"],
                tokens_used=parsed["tokens_used"],
                duration_ms=duration_ms,
                error=stderr or f"Claude Code exited with code {returncode}",
            )

    def _parse_output(
        self, raw_output: str
    ) -> dict[str, Any]:
        """Parse Claude Code --print output format.

        Claude Code with --print outputs JSONL (JSON Lines) format where
        each line contains a message object. This method extracts:
        - Text content from assistant messages
        - Tool calls from tool_use messages
        - Token usage from result message

        Args:
            raw_output: The raw output from Claude Code subprocess.

        Returns:
            Dictionary containing:
            - content: str - extracted text content
            - tool_calls: list[ToolCall] - extracted tool calls
            - tokens_used: int - token count if available
        """
        content_parts: list[str] = []
        tool_calls: list[ToolCall] = []
        tokens_used = 0

        for line in raw_output.strip().split("\n"):
            if not line.strip():
                continue

            try:
                data = json.loads(line)
            except json.JSONDecodeError:
                # Not JSON, treat as plain text content
                content_parts.append(line)
                continue

            # If not a dict (e.g., plain number/string JSON), treat as content
            if not isinstance(data, dict):
                content_parts.append(str(data))
                continue

            # Handle different message types from Claude Code output
            msg_type = data.get("type", "")

            if msg_type == "assistant":
                # Assistant message contains content blocks
                for block in data.get("message", {}).get("content", []):
                    if block.get("type") == "text":
                        content_parts.append(block.get("text", ""))
                    elif block.get("type") == "tool_use":
                        tool_calls.append(
                            ToolCall(
                                tool_name=block.get("name", "unknown"),
                                arguments=block.get("input", {}),
                                result_summary=None,
                            )
                        )

            elif msg_type == "result":
                # Result message may contain token usage
                usage = data.get("usage", {})
                tokens_used = usage.get("input_tokens", 0) + usage.get(
                    "output_tokens", 0
                )
                # Also extract final text if present
                if "text" in data:
                    content_parts.append(data["text"])

            elif msg_type == "content_block_delta":
                # Streaming content delta
                delta = data.get("delta", {})
                if delta.get("type") == "text_delta":
                    content_parts.append(delta.get("text", ""))

            elif msg_type == "message_delta":
                # Message delta with usage
                usage = data.get("usage", {})
                if usage:
                    tokens_used = usage.get("input_tokens", 0) + usage.get(
                        "output_tokens", 0
                    )

        return {
            "content": "".join(content_parts),
            "tool_calls": tool_calls,
            "tokens_used": tokens_used,
        }

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
                logger.debug("Using absolute Claude path", extra={"path": path})
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
            logger.debug(
                "Found Claude in PATH",
                extra={"requested": path, "resolved": which_result},
            )
            return Path(which_result)

        raise LLMError(
            code="CLAUDE_NOT_FOUND",
            message=f"Claude Code CLI '{path}' not found in PATH",
            suggestion=(
                "Install Claude Code or configure llm.claude_code.path in adw.yaml"
            ),
            recoverable=False,
        )
