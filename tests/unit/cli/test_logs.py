"""Unit tests for logs CLI commands.

Tests for log viewing commands:
- logs export: Create shareable bundles
- logs state: Display run state
- logs follow: Stream real-time output

Tests for helper functions:
- _parse_log_line: Parse structured log lines
- _strip_ansi: Remove ANSI codes
"""

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from adw.cli.app import app
from adw.models.logging import LogCategory, LogContext, LogEvent, LogLevel


@pytest.fixture
def runner() -> CliRunner:
    """Create CLI test runner."""
    return CliRunner()


@pytest.fixture
def mock_adw_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Create a mock .adw directory structure."""
    adw_dir = tmp_path / ".adw"
    adw_dir.mkdir(exist_ok=True)
    runs_dir = adw_dir / "runs"
    runs_dir.mkdir(exist_ok=True)
    monkeypatch.chdir(tmp_path)
    return adw_dir


# Standard test run IDs (valid ULID format - Crockford Base32 excludes I, L, O, U)
TEST_RUN_ID = "01HQTESTAB0000000000000001"
TEST_RUN_ID_2 = "01HQTESTAB0000000000000002"


def create_mock_snapshot(
    snapshots_dir: Path,
    sequence: int,
    label: str,
    context: dict[str, Any] | None = None,
) -> Path:
    """Create a mock snapshot file."""
    if context is None:
        context = {"run_id": TEST_RUN_ID, "current_phase": "plan", "status": "running"}

    snapshot_data = {
        "context": context,
        "phase_result": None,
        "timestamp": datetime.now(UTC).isoformat(),
        "label": label,
        "sequence": sequence,
    }

    filename = f"{sequence:03d}_{label}.json"
    path = snapshots_dir / filename
    path.write_text(json.dumps(snapshot_data, indent=2))
    return path


class TestLogsExportCommand:
    """Tests for logs export command - file creation."""

    def test_export_creates_bundle_file(
        self, runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Export creates a bundle file at specified output path."""
        monkeypatch.chdir(tmp_path)

        # Create project structure with logs
        adw_dir = tmp_path / ".adw"
        adw_dir.mkdir(exist_ok=True)
        runs_dir = adw_dir / "runs"
        runs_dir.mkdir(exist_ok=True)

        run_id = "01HQTESTAB0000000000000003"
        run_dir = runs_dir / run_id
        run_dir.mkdir()
        logs_dir = run_dir / "logs"
        logs_dir.mkdir()
        (run_dir / "snapshots").mkdir()
        (run_dir / "llm").mkdir()
        (run_dir / "artifacts").mkdir()

        # Create context.json
        context = {
            "run_id": run_id,
            "feature_description": "Test feature",
            "current_phase": "build",
            "status": "completed",
        }
        (run_dir / "context.json").write_text(json.dumps(context))

        # Create log file
        log_events = [
            LogEvent(
                level=LogLevel.INFO,
                category=LogCategory.PHASE,
                message="Phase plan started",
                context=LogContext(run_id=run_id, phase="plan"),
            ),
        ]
        (logs_dir / "logs.jsonl").write_text(
            "\n".join(e.model_dump_json() for e in log_events)
        )

        output_file = tmp_path / "export.tar.gz"
        result = runner.invoke(
            app, ["logs", "export", run_id, "--output", str(output_file)]
        )
        assert result.exit_code == 0
        assert output_file.exists(), "Export file should be created"
        assert output_file.stat().st_size > 0, "Export file should not be empty"


class TestLogsStateCommand:
    """Tests for logs state command."""

    def test_state_shows_run_context(
        self, runner: CliRunner, mock_adw_dir: Path
    ) -> None:
        """State command displays run context."""
        run_id = "01HQXK5P3Z7V8R2M4N6T9W1Y3C"
        run_dir = mock_adw_dir / "runs" / run_id
        run_dir.mkdir(parents=True)

        # Create context.json
        context = {
            "run_id": run_id,
            "feature_description": "Test feature",
            "current_phase": "build",
            "status": "completed",
        }
        (run_dir / "context.json").write_text(json.dumps(context))
        (run_dir / "snapshots").mkdir()

        result = runner.invoke(app, ["logs", "state", run_id])
        assert result.exit_code == 0
        assert "build" in result.output.lower() or "completed" in result.output.lower()

    def test_state_run_not_found(self, runner: CliRunner, mock_adw_dir: Path) -> None:
        """State command returns error for non-existent run."""
        result = runner.invoke(app, ["logs", "state", "01HQXK5P3Z7V8R2M4N6T9W1Y3C"])
        assert result.exit_code == 1
        assert "not found" in result.output.lower()


class TestParseLogLine:
    """Tests for _parse_log_line helper function."""

    def test_parse_valid_log_line(self) -> None:
        """Test parsing a valid structured log line."""
        from adw.cli.logs import _parse_log_line

        line = "[2024-01-15 10:30:45] [PHASE] Starting plan phase"
        result = _parse_log_line(line)
        assert result is not None
        timestamp, category, content = result
        assert timestamp == "2024-01-15 10:30:45"
        assert category == "PHASE"
        assert content == "Starting plan phase"

    def test_parse_tool_log_line(self) -> None:
        """Test parsing a TOOL category log line."""
        from adw.cli.logs import _parse_log_line

        line = "[2024-01-15 10:30:46] [TOOL] Read: /src/main.py"
        result = _parse_log_line(line)
        assert result is not None
        timestamp, category, content = result
        assert category == "TOOL"
        assert content == "Read: /src/main.py"

    def test_parse_llm_log_line(self) -> None:
        """Test parsing an LLM category log line."""
        from adw.cli.logs import _parse_log_line

        line = "[2024-01-15 10:30:47] [LLM] ▶ Token stream begins"
        result = _parse_log_line(line)
        assert result is not None
        timestamp, category, content = result
        assert category == "LLM"
        assert "Token stream begins" in content

    def test_parse_unstructured_line_returns_none(self) -> None:
        """Test that unstructured lines return None."""
        from adw.cli.logs import _parse_log_line

        line = "This is just plain text without structure"
        result = _parse_log_line(line)
        assert result is None

    def test_parse_llm_streaming_content_returns_none(self) -> None:
        """Test that LLM streaming content (no brackets) returns None."""
        from adw.cli.logs import _parse_log_line

        line = "I'm analyzing your codebase..."
        result = _parse_log_line(line)
        assert result is None

    def test_parse_line_with_trailing_whitespace(self) -> None:
        """Test parsing handles trailing whitespace."""
        from adw.cli.logs import _parse_log_line

        line = "[2024-01-15 10:30:45] [INFO] Some message  \n"
        result = _parse_log_line(line)
        assert result is not None
        timestamp, category, content = result
        assert category == "INFO"

    def test_parse_line_with_embedded_ansi_codes(self) -> None:
        """Test parsing strips ANSI codes before matching."""
        from adw.cli.logs import _parse_log_line

        # Real log line with ANSI color codes embedded
        line = "[2024-01-15 10:30:46] \x1b[33m[TOOL]\x1b[0m \x1b[1mRead\x1b[0m: /src/main.py"
        result = _parse_log_line(line)
        assert result is not None
        timestamp, category, content = result
        assert timestamp == "2024-01-15 10:30:46"
        assert category == "TOOL"
        assert content == "Read: /src/main.py"

    def test_parse_line_extracts_component_from_content(self) -> None:
        """Test parsing extracts [COMPONENT] from content when present."""
        from adw.cli.logs import _parse_log_line

        # Format: [timestamp] [INFO] [PHASE] message - should use PHASE as category
        line = "[2024-01-15 10:30:45] [INFO] [PHASE] {run=01KEVKB9} Starting run"
        result = _parse_log_line(line)
        assert result is not None
        timestamp, category, content = result
        assert timestamp == "2024-01-15 10:30:45"
        assert category == "PHASE"  # Should extract PHASE, not INFO
        assert content == "{run=01KEVKB9} Starting run"

    def test_parse_line_keeps_category_for_unknown_component(self) -> None:
        """Test parsing keeps original category if component is not known."""
        from adw.cli.logs import _parse_log_line

        # Format: [timestamp] [INFO] [UNKNOWN] message - UNKNOWN not in PANEL_COLORS
        line = "[2024-01-15 10:30:45] [INFO] [CUSTOM] Some message"
        result = _parse_log_line(line)
        assert result is not None
        timestamp, category, content = result
        assert timestamp == "2024-01-15 10:30:45"
        assert category == "INFO"  # Keeps INFO since CUSTOM is not known
        assert content == "[CUSTOM] Some message"  # Content unchanged


class TestStripAnsi:
    """Tests for _strip_ansi helper function."""

    def test_strip_ansi_codes(self) -> None:
        """Test removing ANSI escape codes from text."""
        from adw.cli.logs import _strip_ansi

        # Text with ANSI color codes
        colored = "\x1b[32mGreen text\x1b[0m"
        result = _strip_ansi(colored)
        assert result == "Green text"

    def test_strip_multiple_ansi_codes(self) -> None:
        """Test removing multiple ANSI codes."""
        from adw.cli.logs import _strip_ansi

        colored = "\x1b[1m\x1b[34mBold blue\x1b[0m normal"
        result = _strip_ansi(colored)
        assert result == "Bold blue normal"

    def test_strip_ansi_no_codes(self) -> None:
        """Test that text without ANSI codes is unchanged."""
        from adw.cli.logs import _strip_ansi

        plain = "Just plain text"
        result = _strip_ansi(plain)
        assert result == plain

    def test_strip_ansi_preserves_unicode(self) -> None:
        """Test that unicode characters are preserved."""
        from adw.cli.logs import _strip_ansi

        text = "\x1b[33m▶ Token stream begins\x1b[0m"
        result = _strip_ansi(text)
        assert result == "▶ Token stream begins"
