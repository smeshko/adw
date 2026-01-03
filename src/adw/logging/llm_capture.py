"""LLM Capture Manager for file-based LLM interaction logging.

This module provides the LLMCaptureManager class that writes LLM
interactions to files for debugging and replay:
- Request JSON: `<seq>_<phase>_request.json`
- Response JSON: `<seq>_<phase>_response.json`
- Stream JSONL: `<seq>_<phase>_stream.jsonl`

Example:
    >>> from pathlib import Path
    >>> manager = LLMCaptureManager(Path(".agent/runs/123/llm"))
    >>> manager.capture_request(LLMRequest(prompt="test", phase="build"))
    >>> manager.capture_stream(stream_events)
    >>> manager.capture_response(LLMResponse(content="...", phase="build"))
    >>> manager.next_sequence()  # Advance to next sequence number
    >>> # Second LLM call uses sequence 002
    >>> manager.capture_request(LLMRequest(prompt="second", phase="plan"))
"""

from pathlib import Path

from adw.logging.redaction import redact_secrets
from adw.models.logging import LLMRequest, LLMResponse, LLMStreamEvent


class LLMCaptureManager:
    """Manager for capturing LLM interactions to files.

    Writes LLM request, response, and stream data to the run's llm directory.
    Uses 3-digit zero-padded sequence numbers for file ordering.

    Sequence Management:
        - All captures (request, stream, response) use the current sequence
        - Call next_sequence() after completing a request/response pair
        - Sequence starts at 1 and increments with each next_sequence() call

    Attributes:
        llm_dir: Directory for LLM capture files (stored as _llm_dir internally)
        sequence: Current sequence number (1-based)
        current_phase: Phase from the current request

    Example:
        >>> manager = LLMCaptureManager(Path(".agent/runs/123/llm"))
        >>> manager.capture_request(request)   # writes 001_..._request.json
        >>> manager.capture_stream(events)     # writes 001_..._stream.jsonl
        >>> manager.capture_response(response) # writes 001_..._response.json
        >>> manager.next_sequence()            # advance to 002
        >>> manager.capture_request(request2)  # writes 002_..._request.json
    """

    def __init__(self, llm_dir: Path | str) -> None:
        """Initialize the LLMCaptureManager.

        Args:
            llm_dir: Directory for LLM capture files (e.g., .agent/runs/123/llm)
        """
        self._llm_dir = Path(llm_dir)
        self._sequence = 1
        self._current_phase: str = "unknown"

    @property
    def llm_dir(self) -> Path:
        """Get the LLM capture directory."""
        return self._llm_dir

    @property
    def sequence(self) -> int:
        """Get the current sequence number."""
        return self._sequence

    @property
    def current_phase(self) -> str:
        """Get the current phase from the last request."""
        return self._current_phase

    def _ensure_dir(self) -> None:
        """Ensure the LLM directory exists."""
        self._llm_dir.mkdir(parents=True, exist_ok=True)

    def _sequence_str(self) -> str:
        """Get the current sequence as a zero-padded string.

        Returns:
            3-digit zero-padded sequence number (e.g., "001", "002").
        """
        return f"{self._sequence:03d}"

    def capture_request(self, request: LLMRequest) -> Path:
        """Capture an LLM request to file.

        Writes the request to `<seq>_<phase>_request.json`.
        Updates the current phase for subsequent captures.

        Note:
            Does NOT increment sequence. Call next_sequence() after
            completing the request/response pair to advance.

        Args:
            request: The LLM request to capture.

        Returns:
            Path to the created request file.

        Example:
            >>> manager.capture_request(
            ...     LLMRequest(prompt="Generate code", phase="build")
            ... )
        """
        self._ensure_dir()
        self._current_phase = request.phase

        filename = f"{self._sequence_str()}_{request.phase}_request.json"
        file_path = self._llm_dir / filename

        # Apply secret redaction before writing (placeholder until Story 7.6)
        redacted_request = request.model_copy(
            update={"prompt": redact_secrets(request.prompt)}
        )

        # Write formatted JSON for readability
        file_path.write_text(redacted_request.model_dump_json(indent=2))

        return file_path

    def capture_response(self, response: LLMResponse) -> Path:
        """Capture an LLM response to file.

        Writes the response to `<seq>_<phase>_response.json`.
        Uses the current sequence number.

        Args:
            response: The LLM response to capture.

        Returns:
            Path to the created response file.

        Example:
            >>> manager.capture_response(
            ...     LLMResponse(content="Here's the code", phase="build")
            ... )
        """
        self._ensure_dir()

        filename = f"{self._sequence_str()}_{response.phase}_response.json"
        file_path = self._llm_dir / filename

        # Apply secret redaction before writing (placeholder until Story 7.6)
        redacted_response = response.model_copy(
            update={"content": redact_secrets(response.content)}
        )

        # Write formatted JSON for readability
        file_path.write_text(redacted_response.model_dump_json(indent=2))

        return file_path

    def capture_stream(self, events: list[LLMStreamEvent]) -> Path:
        """Capture stream events to a JSONL file.

        Writes events to `<seq>_<phase>_stream.jsonl` in JSON Lines format.
        Uses the current sequence number.

        Args:
            events: List of stream events to capture.

        Returns:
            Path to the created stream file.

        Example:
            >>> manager.capture_stream([
            ...     LLMStreamEvent(t=0, type=StreamEventType.TOKEN, content="Hello"),
            ...     LLMStreamEvent(t=10, type=StreamEventType.TOKEN, content=" world"),
            ... ])
        """
        self._ensure_dir()

        filename = f"{self._sequence_str()}_{self._current_phase}_stream.jsonl"
        file_path = self._llm_dir / filename

        # Write JSONL (one JSON object per line)
        lines = [event.model_dump_json() for event in events]
        file_path.write_text("\n".join(lines) + "\n" if lines else "")

        return file_path

    def next_sequence(self) -> None:
        """Advance to the next sequence number.

        Call this after completing a request/response pair to
        prepare for the next LLM interaction.

        Example:
            >>> manager.capture_request(request)
            >>> manager.capture_response(response)
            >>> manager.next_sequence()  # Now at sequence 002
            >>> manager.capture_request(request2)  # Writes 002_..._request.json
        """
        self._sequence += 1
