"""Tests for ToolLogger class.

Tests for the ToolLogger that handles JSONL logging of tool execution events.
"""

import json
import threading
from pathlib import Path

import pytest

from adw.models.security import ToolCallLog
from adw.security.tool_logger import ToolLogger


class TestToolLoggerInit:
    """Test suite for ToolLogger initialization."""

    def test_init_with_run_dir(self, tmp_path: Path) -> None:
        """Test initializing ToolLogger with run directory."""
        run_dir = tmp_path / "runs" / "test-run-id"
        run_dir.mkdir(parents=True)

        logger = ToolLogger(run_dir)

        assert logger.run_dir == run_dir
        assert logger.log_path == run_dir / "tools.jsonl"

    def test_init_creates_log_path(self, tmp_path: Path) -> None:
        """Test that log_path points to correct file."""
        run_dir = tmp_path / "runs" / "test-run"
        run_dir.mkdir(parents=True)

        logger = ToolLogger(run_dir)

        assert logger.log_path.name == "tools.jsonl"
        assert logger.log_path.parent == run_dir


class TestToolLoggerWrite:
    """Test suite for ToolLogger.log_tool_call()."""

    def test_log_single_tool_call(self, tmp_path: Path) -> None:
        """Test logging a single tool call."""
        run_dir = tmp_path / "runs" / "test-run"
        run_dir.mkdir(parents=True)

        logger = ToolLogger(run_dir)
        entry = ToolCallLog(
            timestamp="2026-01-03T10:30:00.123Z",
            tool_name="Bash",
            arguments={"command": "npm test"},
            result_summary="Exit code: 0",
            duration_ms=2500,
            phase="build",
        )

        logger.log_tool_call(entry)

        # Verify file was created and contains the entry
        assert logger.log_path.exists()
        content = logger.log_path.read_text()
        assert "Bash" in content
        assert "npm test" in content

    def test_log_multiple_tool_calls(self, tmp_path: Path) -> None:
        """Test logging multiple tool calls appends to file."""
        run_dir = tmp_path / "runs" / "test-run"
        run_dir.mkdir(parents=True)

        logger = ToolLogger(run_dir)

        entries = [
            ToolCallLog(
                timestamp="2026-01-03T10:30:00.000Z",
                tool_name="Read",
                arguments={"file_path": "/src/main.py"},
                result_summary="File read",
                duration_ms=10,
            ),
            ToolCallLog(
                timestamp="2026-01-03T10:30:01.000Z",
                tool_name="Write",
                arguments={"file_path": "/src/test.py"},
                result_summary="File written",
                duration_ms=5,
            ),
            ToolCallLog(
                timestamp="2026-01-03T10:30:02.000Z",
                tool_name="Bash",
                arguments={"command": "pytest"},
                result_summary="Tests passed",
                duration_ms=3000,
            ),
        ]

        for entry in entries:
            logger.log_tool_call(entry)

        # Verify all entries are in file
        lines = logger.log_path.read_text().strip().split("\n")
        assert len(lines) == 3

        # Verify each line is valid JSON
        for i, line in enumerate(lines):
            data = json.loads(line)
            assert data["tool_name"] == entries[i].tool_name

    def test_log_blocked_tool_call(self, tmp_path: Path) -> None:
        """Test logging a blocked tool call."""
        run_dir = tmp_path / "runs" / "test-run"
        run_dir.mkdir(parents=True)

        logger = ToolLogger(run_dir)
        entry = ToolCallLog(
            timestamp="2026-01-03T10:30:00.123Z",
            tool_name="Bash",
            arguments={"command": "rm -rf /"},
            result_summary=None,
            duration_ms=0,
            blocked=True,
            block_reason="Dangerous command pattern detected",
            phase="build",
        )

        logger.log_tool_call(entry)

        content = logger.log_path.read_text()
        data = json.loads(content.strip())
        assert data["blocked"] is True
        assert data["block_reason"] == "Dangerous command pattern detected"

    def test_creates_parent_directories(self, tmp_path: Path) -> None:
        """Test that log_tool_call creates parent directories."""
        run_dir = tmp_path / "runs" / "new-run"
        # Don't create directory - let ToolLogger create it

        logger = ToolLogger(run_dir)
        entry = ToolCallLog(
            timestamp="2026-01-03T10:30:00.123Z",
            tool_name="Read",
            duration_ms=5,
        )

        logger.log_tool_call(entry)

        assert run_dir.exists()
        assert logger.log_path.exists()


class TestToolLoggerRead:
    """Test suite for ToolLogger.get_tool_history()."""

    def test_get_empty_history(self, tmp_path: Path) -> None:
        """Test getting history when no logs exist."""
        run_dir = tmp_path / "runs" / "empty-run"
        run_dir.mkdir(parents=True)

        logger = ToolLogger(run_dir)
        history = logger.get_tool_history()

        assert history == []

    def test_get_single_entry_history(self, tmp_path: Path) -> None:
        """Test getting history with single entry."""
        run_dir = tmp_path / "runs" / "test-run"
        run_dir.mkdir(parents=True)

        logger = ToolLogger(run_dir)
        entry = ToolCallLog(
            timestamp="2026-01-03T10:30:00.123Z",
            tool_name="Bash",
            arguments={"command": "npm test"},
            result_summary="Exit code: 0",
            duration_ms=2500,
        )
        logger.log_tool_call(entry)

        history = logger.get_tool_history()

        assert len(history) == 1
        assert history[0].tool_name == "Bash"
        assert history[0].duration_ms == 2500

    def test_get_multiple_entries_history(self, tmp_path: Path) -> None:
        """Test getting history with multiple entries."""
        run_dir = tmp_path / "runs" / "test-run"
        run_dir.mkdir(parents=True)

        logger = ToolLogger(run_dir)
        for i in range(5):
            entry = ToolCallLog(
                timestamp=f"2026-01-03T10:30:0{i}.000Z",
                tool_name=f"Tool{i}",
                duration_ms=i * 100,
            )
            logger.log_tool_call(entry)

        history = logger.get_tool_history()

        assert len(history) == 5
        for i, log in enumerate(history):
            assert log.tool_name == f"Tool{i}"
            assert log.duration_ms == i * 100

    def test_get_history_preserves_order(self, tmp_path: Path) -> None:
        """Test that history preserves chronological order."""
        run_dir = tmp_path / "runs" / "test-run"
        run_dir.mkdir(parents=True)

        logger = ToolLogger(run_dir)
        tool_names = ["Read", "Bash", "Write", "Grep", "Glob"]
        for name in tool_names:
            entry = ToolCallLog(
                timestamp="2026-01-03T10:30:00.123Z",
                tool_name=name,
                duration_ms=10,
            )
            logger.log_tool_call(entry)

        history = logger.get_tool_history()

        for i, log in enumerate(history):
            assert log.tool_name == tool_names[i]


class TestToolLoggerStaticRead:
    """Test suite for static get_tool_history_for_run()."""

    def test_get_history_for_run_id(self, tmp_path: Path) -> None:
        """Test getting history by run ID."""
        runs_dir = tmp_path / ".adw" / "runs"
        run_id = "01HQXK5P3Z"
        run_dir = runs_dir / run_id
        run_dir.mkdir(parents=True)

        # Write some entries
        logger = ToolLogger(run_dir)
        entry = ToolCallLog(
            timestamp="2026-01-03T10:30:00.123Z",
            tool_name="Bash",
            duration_ms=100,
        )
        logger.log_tool_call(entry)

        # Read using static method
        history = ToolLogger.get_tool_history_for_run(runs_dir, run_id)

        assert len(history) == 1
        assert history[0].tool_name == "Bash"

    def test_get_history_for_nonexistent_run(self, tmp_path: Path) -> None:
        """Test getting history for non-existent run returns empty."""
        runs_dir = tmp_path / ".adw" / "runs"
        runs_dir.mkdir(parents=True)

        history = ToolLogger.get_tool_history_for_run(runs_dir, "nonexistent")

        assert history == []


class TestToolLoggerThreadSafety:
    """Test suite for thread safety of ToolLogger."""

    def test_concurrent_writes(self, tmp_path: Path) -> None:
        """Test concurrent writes from multiple threads."""
        run_dir = tmp_path / "runs" / "concurrent-test"
        run_dir.mkdir(parents=True)

        logger = ToolLogger(run_dir)
        num_threads = 10
        entries_per_thread = 20
        results: list[bool] = []

        def write_entries(thread_id: int) -> None:
            try:
                for i in range(entries_per_thread):
                    entry = ToolCallLog(
                        timestamp="2026-01-03T10:30:00.123Z",
                        tool_name=f"Thread{thread_id}_Tool{i}",
                        duration_ms=thread_id * 100 + i,
                    )
                    logger.log_tool_call(entry)
                results.append(True)
            except Exception:
                results.append(False)

        threads = [
            threading.Thread(target=write_entries, args=(i,))
            for i in range(num_threads)
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All threads should complete successfully
        assert all(results)
        assert len(results) == num_threads

        # Verify all entries were written
        history = logger.get_tool_history()
        assert len(history) == num_threads * entries_per_thread


class TestToolLoggerCleanup:
    """Test suite for ToolLogger cleanup operations."""

    def test_close_removes_lock_file(self, tmp_path: Path) -> None:
        """Test that close() removes lock file."""
        run_dir = tmp_path / "runs" / "test-run"
        run_dir.mkdir(parents=True)

        logger = ToolLogger(run_dir)
        entry = ToolCallLog(
            timestamp="2026-01-03T10:30:00.123Z",
            tool_name="Test",
            duration_ms=10,
        )
        logger.log_tool_call(entry)

        # Lock file might exist
        lock_path = logger.log_path.with_suffix(".jsonl.lock")

        logger.close()

        # Lock file should be cleaned up
        assert not lock_path.exists()

    def test_context_manager(self, tmp_path: Path) -> None:
        """Test using ToolLogger as context manager."""
        run_dir = tmp_path / "runs" / "test-run"
        run_dir.mkdir(parents=True)

        with ToolLogger(run_dir) as logger:
            entry = ToolCallLog(
                timestamp="2026-01-03T10:30:00.123Z",
                tool_name="Test",
                duration_ms=10,
            )
            logger.log_tool_call(entry)

        # Verify entry was written
        assert (run_dir / "tools.jsonl").exists()
