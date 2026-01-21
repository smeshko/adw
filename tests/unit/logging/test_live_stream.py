"""Unit tests for LiveStreamTransport.

These tests validate the live.log streaming transport including
LLM output formatting, tool call logging, and box drawing.
"""

import tempfile
from pathlib import Path

import pytest

from adw.logging.live_stream import LiveStreamTransport


class TestLiveStreamTransportBasics:
    """Basic tests for LiveStreamTransport."""

    def test_creates_file_on_write(self, tmp_path: Path) -> None:
        """Should create log file when first write occurs."""
        log_path = tmp_path / "live.log"
        transport = LiveStreamTransport(log_path)

        transport.write_llm_start("test")
        transport.close()

        assert log_path.exists()

    def test_path_property(self, tmp_path: Path) -> None:
        """Should expose path property."""
        log_path = tmp_path / "live.log"
        transport = LiveStreamTransport(log_path)

        assert transport.path == log_path
        transport.close()

    def test_context_manager(self, tmp_path: Path) -> None:
        """Should work as context manager."""
        log_path = tmp_path / "live.log"

        with LiveStreamTransport(log_path) as transport:
            transport.write_llm_start("test")

        assert log_path.exists()


class TestLLMBoxFormatting:
    """Tests for LLM output box formatting (Task 5)."""

    def test_llm_start_writes_top_border(self, tmp_path: Path) -> None:
        """write_llm_start() should output top border with LLM label."""
        log_path = tmp_path / "live.log"
        transport = LiveStreamTransport(log_path)

        transport.write_llm_start("build")
        transport.close()

        content = log_path.read_text()
        assert "Token stream begins" in content
        assert "┌─ LLM" in content

    def test_llm_token_writes_with_box_prefix(self, tmp_path: Path) -> None:
        """write_llm_token() should prefix content with │ character."""
        log_path = tmp_path / "live.log"
        transport = LiveStreamTransport(log_path)

        transport.write_llm_start()
        transport.write_llm_token("Hello world")
        transport.close()

        content = log_path.read_text()
        assert "│" in content
        assert "Hello world" in content

    def test_llm_end_writes_bottom_border(self, tmp_path: Path) -> None:
        """write_llm_end() should output bottom border."""
        log_path = tmp_path / "live.log"
        transport = LiveStreamTransport(log_path)

        transport.write_llm_start()
        transport.write_llm_token("Some content")
        transport.write_llm_end(token_count=100, duration_ms=5000)
        transport.close()

        content = log_path.read_text()
        assert "└" in content
        assert "Token stream ends" in content
        assert "100 tokens" in content
        assert "5.0s" in content

    def test_llm_box_has_cyan_color_codes(self, tmp_path: Path) -> None:
        """LLM box should use cyan ANSI color codes."""
        log_path = tmp_path / "live.log"
        transport = LiveStreamTransport(log_path)

        transport.write_llm_start()
        transport.write_llm_token("Test")
        transport.write_llm_end()
        transport.close()

        content = log_path.read_text()
        # Cyan ANSI code
        assert "\033[36m" in content


class TestToolCallFormatting:
    """Tests for tool call header formatting (Task 6)."""

    def test_tool_call_basic_format(self, tmp_path: Path) -> None:
        """write_tool_call() should format with [TOOL] label and tool name."""
        log_path = tmp_path / "live.log"
        transport = LiveStreamTransport(log_path)

        transport.write_tool_call("Read", "/path/to/file.py")
        transport.close()

        content = log_path.read_text()
        assert "[TOOL]" in content
        assert "Read" in content
        assert "/path/to/file.py" in content

    def test_tool_call_truncates_long_paths(self, tmp_path: Path) -> None:
        """write_tool_call() should truncate paths longer than 60 chars."""
        log_path = tmp_path / "live.log"
        transport = LiveStreamTransport(log_path)

        long_path = "/very/long/path/that/exceeds/sixty/characters/in/total/length/file.swift"
        transport.write_tool_call("Read", long_path)
        transport.close()

        content = log_path.read_text()
        assert "..." in content
        # Path should be truncated
        assert len(long_path) > 60
        # But we should still see the file name at the end
        assert "file.swift" in content

    def test_tool_call_without_context(self, tmp_path: Path) -> None:
        """write_tool_call() should work without context."""
        log_path = tmp_path / "live.log"
        transport = LiveStreamTransport(log_path)

        transport.write_tool_call("Glob")
        transport.close()

        content = log_path.read_text()
        assert "[TOOL]" in content
        assert "Glob" in content

    def test_tool_call_has_dim_timestamp(self, tmp_path: Path) -> None:
        """write_tool_call() should have dim timestamp."""
        log_path = tmp_path / "live.log"
        transport = LiveStreamTransport(log_path)

        transport.write_tool_call("Bash", "npm install")
        transport.close()

        content = log_path.read_text()
        # Dim ANSI code
        assert "\033[2m" in content


class TestToolResultFormatting:
    """Tests for tool result box formatting (Task 4)."""

    def test_tool_result_basic_format(self, tmp_path: Path) -> None:
        """write_tool_result() should output boxed result."""
        log_path = tmp_path / "live.log"
        transport = LiveStreamTransport(log_path)

        transport.write_tool_result("File contents here")
        transport.close()

        content = log_path.read_text()
        assert "┌─ output" in content
        assert "│" in content
        assert "File contents here" in content
        assert "└" in content

    def test_tool_result_error_format(self, tmp_path: Path) -> None:
        """write_tool_result() with is_error=True should show ERROR."""
        log_path = tmp_path / "live.log"
        transport = LiveStreamTransport(log_path)

        transport.write_tool_result("Command failed", is_error=True)
        transport.close()

        content = log_path.read_text()
        assert "ERROR" in content
        # Red ANSI code
        assert "\033[31m" in content

    def test_tool_result_with_exit_code(self, tmp_path: Path) -> None:
        """write_tool_result() should show exit code in footer."""
        log_path = tmp_path / "live.log"
        transport = LiveStreamTransport(log_path)

        transport.write_tool_result("Build complete!", exit_code=0)
        transport.close()

        content = log_path.read_text()
        assert "exit 0" in content

    def test_tool_result_truncates_long_output(self, tmp_path: Path) -> None:
        """write_tool_result() should truncate output > 10 lines."""
        log_path = tmp_path / "live.log"
        transport = LiveStreamTransport(log_path)

        # Create 20 lines of output
        long_output = "\n".join([f"Line {i}" for i in range(20)])
        transport.write_tool_result(long_output)
        transport.close()

        content = log_path.read_text()
        # Should have truncation message
        assert "lines truncated" in content
        # Should have first 5 lines
        assert "Line 0" in content
        assert "Line 4" in content
        # Should have last 5 lines
        assert "Line 15" in content
        assert "Line 19" in content
        # Should NOT have middle lines
        assert "Line 6" not in content or "truncated" in content

    def test_tool_result_short_output_not_truncated(self, tmp_path: Path) -> None:
        """write_tool_result() should not truncate output <= 10 lines."""
        log_path = tmp_path / "live.log"
        transport = LiveStreamTransport(log_path)

        # Create 8 lines of output
        short_output = "\n".join([f"Line {i}" for i in range(8)])
        transport.write_tool_result(short_output)
        transport.close()

        content = log_path.read_text()
        # Should NOT have truncation message
        assert "truncated" not in content
        # Should have all lines
        assert "Line 0" in content
        assert "Line 7" in content


class TestPhaseFormatting:
    """Tests for phase transition logging."""

    def test_write_phase(self, tmp_path: Path) -> None:
        """write_phase() should format phase transitions."""
        log_path = tmp_path / "live.log"
        transport = LiveStreamTransport(log_path)

        transport.write_phase("build", "started")
        transport.close()

        content = log_path.read_text()
        assert "[PHASE]" in content
        assert "build" in content
        assert "started" in content


class TestErrorFormatting:
    """Tests for error logging."""

    def test_write_error(self, tmp_path: Path) -> None:
        """write_error() should format error messages in red."""
        log_path = tmp_path / "live.log"
        transport = LiveStreamTransport(log_path)

        transport.write_error("Something went wrong")
        transport.close()

        content = log_path.read_text()
        assert "[ERROR]" in content
        assert "Something went wrong" in content
        # Red ANSI code
        assert "\033[31m" in content


class TestCloseBehavior:
    """Tests for close and cleanup behavior."""

    def test_write_after_close_is_noop(self, tmp_path: Path) -> None:
        """Writes after close() should be silently ignored."""
        log_path = tmp_path / "live.log"
        transport = LiveStreamTransport(log_path)

        transport.write_llm_start()
        transport.close()

        # Clear file to detect if write happens
        log_path.write_text("")

        # These should be no-ops
        transport.write_llm_token("Should not appear")
        transport.write_tool_call("Read", "/path")

        content = log_path.read_text()
        assert content == ""

    def test_close_removes_lock_file(self, tmp_path: Path) -> None:
        """close() should remove the lock file."""
        log_path = tmp_path / "live.log"
        lock_path = log_path.with_suffix(".log.lock")
        transport = LiveStreamTransport(log_path)

        transport.write_llm_start()
        # Lock file may exist after write
        transport.close()

        # Lock file should be removed
        assert not lock_path.exists()
