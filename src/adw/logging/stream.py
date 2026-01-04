"""StreamLogger for capturing LLM streaming events.

This module provides the StreamLogger class that captures LLM streaming
events (tokens, tool calls, thinking blocks) for debugging and replay.

Example:
    >>> logger = StreamLogger()
    >>> logger.token("Hello")
    >>> logger.token(" world")
    >>> logger.tool_call(id="call_01", name="create_file", input={"path": "test.py"})
    >>> logger.tool_result(id="call_01", success=True, duration_ms=45)
    >>> logger.end(LLMStats(input_tokens=100, output_tokens=50))
    >>> events = logger.get_events()
"""

import time
from typing import Any

from adw.models.logging import LLMStats, LLMStreamEvent, StreamEventType


class StreamLogger:
    """Logger for capturing LLM streaming events.

    Captures all events during LLM streaming for debugging and replay.
    Events are timestamped relative to logger creation for accurate replay.

    Attributes:
        _events: Internal list of captured events
        _start_time: Monotonic time when logger was created

    Example:
        >>> logger = StreamLogger()
        >>> logger.token("I'll create a file")
        >>> logger.tool_call(id="call_01", name="create_file", input={})
        >>> logger.tool_result(id="call_01", success=True, duration_ms=45)
        >>> logger.end(LLMStats(input_tokens=100, output_tokens=50))
        >>> for event in logger.get_events():
        ...     print(f"{event.t}ms: {event.type.value}")
    """

    def __init__(self) -> None:
        """Initialize the StreamLogger.

        Records the start time for relative timestamps.
        """
        self._events: list[LLMStreamEvent] = []
        self._start_time: float = time.monotonic()

    def _elapsed_ms(self) -> int:
        """Get elapsed time in milliseconds since logger creation.

        Returns:
            Elapsed time in milliseconds.
        """
        return int((time.monotonic() - self._start_time) * 1000)

    def token(self, content: str) -> None:
        """Capture a text token event.

        Args:
            content: The token text content.

        Example:
            >>> logger.token("Hello")
            >>> logger.token(" world")
        """
        event = LLMStreamEvent(
            t=self._elapsed_ms(),
            type=StreamEventType.TOKEN,
            content=content,
        )
        self._events.append(event)

    def tool_call(
        self,
        *,
        id: str,
        name: str,
        input: dict[str, Any] | None = None,
    ) -> None:
        """Capture a tool call start event.

        Args:
            id: Unique identifier for this tool call.
            name: Name of the tool being called.
            input: Arguments passed to the tool.

        Example:
            >>> logger.tool_call(
            ...     id="call_01",
            ...     name="create_file",
            ...     input={"path": "test.py", "content": "# test"}
            ... )
        """
        event = LLMStreamEvent(
            t=self._elapsed_ms(),
            type=StreamEventType.TOOL_CALL_START,
            id=id,
            name=name,
            input=input or {},
        )
        self._events.append(event)

    def tool_result(
        self,
        *,
        id: str,
        success: bool = True,
        duration_ms: int = 0,
    ) -> None:
        """Capture a tool call end event.

        Args:
            id: Tool call ID this result corresponds to.
            success: Whether the tool executed successfully.
            duration_ms: Execution time in milliseconds.

        Example:
            >>> logger.tool_result(id="call_01", success=True, duration_ms=45)
        """
        event = LLMStreamEvent(
            t=self._elapsed_ms(),
            type=StreamEventType.TOOL_CALL_END,
            id=id,
            success=success,
            duration_ms=duration_ms,
        )
        self._events.append(event)

    def thinking(self, content: str) -> None:
        """Capture a thinking/reasoning block event.

        Args:
            content: The thinking/reasoning content.

        Example:
            >>> logger.thinking("Let me analyze this problem...")
        """
        event = LLMStreamEvent(
            t=self._elapsed_ms(),
            type=StreamEventType.THINKING,
            content=content,
        )
        self._events.append(event)

    def end(self, stats: LLMStats) -> None:
        """Capture stream completion event.

        Args:
            stats: Final statistics (tokens, duration).

        Example:
            >>> stats = LLMStats(input_tokens=100, output_tokens=50)
            >>> logger.end(stats)
        """
        event = LLMStreamEvent(
            t=self._elapsed_ms(),
            type=StreamEventType.COMPLETE,
            stats=stats,
        )
        self._events.append(event)

    def error(self, message: str) -> None:
        """Capture an error event.

        Args:
            message: Error message describing what went wrong.

        Example:
            >>> logger.error("Connection timeout after 30 seconds")
        """
        event = LLMStreamEvent(
            t=self._elapsed_ms(),
            type=StreamEventType.ERROR,
            error=message,
        )
        self._events.append(event)

    def get_events(self) -> list[LLMStreamEvent]:
        """Get a copy of all captured events.

        Returns a copy to prevent external mutation of internal state.

        Returns:
            List of captured LLMStreamEvent objects.

        Example:
            >>> events = logger.get_events()
            >>> for event in events:
            ...     print(event.model_dump_json())
        """
        return list(self._events)

    def clear(self) -> None:
        """Clear all captured events and reset the start time.

        Useful for reusing the logger for a new stream.

        Example:
            >>> logger.clear()
            >>> assert len(logger.get_events()) == 0
        """
        self._events.clear()
        self._start_time = time.monotonic()
