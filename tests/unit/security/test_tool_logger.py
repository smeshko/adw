"""Unit tests for ToolLogger."""

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from adw.models.security import ToolCallLog
from adw.security import ToolLogger


@pytest.fixture
def temp_run_dir(tmp_path: Path) -> Path:
    """Create a temporary run directory."""
    run_dir = tmp_path / ".adw" / "runs" / "test123"
    return run_dir


class TestToolLogger:
    """Tests for ToolLogger class."""

    def test_creates_run_directory(self, temp_run_dir: Path) -> None:
        """Test that logger creates the run directory."""
        assert not temp_run_dir.exists()
        logger = ToolLogger(temp_run_dir)
        assert temp_run_dir.exists()

    def test_log_tool_call(self, temp_run_dir: Path) -> None:
        """Test logging a tool call entry."""
        logger = ToolLogger(temp_run_dir)
        
        entry = ToolCallLog(
            timestamp=datetime(2026, 1, 3, 10, 30, 0, tzinfo=timezone.utc),
            tool_name="Bash",
            arguments={"command": "ls -la"},
            result_summary="success",
            duration_ms=150,
        )
        logger.log_tool_call(entry)
        
        # Verify file exists and has content
        assert logger.log_file.exists()
        content = logger.log_file.read_text()
        assert "Bash" in content
        assert "ls -la" in content

    def test_log_convenience_method(self, temp_run_dir: Path) -> None:
        """Test the convenience log method."""
        logger = ToolLogger(temp_run_dir)
        
        logger.log(
            tool_name="Read",
            arguments={"file_path": "/tmp/test.txt"},
            result_summary="success",
            duration_ms=50,
        )
        
        assert logger.log_file.exists()
        content = logger.log_file.read_text()
        assert "Read" in content

    def test_log_blocked_call(self, temp_run_dir: Path) -> None:
        """Test logging a blocked tool call."""
        logger = ToolLogger(temp_run_dir)
        
        logger.log(
            tool_name="Bash",
            arguments={"command": "rm -rf /"},
            result_summary="blocked",
            duration_ms=0,
            blocked=True,
            block_reason="Matches dangerous pattern",
        )
        
        content = logger.log_file.read_text()
        assert '"blocked": true' in content or '"blocked":true' in content
        assert "dangerous pattern" in content

    def test_multiple_entries_jsonl_format(self, temp_run_dir: Path) -> None:
        """Test that multiple entries are written as JSONL."""
        logger = ToolLogger(temp_run_dir)
        
        for i in range(3):
            logger.log(
                tool_name=f"Tool{i}",
                arguments={"arg": i},
                result_summary="success",
                duration_ms=i * 10,
            )
        
        # Verify JSONL format (one JSON object per line)
        lines = logger.log_file.read_text().strip().split("\n")
        assert len(lines) == 3
        
        for i, line in enumerate(lines):
            data = json.loads(line)
            assert data["tool_name"] == f"Tool{i}"

    def test_read_entries(self, temp_run_dir: Path) -> None:
        """Test reading entries from log file."""
        logger = ToolLogger(temp_run_dir)
        
        # Write some entries
        for i in range(3):
            logger.log(
                tool_name=f"Tool{i}",
                arguments={"arg": i},
                result_summary="success",
                duration_ms=i * 10,
            )
        
        # Read them back
        entries = logger.read_entries()
        assert len(entries) == 3
        assert entries[0].tool_name == "Tool0"
        assert entries[2].tool_name == "Tool2"

    def test_read_entries_empty_file(self, temp_run_dir: Path) -> None:
        """Test reading from non-existent log file."""
        logger = ToolLogger(temp_run_dir)
        entries = logger.read_entries()
        assert entries == []

    def test_get_log_path(self, temp_run_dir: Path) -> None:
        """Test getting the log file path."""
        logger = ToolLogger(temp_run_dir)
        log_path = logger.get_log_path()
        assert log_path == temp_run_dir / "tools.jsonl"
