"""Tests for CLI evidence file writer.

Tests the EvidenceFileWriter class that writes command results to files.
"""

from datetime import datetime, timezone
from pathlib import Path

import pytest

from adw.evidence.file_writer import EvidenceFileWriter
from adw.models.evidence import CommandResult


class TestEvidenceFileWriter:
    """Tests for EvidenceFileWriter class."""

    def test_init_creates_directory(self, tmp_path: Path) -> None:
        """EvidenceFileWriter should create evidence directory."""
        evidence_dir = tmp_path / "evidence" / "cli"
        writer = EvidenceFileWriter(evidence_dir)

        assert evidence_dir.exists()
        assert writer.evidence_dir == evidence_dir

    def test_init_with_existing_directory(self, tmp_path: Path) -> None:
        """EvidenceFileWriter should work with existing directory."""
        evidence_dir = tmp_path / "evidence" / "cli"
        evidence_dir.mkdir(parents=True)

        writer = EvidenceFileWriter(evidence_dir)

        assert evidence_dir.exists()
        assert writer.evidence_dir == evidence_dir


class TestWriteCommandResult:
    """Tests for write_command_result method."""

    def test_write_successful_result(self, tmp_path: Path) -> None:
        """write_command_result should create file with correct format."""
        evidence_dir = tmp_path / "evidence" / "cli"
        writer = EvidenceFileWriter(evidence_dir)

        result = CommandResult(
            command="adw --version",
            exit_code=0,
            stdout="adw version 1.0.0\n",
            stderr="",
            duration_seconds=0.125,
            success=True,
            executed_at=datetime(2026, 1, 3, 10, 30, 45, tzinfo=timezone.utc),
        )

        output_path = writer.write_command_result("version", result)

        assert output_path.exists()
        assert output_path.name == "version.txt"

        content = output_path.read_text()
        assert "COMMAND EVIDENCE" in content
        assert "Command: adw --version" in content
        assert "Exit Code: 0" in content
        assert "Status: PASSED" in content
        assert "Duration: 0.125s" in content
        assert "STDOUT" in content
        assert "adw version 1.0.0" in content
        assert "STDERR" in content

    def test_write_failed_result(self, tmp_path: Path) -> None:
        """write_command_result should mark failed commands."""
        evidence_dir = tmp_path / "evidence" / "cli"
        writer = EvidenceFileWriter(evidence_dir)

        result = CommandResult(
            command="invalid-cmd",
            exit_code=127,
            stdout="",
            stderr="command not found: invalid-cmd\n",
            duration_seconds=0.05,
            success=False,
            executed_at=datetime(2026, 1, 3, 10, 30, 45, tzinfo=timezone.utc),
        )

        output_path = writer.write_command_result("invalid", result)

        content = output_path.read_text()
        assert "Exit Code: 127" in content
        assert "Status: FAILED" in content
        assert "command not found" in content

    def test_write_result_with_stderr(self, tmp_path: Path) -> None:
        """write_command_result should capture stderr."""
        evidence_dir = tmp_path / "evidence" / "cli"
        writer = EvidenceFileWriter(evidence_dir)

        result = CommandResult(
            command="cmd-with-warnings",
            exit_code=0,
            stdout="output\n",
            stderr="warning: something\n",
            duration_seconds=0.1,
            success=True,
            executed_at=datetime(2026, 1, 3, 10, 30, 45, tzinfo=timezone.utc),
        )

        output_path = writer.write_command_result("warnings", result)

        content = output_path.read_text()
        assert "STDOUT" in content
        assert "output" in content
        assert "STDERR" in content
        assert "warning: something" in content

    def test_write_result_empty_output(self, tmp_path: Path) -> None:
        """write_command_result should handle empty stdout/stderr."""
        evidence_dir = tmp_path / "evidence" / "cli"
        writer = EvidenceFileWriter(evidence_dir)

        result = CommandResult(
            command="silent-cmd",
            exit_code=0,
            stdout="",
            stderr="",
            duration_seconds=0.01,
            success=True,
            executed_at=datetime(2026, 1, 3, 10, 30, 45, tzinfo=timezone.utc),
        )

        output_path = writer.write_command_result("silent", result)

        content = output_path.read_text()
        assert "(empty)" in content

    def test_write_timeout_result(self, tmp_path: Path) -> None:
        """write_command_result should handle timeout."""
        evidence_dir = tmp_path / "evidence" / "cli"
        writer = EvidenceFileWriter(evidence_dir)

        result = CommandResult(
            command="sleep 100",
            exit_code=-1,
            stdout="",
            stderr="Command timed out",
            duration_seconds=30.0,
            success=False,
            executed_at=datetime(2026, 1, 3, 10, 30, 45, tzinfo=timezone.utc),
        )

        output_path = writer.write_command_result("timeout", result)

        content = output_path.read_text()
        assert "Exit Code: -1" in content
        assert "Status: FAILED" in content
        assert "timed out" in content

    def test_write_multiple_results(self, tmp_path: Path) -> None:
        """write_command_result should handle multiple results."""
        evidence_dir = tmp_path / "evidence" / "cli"
        writer = EvidenceFileWriter(evidence_dir)

        result1 = CommandResult(
            command="echo a",
            exit_code=0,
            stdout="a\n",
            stderr="",
            duration_seconds=0.01,
            success=True,
        )
        result2 = CommandResult(
            command="echo b",
            exit_code=0,
            stdout="b\n",
            stderr="",
            duration_seconds=0.01,
            success=True,
        )

        path1 = writer.write_command_result("cmd1", result1)
        path2 = writer.write_command_result("cmd2", result2)

        assert path1.exists()
        assert path2.exists()
        assert path1.name == "cmd1.txt"
        assert path2.name == "cmd2.txt"


class TestFormatEvidenceFile:
    """Tests for evidence file formatting."""

    def test_header_format(self, tmp_path: Path) -> None:
        """Evidence file should have correct header format."""
        evidence_dir = tmp_path / "evidence" / "cli"
        writer = EvidenceFileWriter(evidence_dir)

        result = CommandResult(
            command="test-cmd",
            exit_code=0,
            stdout="ok",
            stderr="",
            duration_seconds=0.5,
            success=True,
            executed_at=datetime(2026, 1, 3, 10, 30, 45, tzinfo=timezone.utc),
        )

        output_path = writer.write_command_result("test", result)
        content = output_path.read_text()

        # Check for section separators
        assert "=" * 80 in content

        # Check for header section
        lines = content.split("\n")
        assert any("COMMAND EVIDENCE" in line for line in lines)
        assert any("Command:" in line for line in lines)
        assert any("Executed:" in line for line in lines)
        assert any("Duration:" in line for line in lines)
        assert any("Exit Code:" in line for line in lines)
        assert any("Status:" in line for line in lines)
