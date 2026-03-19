"""Claude Code CLI Executor.

This module provides the ClaudeCodeExecutor that implements the LLMExecutor
protocol by invoking the Claude Code CLI as a subprocess with real-time
streaming output.
"""

import asyncio
import json
import logging
import os
import shutil
import signal
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any

from rich.console import Console

from adw.exceptions import LLMError
from adw.models.config import LLMConfig
from adw.models.llm import LLMResult, ToolCall

if TYPE_CHECKING:
    from adw.logging.live_stream import LiveStreamTransport
    from adw.security.interceptor import SecurityInterceptor

logger = logging.getLogger(__name__)


class ClaudeCodeExecutor:
    """LLM Executor using Claude Code CLI.

    Executes prompts by spawning the Claude Code CLI as a subprocess,
    streaming output in real-time, and returning structured results.

    Implements the LLMExecutor Protocol for interchangeability with
    MockExecutor in tests.

    Example:
        >>> config = LLMConfig(path="claude")
        >>> executor = ClaudeCodeExecutor(config)
        >>> result = executor.execute("Generate a hello world program")
        >>> print(result.content)
    """

    def __init__(
        self,
        config: LLMConfig,
        *,
        console: Console | None = None,
        security_interceptor: "SecurityInterceptor | None" = None,
        allow_dangerous: bool = False,
        live_stream: "LiveStreamTransport | None" = None,
    ) -> None:
        """Initialize the ClaudeCodeExecutor.

        Args:
            config: LLM configuration containing path, timeout, and other settings.
            console: Optional Rich console for streaming output. If not provided,
                     a new Console instance is created.
            security_interceptor: Optional SecurityInterceptor for checking tool
                        calls against security patterns (Story 3.6).
            allow_dangerous: If True, log warnings instead of blocking dangerous
                        commands (Story 3.6).
            live_stream: Optional LiveStreamTransport for writing LLM tokens
                        to live.log for real-time tailing.
        """
        self.config = config
        self.console = console or Console()
        self.security_interceptor = security_interceptor
        self.allow_dangerous = allow_dangerous
        self.live_stream = live_stream

    def execute(
        self,
        prompt: str,
        *,
        timeout: int | None = None,
        phase: str | None = None,
        cwd: Path | None = None,
        model: str | None = None,
    ) -> LLMResult:
        """Execute a prompt using Claude Code CLI.

        Spawns Claude Code as a subprocess, streams output in real-time,
        and returns a structured result. LLM output is always written to
        live.log when a live_stream transport is configured.

        Args:
            prompt: The prompt to send to Claude Code.
            timeout: Unused, kept for interface compatibility.
            phase: Optional phase name for log context.
            cwd: Optional working directory for subprocess execution.
                 If None, uses current working directory (legacy mode).
                 Used for worktree isolation support (Story 10.5).
            model: Optional model identifier to use for this call.
                 If None, no --model flag is passed.

        Returns:
            LLMResult with success status, content, tool calls, and metrics.

        Raises:
            LLMError: If Claude Code is not found or execution fails.
        """
        # Log LLM start to live stream
        if self.live_stream:
            self.live_stream.write_llm_start(phase)

        result = asyncio.run(self._stream_subprocess(prompt, cwd=cwd, model=model))

        # Log LLM end to live stream
        if self.live_stream:
            self.live_stream.write_llm_end(result.tokens_used, result.duration_ms)

        return result

    async def _stream_subprocess(
        self,
        prompt: str,
        *,
        cwd: Path | None = None,
        model: str | None = None,
    ) -> LLMResult:
        """Execute Claude Code subprocess with streaming output.

        Uses concurrent tasks for stdout/stderr to prevent deadlocks.
        LLM tokens are written to live.log when a live_stream transport
        is configured. Runs without a timeout so the LLM can complete
        naturally.

        Args:
            prompt: The prompt to send to Claude Code.
            cwd: Optional working directory for subprocess execution.
                 If None, uses current working directory (legacy mode).
            model: Optional model identifier. If set, passes --model flag.

        Returns:
            LLMResult with execution results.

        Raises:
            LLMError: If execution fails.
        """
        start_time = time.monotonic()

        # Verify Claude path exists
        claude_path = self._verify_claude_path()

        # Build command arguments
        # Note: --output-format stream-json requires --verbose
        args = [
            str(claude_path),
            "--print",
            "--verbose",
            "--output-format",
            "stream-json",  # Structured output with tokens
            "--dangerously-skip-permissions",  # Allow automated file writes
            prompt,
        ]

        # Add model if specified per-call
        if model:
            args.extend(["--model", model])

        logger.debug(
            "Executing Claude Code",
            extra={
                "path": str(claude_path),
                "model": model,
                "prompt_length": len(prompt),
                "cwd": str(cwd) if cwd else None,
            },
        )

        # Create subprocess with increased buffer limit for large JSON outputs.
        # Claude Code outputs JSON lines that can be very large when tool results
        # contain file contents (e.g., reading large files). 10MB handles most cases.
        # start_new_session=True puts the process in its own process group so we
        # can kill orphaned children (e.g., background codex exec) if the main
        # process exits but grandchildren hold the pipe FDs open.
        process = await asyncio.create_subprocess_exec(
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            limit=10 * 1024 * 1024,  # 10MB buffer limit for large tool results
            cwd=cwd,  # Set working directory for worktree support (Story 10.5)
            start_new_session=True,  # Own process group for clean kill
        )

        try:
            # Use concurrent tasks to read stdout and stderr to prevent deadlocks
            result = await self._read_process_output(process)
            return self._build_result(result, start_time)

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

    async def _read_process_output(
        self,
        process: asyncio.subprocess.Process,
    ) -> dict[str, Any]:
        """Read stdout and stderr concurrently to prevent deadlocks.

        Uses asyncio.create_task() for concurrent processing as required
        by NFR3 (artifact writes don't block stream). LLM tokens are
        written to live.log when a live_stream transport is configured.

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
            """Read stdout line-by-line and write to live.log.

            With --output-format stream-json, each line is JSON.
            We parse it to extract text content and write to live.log
            for real-time tailing via `adw logs follow`.

            Note: Console output is NOT displayed - use `adw logs follow`
            in another terminal to see real-time LLM output.
            """
            while True:
                line = await stdout.readline()
                if not line:
                    break
                decoded = line.decode()
                content_lines.append(decoded)

                # Write tokens to live.log for real-time tailing
                if self.live_stream:
                    display_text = self._extract_display_text(decoded)
                    if display_text:
                        self.live_stream.write_llm_token(display_text)

                    # Detect and log tool calls inline as they happen
                    tool_info = self._extract_tool_call(decoded)
                    if tool_info:
                        self.live_stream.write_tool_call(tool_info[0], tool_info[1])

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

        # Wait for the main process to exit first. Once it exits, the readers
        # should get EOF shortly — unless an orphaned child process (e.g., a
        # background `codex exec`) inherited the pipe FDs and keeps them open.
        await process.wait()

        # Give readers a short grace period to drain remaining output after
        # the process exits. If they're still blocked, an orphaned child is
        # holding the pipe open — kill the entire process group and cancel.
        try:
            await asyncio.wait_for(
                asyncio.gather(stdout_task, stderr_task),
                timeout=5.0,
            )
        except TimeoutError:
            logger.warning(
                "Pipe readers still blocked after process exit — "
                "killing orphaned child processes",
                extra={"pid": process.pid},
            )
            self._kill_process_group(process.pid)
            stdout_task.cancel()
            stderr_task.cancel()
            # Suppress CancelledError from the cancelled tasks
            import contextlib

            for task in (stdout_task, stderr_task):
                with contextlib.suppress(Exception):
                    await task

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

        # Build common kwargs for LLMResult
        common = {
            "content": parsed["content"],
            "final_output": parsed.get("final_output", ""),
            "tool_calls": parsed["tool_calls"],
            "tokens_used": parsed["tokens_used"],
            "input_tokens": parsed["input_tokens"],
            "output_tokens": parsed["output_tokens"],
            "cache_creation_input_tokens": parsed["cache_creation_input_tokens"],
            "cache_read_input_tokens": parsed["cache_read_input_tokens"],
            "total_cost_usd": parsed["total_cost_usd"],
            "duration_ms": duration_ms,
        }

        # Build result
        if returncode == 0:
            return LLMResult(success=True, **common)
        else:
            error_msg = stderr or f"Claude Code exited with code {returncode}"
            # Log error to live stream
            if self.live_stream:
                self.live_stream.write_error(error_msg)
            return LLMResult(success=False, error=error_msg, **common)

    def _parse_output(self, raw_output: str) -> dict[str, Any]:
        """Parse Claude Code --print output format.

        Claude Code with --print outputs JSONL (JSON Lines) format where
        each line contains a message object. This method extracts:
        - Text content from assistant messages
        - Tool calls from tool_use messages
        - Token usage from result message
        - Final output (last assistant message text only) - ISS-023

        Args:
            raw_output: The raw output from Claude Code subprocess.

        Returns:
            Dictionary containing:
            - content: str - full extracted text content (all messages)
            - final_output: str - only the last assistant message text
            - tool_calls: list[ToolCall] - extracted tool calls
            - tokens_used: int - token count if available
        """
        content_parts: list[str] = []
        tool_calls: list[ToolCall] = []
        input_tokens = 0
        output_tokens = 0
        cache_creation_input_tokens = 0
        cache_read_input_tokens = 0
        total_cost_usd = 0.0
        # Track the last assistant message text separately (ISS-023)
        last_assistant_text: list[str] = []
        current_message_text: list[str] = []
        in_assistant_message = False

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
                # Start of a new assistant message - save previous if exists
                if in_assistant_message and current_message_text:
                    last_assistant_text = current_message_text.copy()
                current_message_text = []
                in_assistant_message = True

                # Assistant message contains content blocks
                for block in data.get("message", {}).get("content", []):
                    if block.get("type") == "text":
                        text = block.get("text", "")
                        content_parts.append(text)
                        current_message_text.append(text)
                    elif block.get("type") == "tool_use":
                        tool_calls.append(
                            ToolCall(
                                tool_name=block.get("name", "unknown"),
                                arguments=block.get("input", {}),
                                result_summary=None,
                            )
                        )

            elif msg_type == "result":
                # Result message contains authoritative cumulative token usage
                usage = data.get("usage", {})
                input_tokens = usage.get("input_tokens", 0)
                output_tokens = usage.get("output_tokens", 0)
                cache_creation_input_tokens = usage.get(
                    "cache_creation_input_tokens", 0
                )
                cache_read_input_tokens = usage.get("cache_read_input_tokens", 0)
                # total_cost_usd is at top level of result message
                total_cost_usd = data.get("total_cost_usd", total_cost_usd)
                # Also extract final text if present
                if "text" in data:
                    text = data["text"]
                    content_parts.append(text)
                    # Result text is considered final output
                    if in_assistant_message:
                        current_message_text.append(text)

            elif msg_type == "content_block_delta":
                # Streaming content delta
                delta = data.get("delta", {})
                if delta.get("type") == "text_delta":
                    text = delta.get("text", "")
                    content_parts.append(text)
                    # Track streaming deltas as part of current message
                    if in_assistant_message:
                        current_message_text.append(text)

            elif msg_type == "message_delta":
                # Message delta with usage
                usage = data.get("usage", {})
                if usage:
                    input_tokens += usage.get("input_tokens", 0)
                    output_tokens += usage.get("output_tokens", 0)

        # Save the final assistant message text
        if current_message_text:
            last_assistant_text = current_message_text

        # Build final output from last assistant message
        final_output = "".join(last_assistant_text)

        # Total input includes all three input token types
        total_input = (
            input_tokens + cache_creation_input_tokens + cache_read_input_tokens
        )

        return {
            "content": "".join(content_parts),
            "final_output": final_output,
            "tool_calls": tool_calls,
            "input_tokens": total_input,
            "output_tokens": output_tokens,
            "cache_creation_input_tokens": cache_creation_input_tokens,
            "cache_read_input_tokens": cache_read_input_tokens,
            "total_cost_usd": total_cost_usd,
            "tokens_used": total_input + output_tokens,
        }

    def _extract_tool_context(
        self,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> str | None:
        """Extract meaningful context from tool arguments for logging.

        Args:
            tool_name: Name of the tool.
            arguments: Tool arguments.

        Returns:
            A context string (e.g., file path), or None.
            Newlines are replaced with ↵ to keep log entries on single lines.
        """
        context: str | None = None

        if tool_name == "Read" or tool_name == "Write" or tool_name == "Edit":
            context = arguments.get("file_path") or None

        elif tool_name == "Bash":
            context = arguments.get("command") or None

        elif tool_name == "Glob" or tool_name == "Grep":
            context = arguments.get("pattern") or None

        elif tool_name == "Task":
            subagent = arguments.get("subagent_type")
            context = subagent or (arguments.get("description") or None)

        # Replace newlines with ↵ to keep log entries on single lines
        if context and "\n" in context:
            context = context.replace("\n", " ↵ ")

        return context

    def _extract_tool_call(self, line: str) -> tuple[str, str | None] | None:
        """Extract tool call info from stream-json line for inline logging.

        Detects tool_use blocks in assistant messages as they stream, enabling
        real-time logging of tool calls instead of batching at end.

        Args:
            line: A single line of stream-json output.

        Returns:
            Tuple of (tool_name, context) if tool call found, None otherwise.
        """
        try:
            data = json.loads(line.strip())
        except json.JSONDecodeError:
            return None

        if not isinstance(data, dict):
            return None

        # Check for tool_use in assistant message content blocks
        if data.get("type") == "assistant":
            for block in data.get("message", {}).get("content", []):
                if block.get("type") == "tool_use":
                    tool_name = block.get("name", "unknown")
                    context = self._extract_tool_context(
                        tool_name, block.get("input", {})
                    )
                    return (tool_name, context)

        return None

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
                suggestion="Install Claude Code or configure "
                "llm.claude_code.path in project.yaml",
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
                "Install Claude Code or configure llm.claude_code.path in project.yaml"
            ),
            recoverable=False,
        )

    @staticmethod
    def _kill_process_group(pid: int) -> None:
        """Kill an entire process group to clean up orphaned children.

        Used when the main Claude Code process has exited but child processes
        (e.g., a background `codex exec`) still hold the stdout/stderr pipe
        FDs open, preventing the readers from getting EOF.

        Args:
            pid: PID of the process whose group should be killed.
        """
        try:
            os.killpg(pid, signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            # Process group already gone or not owned by us
            pass
        except OSError as e:
            logger.debug(
                "Failed to kill process group",
                extra={"pid": pid, "error": str(e)},
            )

    def _extract_display_text(self, line: str) -> str | None:
        """Extract displayable text from a stream-json line.

        Claude Code --output-format stream-json produces JSONL with various
        message types. This extracts text content suitable for real-time display.

        Args:
            line: A single line of stream-json output.

        Returns:
            Text content to display, or None if no displayable content.
        """
        try:
            data = json.loads(line.strip())
        except json.JSONDecodeError:
            return None

        if not isinstance(data, dict):
            return None

        msg_type = data.get("type", "")

        # Extract text from content block deltas (streaming text)
        if msg_type == "content_block_delta":
            delta = data.get("delta", {})
            if delta.get("type") == "text_delta":
                text = delta.get("text", "")
                return str(text) if text else None

        # Extract text from assistant message content blocks
        if msg_type == "assistant":
            for block in data.get("message", {}).get("content", []):
                if block.get("type") == "text":
                    text = block.get("text", "")
                    return str(text) if text else None

        return None
