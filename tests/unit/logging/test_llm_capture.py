"""Tests for LLMCaptureManager class (Story 7.3)."""

import json
from pathlib import Path

from adw.logging.llm_capture import LLMCaptureManager
from adw.models.logging import (
    LLMRequest,
    LLMResponse,
    LLMStats,
    LLMStreamEvent,
    LLMToolCall,
    StreamEventType,
)


class TestLLMCaptureManagerCreation:
    """Tests for LLMCaptureManager initialization."""

    def test_create_capture_manager(self, tmp_path: Path) -> None:
        """LLMCaptureManager can be created with run directory."""
        llm_dir = tmp_path / "llm"
        manager = LLMCaptureManager(llm_dir)
        assert manager is not None

    def test_creates_llm_directory(self, tmp_path: Path) -> None:
        """LLMCaptureManager creates the llm directory if needed."""
        llm_dir = tmp_path / "llm"
        assert not llm_dir.exists()
        manager = LLMCaptureManager(llm_dir)
        # Directory created on first capture, not on init
        manager.capture_request(
            LLMRequest(prompt="test", phase="plan")
        )
        assert llm_dir.exists()

    def test_initial_sequence_is_one(self, tmp_path: Path) -> None:
        """Initial sequence number is 1."""
        manager = LLMCaptureManager(tmp_path / "llm")
        assert manager.sequence == 1


class TestLLMCaptureManagerRequest:
    """Tests for LLMCaptureManager.capture_request()."""

    def test_capture_request_creates_file(self, tmp_path: Path) -> None:
        """capture_request() creates a request JSON file."""
        llm_dir = tmp_path / "llm"
        manager = LLMCaptureManager(llm_dir)
        request = LLMRequest(
            prompt="Generate hello world",
            phase="build",
            params={"model": "claude-sonnet-4-20250514"},
        )
        manager.capture_request(request)

        expected_file = llm_dir / "001_build_request.json"
        assert expected_file.exists()

    def test_capture_request_content(self, tmp_path: Path) -> None:
        """capture_request() writes correct JSON content."""
        llm_dir = tmp_path / "llm"
        manager = LLMCaptureManager(llm_dir)
        request = LLMRequest(
            prompt="Test prompt",
            phase="plan",
            params={"model": "claude-sonnet-4-20250514", "temperature": 0},
        )
        manager.capture_request(request)

        file_path = llm_dir / "001_plan_request.json"
        content = json.loads(file_path.read_text())
        assert content["prompt"] == "Test prompt"
        assert content["phase"] == "plan"
        assert content["params"]["model"] == "claude-sonnet-4-20250514"

    def test_capture_request_does_not_increment_sequence(self, tmp_path: Path) -> None:
        """capture_request() does NOT increment sequence (use next_sequence())."""
        llm_dir = tmp_path / "llm"
        manager = LLMCaptureManager(llm_dir)

        manager.capture_request(LLMRequest(prompt="first", phase="plan"))
        assert manager.sequence == 1  # Still 1, not incremented

        manager.next_sequence()  # Explicitly advance
        assert manager.sequence == 2

        manager.capture_request(LLMRequest(prompt="second", phase="build"))
        assert manager.sequence == 2  # Still 2, not incremented


class TestLLMCaptureManagerResponse:
    """Tests for LLMCaptureManager.capture_response()."""

    def test_capture_response_creates_file(self, tmp_path: Path) -> None:
        """capture_response() creates a response JSON file."""
        llm_dir = tmp_path / "llm"
        manager = LLMCaptureManager(llm_dir)

        # Capture request first to set sequence
        manager.capture_request(LLMRequest(prompt="test", phase="build"))

        response = LLMResponse(
            content="Generated code here",
            phase="build",
            stats=LLMStats(input_tokens=100, output_tokens=50, duration_ms=1000),
        )
        manager.capture_response(response)

        expected_file = llm_dir / "001_build_response.json"
        assert expected_file.exists()

    def test_capture_response_content(self, tmp_path: Path) -> None:
        """capture_response() writes correct JSON content."""
        llm_dir = tmp_path / "llm"
        manager = LLMCaptureManager(llm_dir)

        manager.capture_request(LLMRequest(prompt="test", phase="plan"))

        response = LLMResponse(
            content="Response content",
            phase="plan",
            tool_calls=[LLMToolCall(id="call_01", name="create_file", input={})],
            stats=LLMStats(input_tokens=4521, output_tokens=3892, duration_ms=47333),
        )
        manager.capture_response(response)

        file_path = llm_dir / "001_plan_response.json"
        content = json.loads(file_path.read_text())
        assert content["content"] == "Response content"
        assert content["phase"] == "plan"
        assert len(content["tool_calls"]) == 1
        assert content["stats"]["input_tokens"] == 4521

    def test_capture_response_does_not_increment_sequence(self, tmp_path: Path) -> None:
        """capture_response() does not increment sequence."""
        llm_dir = tmp_path / "llm"
        manager = LLMCaptureManager(llm_dir)

        manager.capture_request(LLMRequest(prompt="test", phase="build"))
        assert manager.sequence == 1

        manager.capture_response(LLMResponse(content="response", phase="build"))
        assert manager.sequence == 1  # Still 1, neither method increments


class TestLLMCaptureManagerStream:
    """Tests for LLMCaptureManager.capture_stream()."""

    def test_capture_stream_creates_file(self, tmp_path: Path) -> None:
        """capture_stream() creates a stream JSONL file."""
        llm_dir = tmp_path / "llm"
        manager = LLMCaptureManager(llm_dir)

        manager.capture_request(LLMRequest(prompt="test", phase="build"))

        events = [
            LLMStreamEvent(t=0, type=StreamEventType.TOKEN, content="Hello"),
            LLMStreamEvent(t=10, type=StreamEventType.TOKEN, content=" world"),
        ]
        manager.capture_stream(events)

        expected_file = llm_dir / "001_build_stream.jsonl"
        assert expected_file.exists()

    def test_capture_stream_content(self, tmp_path: Path) -> None:
        """capture_stream() writes correct JSONL content."""
        llm_dir = tmp_path / "llm"
        manager = LLMCaptureManager(llm_dir)

        manager.capture_request(LLMRequest(prompt="test", phase="plan"))

        events = [
            LLMStreamEvent(t=0, type=StreamEventType.TOKEN, content="I'll"),
            LLMStreamEvent(t=12, type=StreamEventType.TOKEN, content=" create"),
            LLMStreamEvent(
                t=1250,
                type=StreamEventType.TOOL_CALL_START,
                id="call_01",
                name="create_file",
                input={"path": "test.py"},
            ),
        ]
        manager.capture_stream(events)

        file_path = llm_dir / "001_plan_stream.jsonl"
        lines = file_path.read_text().strip().split("\n")
        assert len(lines) == 3

        first_event = json.loads(lines[0])
        assert first_event["t"] == 0
        assert first_event["type"] == "token"
        assert first_event["content"] == "I'll"

        third_event = json.loads(lines[2])
        assert third_event["type"] == "tool_call_start"
        assert third_event["id"] == "call_01"


class TestLLMCaptureManagerSequencing:
    """Tests for sequence numbering behavior."""

    def test_sequence_zero_padded(self, tmp_path: Path) -> None:
        """Sequence numbers are zero-padded to 3 digits."""
        llm_dir = tmp_path / "llm"
        manager = LLMCaptureManager(llm_dir)

        manager.capture_request(LLMRequest(prompt="test", phase="build"))
        assert (llm_dir / "001_build_request.json").exists()

    def test_next_sequence_increments(self, tmp_path: Path) -> None:
        """next_sequence() increments the sequence number."""
        llm_dir = tmp_path / "llm"
        manager = LLMCaptureManager(llm_dir)

        assert manager.sequence == 1
        manager.next_sequence()
        assert manager.sequence == 2
        manager.next_sequence()
        assert manager.sequence == 3

    def test_multiple_sequences(self, tmp_path: Path) -> None:
        """Multiple request/response pairs use different sequences."""
        llm_dir = tmp_path / "llm"
        manager = LLMCaptureManager(llm_dir)

        # First pair
        manager.capture_request(LLMRequest(prompt="first", phase="plan"))
        manager.capture_response(LLMResponse(content="response1", phase="plan"))
        manager.next_sequence()  # Move to next sequence

        # Second pair
        manager.capture_request(LLMRequest(prompt="second", phase="build"))
        manager.capture_response(LLMResponse(content="response2", phase="build"))

        assert (llm_dir / "001_plan_request.json").exists()
        assert (llm_dir / "001_plan_response.json").exists()
        assert (llm_dir / "002_build_request.json").exists()
        assert (llm_dir / "002_build_response.json").exists()


class TestLLMCaptureManagerRedaction:
    """Tests for redaction integration."""

    def test_request_applies_redaction(self, tmp_path: Path) -> None:
        """capture_request() applies Redactor.redact() to prompt."""
        from unittest.mock import MagicMock, patch

        llm_dir = tmp_path / "llm"
        manager = LLMCaptureManager(llm_dir)

        mock_redactor = MagicMock()
        mock_redactor.redact.return_value = "REDACTED_PROMPT"

        with patch("adw.logging.llm_capture.get_redactor", return_value=mock_redactor):
            manager.capture_request(
                LLMRequest(prompt="secret: sk-1234", phase="build")
            )

            mock_redactor.redact.assert_called_once_with("secret: sk-1234")

        # Verify redacted content was written
        file_path = llm_dir / "001_build_request.json"
        content = json.loads(file_path.read_text())
        assert content["prompt"] == "REDACTED_PROMPT"

    def test_response_applies_redaction(self, tmp_path: Path) -> None:
        """capture_response() applies Redactor.redact() to content."""
        from unittest.mock import MagicMock, patch

        llm_dir = tmp_path / "llm"
        manager = LLMCaptureManager(llm_dir)
        manager.capture_request(LLMRequest(prompt="test", phase="build"))

        mock_redactor = MagicMock()
        mock_redactor.redact.return_value = "REDACTED_CONTENT"

        with patch("adw.logging.llm_capture.get_redactor", return_value=mock_redactor):
            manager.capture_response(
                LLMResponse(content="API key: sk-secret", phase="build")
            )

            mock_redactor.redact.assert_called_once_with("API key: sk-secret")

        # Verify redacted content was written
        file_path = llm_dir / "001_build_response.json"
        content = json.loads(file_path.read_text())
        assert content["content"] == "REDACTED_CONTENT"


class TestLLMCaptureManagerIntegration:
    """Integration tests for full capture flow."""

    def test_full_capture_flow(self, tmp_path: Path) -> None:
        """Full capture flow with request, stream, and response."""
        llm_dir = tmp_path / "llm"
        manager = LLMCaptureManager(llm_dir)

        # Capture request
        request = LLMRequest(
            prompt="Generate a hello world program",
            phase="build",
            params={"model": "claude-sonnet-4-20250514"},
        )
        manager.capture_request(request)

        # Capture stream
        events = [
            LLMStreamEvent(t=0, type=StreamEventType.TOKEN, content="Here's"),
            LLMStreamEvent(t=50, type=StreamEventType.TOKEN, content=" the code"),
            LLMStreamEvent(
                t=100,
                type=StreamEventType.COMPLETE,
                stats=LLMStats(input_tokens=100, output_tokens=50),
            ),
        ]
        manager.capture_stream(events)

        # Capture response
        response = LLMResponse(
            content="Here's the code",
            phase="build",
            stats=LLMStats(input_tokens=100, output_tokens=50, duration_ms=1000),
        )
        manager.capture_response(response)

        # Verify all files exist
        assert (llm_dir / "001_build_request.json").exists()
        assert (llm_dir / "001_build_stream.jsonl").exists()
        assert (llm_dir / "001_build_response.json").exists()

    def test_current_phase_tracking(self, tmp_path: Path) -> None:
        """Manager tracks current phase from request."""
        llm_dir = tmp_path / "llm"
        manager = LLMCaptureManager(llm_dir)

        manager.capture_request(LLMRequest(prompt="test", phase="build"))
        assert manager.current_phase == "build"
