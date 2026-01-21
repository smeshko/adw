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
from typing import TYPE_CHECKING, Any

from rich.console import Console

from adw.exceptions import LLMError, LLMTimeoutError
from adw.models.config import LLMConfig
from adw.models.llm import LLMResult, StreamEvent, StreamEventType, ToolCall

if TYPE_CHECKING:
    from adw.logging.live_stream import LiveStreamTransport
    from adw.security.interceptor import SecurityInterceptor

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
        phase: str | None = None,
        cwd: Path | None = None,
    ) -> LLMResult:
        """Execute a prompt using Claude Code CLI.

        Spawns Claude Code as a subprocess, streams output in real-time,
        and returns a structured result. LLM output is always written to
        live.log when a live_stream transport is configured.

        Args:
            prompt: The prompt to send to Claude Code.
            timeout: Optional timeout in seconds. If None, uses config default.
            phase: Optional phase name for log context.
            cwd: Optional working directory for subprocess execution.
                 If None, uses current working directory (legacy mode).
                 Used for worktree isolation support (Story 10.5).

        Returns:
            LLMResult with success status, content, tool calls, and metrics.

        Raises:
            LLMError: If Claude Code is not found, execution fails, or timeout.
        """
        effective_timeout = self._resolve_timeout(timeout)

        # Log LLM start to live stream
        if self.live_stream:
            self.live_stream.write_llm_start(phase)

        result = asyncio.run(
            self._stream_subprocess(prompt, effective_timeout, cwd=cwd)
        )

        # Log LLM end to live stream
        if self.live_stream:
            self.live_stream.write_llm_end(result.tokens_used, result.duration_ms)

        return result

    async def _stream_subprocess(
        self,
        prompt: str,
        timeout: int,
        *,
        cwd: Path | None = None,
    ) -> LLMResult:
        """Execute Claude Code subprocess with streaming output.

        Uses concurrent tasks for stdout/stderr to prevent deadlocks,
        and enforces timeout on the entire operation. LLM tokens are
        written to live.log when a live_stream transport is configured.

        Args:
            prompt: The prompt to send to Claude Code.
            timeout: Timeout in seconds.
            cwd: Optional working directory for subprocess execution.
                 If None, uses current working directory (legacy mode).

        Returns:
            LLMResult with execution results.

        Raises:
            LLMError: If timeout is exceeded.
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
                "cwd": str(cwd) if cwd else None,
            },
        )

        # Create subprocess with increased buffer limit for large JSON outputs
        # Default is 64KB which can be exceeded by tool results with large file contents
        process = await asyncio.create_subprocess_exec(
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            limit=1024 * 1024,  # 1MB buffer limit
            cwd=cwd,  # Set working directory for worktree support (Story 10.5)
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
        by NFR3 (artifact writes don't block stream). LLM tokens are
        written to live.log when a live_stream transport is configured.

        Tool calls and results are streamed in real-time via _extract_stream_event()
        rather than being batched at the end.

        Args:
            process: The subprocess to read from.

        Returns:
            Dictionary with stdout_lines, stderr, returncode, and
            streamed_tool_ids (set of tool IDs already written to live.log).
        """
        content_lines: list[str] = []
        stderr_lines: list[str] = []

        # Track pending tool calls by ID for correlating with results
        pending_tools: dict[str, dict[str, Any]] = {}
        # Track which tool IDs have been streamed to live.log
        streamed_tool_ids: set[str] = set()

        # These are guaranteed to be set since we passed stdout=PIPE and stderr=PIPE
        assert process.stdout is not None
        assert process.stderr is not None
        stdout = process.stdout
        stderr = process.stderr

        async def read_stdout() -> None:
            """Read stdout line-by-line and write to live.log.

            With --output-format stream-json, each line is JSON.
            We parse it to extract text content, tool calls, and tool results
            and write them to live.log for real-time tailing via `adw logs follow`.

            Note: Console output is NOT displayed - use `adw logs follow`
            in another terminal to see real-time LLM output.
            """
            while True:
                line = await stdout.readline()
                if not line:
                    break
                decoded = line.decode()
                content_lines.append(decoded)

                # Write events to live.log for real-time tailing
                if self.live_stream:
                    event = self._extract_stream_event(decoded)
                    if event:
                        if event.event_type == StreamEventType.TEXT:
                            self.live_stream.write_llm_token(event.content)

                        elif event.event_type == StreamEventType.TOOL_START:
                            # Store pending tool info for later result correlation
                            pending_tools[event.tool_id] = {
                                "name": event.tool_name,
                                "input": event.tool_input,
                            }
                            # Write tool call header immediately
                            context = self._extract_tool_context(
                                event.tool_name, event.tool_input
                            )
                            self.live_stream.write_tool_call(event.tool_name, context)
                            streamed_tool_ids.add(event.tool_id)

                        elif event.event_type == StreamEventType.TOOL_RESULT:
                            # Write tool result with boxed output
                            self.live_stream.write_tool_result(
                                event.tool_output,
                                is_error=event.is_error,
                            )

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
            "streamed_tool_ids": streamed_tool_ids,
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

        # Note: Tool calls are now logged in real-time during streaming via
        # _extract_stream_event() in _read_process_output(). We no longer
        # log them here to avoid duplicate entries (AC3).

        # Build result
        if returncode == 0:
            return LLMResult(
                success=True,
                content=parsed["content"],
                final_output=parsed.get("final_output", ""),
                tool_calls=parsed["tool_calls"],
                tokens_used=parsed["tokens_used"],
                duration_ms=duration_ms,
            )
        else:
            error_msg = stderr or f"Claude Code exited with code {returncode}"
            # Log error to live stream
            if self.live_stream:
                self.live_stream.write_error(error_msg)
            return LLMResult(
                success=False,
                content=parsed["content"],
                final_output=parsed.get("final_output", ""),
                tool_calls=parsed["tool_calls"],
                tokens_used=parsed["tokens_used"],
                duration_ms=duration_ms,
                error=error_msg,
            )

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
        tokens_used = 0
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
                # Result message may contain token usage
                usage = data.get("usage", {})
                tokens_used = usage.get("input_tokens", 0) + usage.get(
                    "output_tokens", 0
                )
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
                    tokens_used = usage.get("input_tokens", 0) + usage.get(
                        "output_tokens", 0
                    )

        # Save the final assistant message text
        if current_message_text:
            last_assistant_text = current_message_text

        # Build final output from last assistant message
        final_output = "".join(last_assistant_text)

        return {
            "content": "".join(content_parts),
            "final_output": final_output,
            "tool_calls": tool_calls,
            "tokens_used": tokens_used,
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
            A brief context string (e.g., file path), or None.
        """
        max_len = 60

        if tool_name == "Read":
            path = arguments.get("file_path", "")
            return path[:max_len] if path else None

        if tool_name == "Write":
            path = arguments.get("file_path", "")
            return path[:max_len] if path else None

        if tool_name == "Edit":
            path = arguments.get("file_path", "")
            return path[:max_len] if path else None

        if tool_name == "Bash":
            cmd = arguments.get("command", "")
            return cmd[:max_len] if cmd else None

        if tool_name == "Glob":
            pattern = arguments.get("pattern", "")
            return pattern[:max_len] if pattern else None

        if tool_name == "Grep":
            pattern = arguments.get("pattern", "")
            return pattern[:max_len] if pattern else None

        if tool_name == "Task":
            subagent = str(arguments.get("subagent_type", ""))
            if subagent:
                return subagent[:max_len]
            desc = str(arguments.get("description", ""))
            return desc[:max_len] if desc else None

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

    def _extract_stream_event(self, line: str) -> StreamEvent | None:
        """Extract a structured stream event from a stream-json line.

        Claude Code --output-format stream-json produces JSONL with various
        message types. This method parses lines and returns structured events
        for real-time handling of text, tool starts, and tool results.

        Args:
            line: A single line of stream-json output.

        Returns:
            StreamEvent if the line contains a relevant event, None otherwise.
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
                if text:
                    return StreamEvent(
                        event_type=StreamEventType.TEXT,
                        content=str(text),
                    )

        # Handle tool_use start from content_block_start
        if msg_type == "content_block_start":
            content_block = data.get("content_block", {})
            if content_block.get("type") == "tool_use":
                return StreamEvent(
                    event_type=StreamEventType.TOOL_START,
                    tool_name=content_block.get("name", "unknown"),
                    tool_id=content_block.get("id", ""),
                    tool_input=content_block.get("input", {}),
                )

        # Handle tool_result messages
        if msg_type == "tool_result":
            # Extract text content from the result
            content_list = data.get("content", [])
            output_parts: list[str] = []
            for item in content_list:
                if isinstance(item, dict) and item.get("type") == "text":
                    output_parts.append(item.get("text", ""))
                elif isinstance(item, str):
                    output_parts.append(item)

            return StreamEvent(
                event_type=StreamEventType.TOOL_RESULT,
                tool_id=data.get("tool_use_id", ""),
                tool_output="\n".join(output_parts),
                is_error=data.get("is_error", False),
            )

        return None

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

