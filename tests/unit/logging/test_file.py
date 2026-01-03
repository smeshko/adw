"""Tests for the file transport classes."""

import json
import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import pytest

from adw.logging.file import RawFileTransport, StructuredFileTransport
from adw.models.logging import LogCategory, LogContext, LogEvent, LogLevel


class TestRawFileTransport:
    """Tests for the RawFileTransport class."""

    def test_creates_log_file_on_first_write(self, tmp_path: Path) -> None:
        """RawFileTransport creates log file on first write."""
        log_path = tmp_path / "raw.log"
        transport = RawFileTransport(log_path)

        event = LogEvent(
            level=LogLevel.INFO,
            category=LogCategory.PHASE,
            message="Test message",
        )
        transport.write(event)

        assert log_path.exists()

    def test_appends_to_existing_file(self, tmp_path: Path) -> None:
        """RawFileTransport appends to existing file."""
        log_path = tmp_path / "raw.log"
        log_path.write_text("Existing content\n")
        transport = RawFileTransport(log_path)

        event = LogEvent(
            level=LogLevel.INFO,
            category=LogCategory.PHASE,
            message="New message",
        )
        transport.write(event)

        content = log_path.read_text()
        assert "Existing content" in content
        assert "New message" in content

    def test_writes_human_readable_format(self, tmp_path: Path) -> None:
        """RawFileTransport writes human-readable plain text."""
        log_path = tmp_path / "raw.log"
        transport = RawFileTransport(log_path)

        event = LogEvent(
            level=LogLevel.WARN,
            category=LogCategory.HOOK,
            message="Warning message",
        )
        transport.write(event)

        content = log_path.read_text()
        assert "Warning message" in content
        assert "WARN" in content or "warn" in content.lower()

    def test_includes_timestamp(self, tmp_path: Path) -> None:
        """RawFileTransport includes timestamp in output."""
        log_path = tmp_path / "raw.log"
        transport = RawFileTransport(log_path)

        event = LogEvent(
            level=LogLevel.INFO,
            category=LogCategory.STATE,
            message="State change",
        )
        transport.write(event)

        content = log_path.read_text()
        # Should contain some form of time/date
        assert any(c.isdigit() for c in content)

    def test_includes_context_fields(self, tmp_path: Path) -> None:
        """RawFileTransport includes context fields in output."""
        log_path = tmp_path / "raw.log"
        transport = RawFileTransport(log_path)

        event = LogEvent(
            level=LogLevel.INFO,
            category=LogCategory.PHASE,
            message="Phase started",
            context=LogContext(run_id="01HQ123ABC", phase="build"),
        )
        transport.write(event)

        content = log_path.read_text()
        assert "01HQ123ABC" in content
        assert "build" in content

    def test_creates_parent_directories(self, tmp_path: Path) -> None:
        """RawFileTransport creates parent directories if needed."""
        log_path = tmp_path / "logs" / "subdir" / "raw.log"
        transport = RawFileTransport(log_path)

        event = LogEvent(
            level=LogLevel.INFO,
            category=LogCategory.PHASE,
            message="Test",
        )
        transport.write(event)

        assert log_path.exists()

    def test_writes_each_event_on_new_line(self, tmp_path: Path) -> None:
        """RawFileTransport writes each event on a new line."""
        log_path = tmp_path / "raw.log"
        transport = RawFileTransport(log_path)

        for i in range(3):
            event = LogEvent(
                level=LogLevel.INFO,
                category=LogCategory.PHASE,
                message=f"Message {i}",
            )
            transport.write(event)

        lines = log_path.read_text().strip().split("\n")
        assert len(lines) == 3


class TestStructuredFileTransport:
    """Tests for the StructuredFileTransport class."""

    def test_creates_jsonl_file_on_first_write(self, tmp_path: Path) -> None:
        """StructuredFileTransport creates JSONL file on first write."""
        log_path = tmp_path / "logs.jsonl"
        transport = StructuredFileTransport(log_path)

        event = LogEvent(
            level=LogLevel.INFO,
            category=LogCategory.PHASE,
            message="Test message",
        )
        transport.write(event)

        assert log_path.exists()

    def test_writes_valid_json_per_line(self, tmp_path: Path) -> None:
        """StructuredFileTransport writes valid JSON on each line."""
        log_path = tmp_path / "logs.jsonl"
        transport = StructuredFileTransport(log_path)

        event = LogEvent(
            level=LogLevel.INFO,
            category=LogCategory.LLM,
            message="LLM interaction",
        )
        transport.write(event)

        content = log_path.read_text().strip()
        parsed = json.loads(content)
        assert parsed["message"] == "LLM interaction"

    def test_includes_all_required_fields(self, tmp_path: Path) -> None:
        """StructuredFileTransport includes timestamp, level, category, message, context."""
        log_path = tmp_path / "logs.jsonl"
        transport = StructuredFileTransport(log_path)

        event = LogEvent(
            level=LogLevel.DEBUG,
            category=LogCategory.PERFORMANCE,
            message="Performance metric",
            context=LogContext(run_id="01HQ123ABC", phase="build"),
        )
        transport.write(event)

        content = log_path.read_text().strip()
        parsed = json.loads(content)

        assert "timestamp" in parsed
        assert parsed["level"] == "debug"
        assert parsed["category"] == "performance"
        assert parsed["message"] == "Performance metric"
        assert parsed["context"]["run_id"] == "01HQ123ABC"
        assert parsed["context"]["phase"] == "build"

    def test_appends_to_existing_file(self, tmp_path: Path) -> None:
        """StructuredFileTransport appends to existing JSONL file."""
        log_path = tmp_path / "logs.jsonl"
        log_path.write_text('{"existing": true}\n')
        transport = StructuredFileTransport(log_path)

        event = LogEvent(
            level=LogLevel.INFO,
            category=LogCategory.PHASE,
            message="New entry",
        )
        transport.write(event)

        lines = log_path.read_text().strip().split("\n")
        assert len(lines) == 2
        assert json.loads(lines[0])["existing"] is True
        assert json.loads(lines[1])["message"] == "New entry"

    def test_creates_parent_directories(self, tmp_path: Path) -> None:
        """StructuredFileTransport creates parent directories if needed."""
        log_path = tmp_path / "logs" / "subdir" / "logs.jsonl"
        transport = StructuredFileTransport(log_path)

        event = LogEvent(
            level=LogLevel.INFO,
            category=LogCategory.PHASE,
            message="Test",
        )
        transport.write(event)

        assert log_path.exists()


class TestFileTransportAtomicWrites:
    """Tests for atomic write behavior with file locking."""

    def test_raw_transport_uses_file_locking(self, tmp_path: Path) -> None:
        """RawFileTransport uses file locking for concurrent safety."""
        log_path = tmp_path / "raw.log"
        transport = RawFileTransport(log_path)

        # Write multiple events concurrently
        events_written = []
        threads = []

        def write_event(i: int) -> None:
            event = LogEvent(
                level=LogLevel.INFO,
                category=LogCategory.PHASE,
                message=f"Concurrent message {i}",
            )
            transport.write(event)
            events_written.append(i)

        for i in range(10):
            t = threading.Thread(target=write_event, args=(i,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        # All events should be written
        lines = log_path.read_text().strip().split("\n")
        assert len(lines) == 10

    def test_structured_transport_uses_file_locking(self, tmp_path: Path) -> None:
        """StructuredFileTransport uses file locking for concurrent safety."""
        log_path = tmp_path / "logs.jsonl"
        transport = StructuredFileTransport(log_path)

        threads = []

        def write_event(i: int) -> None:
            event = LogEvent(
                level=LogLevel.INFO,
                category=LogCategory.PHASE,
                message=f"Concurrent {i}",
            )
            transport.write(event)

        for i in range(10):
            t = threading.Thread(target=write_event, args=(i,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        # All events should be valid JSON
        lines = log_path.read_text().strip().split("\n")
        assert len(lines) == 10
        for line in lines:
            json.loads(line)  # Should not raise


class TestFileTransportAllLevels:
    """Tests for handling all log levels."""

    @pytest.mark.parametrize("level", list(LogLevel))
    def test_raw_transport_handles_all_levels(
        self, tmp_path: Path, level: LogLevel
    ) -> None:
        """RawFileTransport handles all log levels."""
        log_path = tmp_path / "raw.log"
        transport = RawFileTransport(log_path)

        event = LogEvent(
            level=level,
            category=LogCategory.PHASE,
            message=f"Message at {level.value}",
        )
        transport.write(event)

        content = log_path.read_text()
        assert f"Message at {level.value}" in content

    @pytest.mark.parametrize("level", list(LogLevel))
    def test_structured_transport_handles_all_levels(
        self, tmp_path: Path, level: LogLevel
    ) -> None:
        """StructuredFileTransport handles all log levels."""
        log_path = tmp_path / "logs.jsonl"
        transport = StructuredFileTransport(log_path)

        event = LogEvent(
            level=level,
            category=LogCategory.PHASE,
            message=f"Message at {level.value}",
        )
        transport.write(event)

        content = log_path.read_text().strip()
        parsed = json.loads(content)
        assert parsed["level"] == level.value
