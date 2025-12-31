"""Claude Code CLI Executor.

This module provides the ClaudeCodeExecutor that implements the LLMExecutor
protocol by invoking the Claude Code CLI as a subprocess with real-time
streaming output.
"""

import asyncio
import json
import shutil
import time
from pathlib import Path
from typing import Any

from rich.console import Console

from adw.exceptions import LLMError
from adw.models.config import LLMConfig
from adw.models.llm import LLMResult, ToolCall


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
        raw_output = "".join(content_lines)

        # Parse the output to extract content, tool calls, and tokens
        parsed = self._parse_output(raw_output)

        # Build result
        if process.returncode == 0:
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
                error=stderr or f"Claude Code exited with code {process.returncode}",
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
