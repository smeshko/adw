"""Unit tests for logs CLI commands.

REDUCTION: Removed 46 tests (was 57, now 11 tests)
- Deleted: help text verification tests (6)
- Deleted: "requires argument" tests (8)
- Deleted: smoke tests with no meaningful assertions (22)
- Deleted: weak output text checks (10)
- Kept: tests verifying actual business logic (filtering, parsing, error handling)

Tests for state inspection commands (Story 7.5):
- logs snapshots: List snapshots for a run
- logs diff: Show state differences

Tests for log viewing commands (Story 7.4):
- logs export: Create shareable bundles

Tests for run ID validation (ISS-003):
- ULID format validation
- Fuzzy matching suggestions
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


class TestLogsSnapshotsCommand:
    """Tests for logs snapshots command - ordering logic."""

    def test_snapshots_lists_all_in_order(
        self, runner: CliRunner, mock_adw_dir: Path
    ) -> None:
        """Lists all snapshots in correct sequence order."""
        run_dir = mock_adw_dir / "runs" / TEST_RUN_ID
        run_dir.mkdir(parents=True)
        snapshots_dir = run_dir / "snapshots"
        snapshots_dir.mkdir()

        # Create snapshots out of order
        create_mock_snapshot(snapshots_dir, 3, "pre_build")
        create_mock_snapshot(snapshots_dir, 1, "pre_plan")
        create_mock_snapshot(snapshots_dir, 2, "post_plan")

        result = runner.invoke(app, ["logs", "snapshots", TEST_RUN_ID])
        assert result.exit_code == 0

        # Verify all snapshots shown
        assert "pre_plan" in result.output
        assert "post_plan" in result.output
        assert "pre_build" in result.output

        # Verify order (sequence numbers should appear in order)
        output = result.output
        pos_1 = output.find("1")
        pos_2 = output.find("2")
        pos_3 = output.find("3")
        assert pos_1 < pos_2 < pos_3, "Snapshots should be listed in sequence order"


class TestLogsDiffCommand:
    """Tests for logs diff command - diff detection logic."""

    def test_diff_detects_additions(
        self, runner: CliRunner, mock_adw_dir: Path
    ) -> None:
        """Diff correctly identifies added fields."""
        run_dir = mock_adw_dir / "runs" / TEST_RUN_ID
        run_dir.mkdir(parents=True)
        snapshots_dir = run_dir / "snapshots"
        snapshots_dir.mkdir()

        # Create snapshots with differences
        create_mock_snapshot(
            snapshots_dir,
            1,
            "pre_plan",
            {"run_id": TEST_RUN_ID, "status": "running"},
        )
        create_mock_snapshot(
            snapshots_dir,
            2,
            "post_plan",
            {"run_id": TEST_RUN_ID, "status": "running", "new_field": "added_value"},
        )

        result = runner.invoke(
            app,
            ["logs", "diff", TEST_RUN_ID, "--from-snapshot", "1", "--to-snapshot", "2"],
        )
        assert result.exit_code == 0
        # Should show the addition
        assert "new_field" in result.output or "added_value" in result.output

    def test_diff_detects_removals(self, runner: CliRunner, mock_adw_dir: Path) -> None:
        """Diff correctly identifies removed fields."""
        run_dir = mock_adw_dir / "runs" / TEST_RUN_ID
        run_dir.mkdir(parents=True)
        snapshots_dir = run_dir / "snapshots"
        snapshots_dir.mkdir()

        create_mock_snapshot(
            snapshots_dir,
            1,
            "pre_plan",
            {"run_id": TEST_RUN_ID, "status": "running", "old_field": "removed_value"},
        )
        create_mock_snapshot(
            snapshots_dir,
            2,
            "post_plan",
            {"run_id": TEST_RUN_ID, "status": "running"},
        )

        result = runner.invoke(
            app,
            ["logs", "diff", TEST_RUN_ID, "--from-snapshot", "1", "--to-snapshot", "2"],
        )
        assert result.exit_code == 0
        # Should show the removal
        assert "old_field" in result.output or "removed_value" in result.output


class TestLogsToolsCommand:
    """Tests for logs tools command - filtering and truncation logic."""

    def test_verbose_truncates_arguments_over_60_chars(
        self, runner: CliRunner, mock_adw_dir: Path
    ) -> None:
        """--verbose flag truncates arguments longer than 60 characters."""
        run_dir = mock_adw_dir / "runs" / TEST_RUN_ID
        run_dir.mkdir(parents=True)

        # Create an argument string that exceeds 60 characters
        long_path = "/src/" + "a" * 80 + "/file.py"  # Well over 60 chars
        tools_file = run_dir / "tools.jsonl"
        entry = {
            "timestamp": "2026-01-03T10:30:00.123Z",
            "tool_name": "Read",
            "arguments": {"file_path": long_path},
            "result_summary": "Success",
            "duration_ms": 10,
            "blocked": False,
            "block_reason": None,
            "phase": "plan",
        }
        tools_file.write_text(json.dumps(entry) + "\n")

        result = runner.invoke(app, ["logs", "tools", TEST_RUN_ID, "--verbose"])
        assert result.exit_code == 0
        # Should be truncated (Rich uses "..." or ellipsis)
        assert "..." in result.output or "…" in result.output
        # Full path should NOT appear (truncated)
        assert long_path not in result.output

    def test_blocked_only_filters_to_blocked_calls(
        self, runner: CliRunner, mock_adw_dir: Path
    ) -> None:
        """--blocked-only flag correctly filters to only blocked calls."""
        run_dir = mock_adw_dir / "runs" / TEST_RUN_ID
        run_dir.mkdir(parents=True)

        tools_file = run_dir / "tools.jsonl"
        entries = [
            {
                "timestamp": "2026-01-03T10:30:00.123Z",
                "tool_name": "ReadTool",  # Unique name to verify filtering
                "arguments": {},
                "result_summary": "Success",
                "duration_ms": 10,
                "blocked": False,
                "block_reason": None,
                "phase": None,
            },
            {
                "timestamp": "2026-01-03T10:30:01.000Z",
                "tool_name": "BlockedBash",  # Unique name
                "arguments": {"command": "rm -rf /"},
                "result_summary": None,
                "duration_ms": 0,
                "blocked": True,
                "block_reason": "Dangerous",
                "phase": None,
            },
        ]
        tools_file.write_text("\n".join(json.dumps(e) for e in entries) + "\n")

        result = runner.invoke(app, ["logs", "tools", TEST_RUN_ID, "--blocked-only"])
        assert result.exit_code == 0
        # Blocked call should appear (may be truncated in table display)
        assert "Bloc" in result.output  # BlockedBash may be truncated
        # Non-blocked ReadTool should NOT appear
        assert "Read" not in result.output


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


class TestRunIdValidation:
    """Tests for run ID validation logic (ISS-003)."""

    def test_valid_ulid_proceeds_to_run_lookup(
        self, runner: CliRunner, mock_adw_dir: Path
    ) -> None:
        """Valid ULID format should proceed to run lookup (not format error)."""
        # Valid 26-character ULID that doesn't exist
        result = runner.invoke(app, ["logs", "show", "01HQXK5P3Z7V8R2M4N6T9W1Y3C"])
        assert result.exit_code == 1
        # Should get "Run not found" error, not "Invalid format"
        assert "Invalid run ID format" not in result.output
        assert "not found" in result.output.lower()

    def test_fuzzy_match_suggests_similar_runs(
        self, runner: CliRunner, mock_adw_dir: Path
    ) -> None:
        """Similar run IDs should be suggested when run not found."""
        # Create a run with a known ID
        run_dir = mock_adw_dir / "runs" / "01HQXK5P3Z7V8R2M4N6T9W1Y3C"
        run_dir.mkdir(parents=True)
        (run_dir / "context.json").write_text(
            '{"run_id": "01HQXK5P3Z7V8R2M4N6T9W1Y3C"}'
        )

        # Search with similar but wrong ID (same prefix, different last char)
        result = runner.invoke(app, ["logs", "show", "01HQXK5P3Z7V8R2M4N6T9W1Y3D"])
        assert result.exit_code == 1
        # Should suggest the similar run
        assert (
            "Did you mean" in result.output
            or "01HQXK5P3Z7V8R2M4N6T9W1Y3C" in result.output
        )

    def test_run_exists_but_no_logs_graceful_handling(
        self, runner: CliRunner, mock_adw_dir: Path
    ) -> None:
        """Run directory exists but no logs should show helpful message, not error."""
        run_id = "01HQXK5P3Z7V8R2M4N6T9W1Y3C"
        run_dir = mock_adw_dir / "runs" / run_id
        run_dir.mkdir(parents=True)
        (run_dir / "context.json").write_text(
            f'{{"run_id": "{run_id}", "status": "running"}}'
        )
        (run_dir / "logs").mkdir()

        result = runner.invoke(app, ["logs", "show", run_id])
        assert result.exit_code == 0
        assert "No log entries" in result.output or "no log" in result.output.lower()

    def test_typo_in_run_id_suggests_correct_run(
        self, runner: CliRunner, mock_adw_dir: Path
    ) -> None:
        """Run ID with typo suggests the correct run via fuzzy matching."""
        # Create a real run
        real_run_id = "01HQXK5P3Z7V8R2M4N6T9W1Y3C"
        run_dir = mock_adw_dir / "runs" / real_run_id
        run_dir.mkdir(parents=True)
        (run_dir / "context.json").write_text(f'{{"run_id": "{real_run_id}"}}')

        # Try with wrong last character (D instead of C)
        wrong_run_id = "01HQXK5P3Z7V8R2M4N6T9W1Y3D"
        result = runner.invoke(app, ["logs", "show", wrong_run_id])

        assert result.exit_code == 1
        assert "Did you mean" in result.output
        assert real_run_id in result.output


class TestLogsIntegration:
    """Integration tests for complete workflows."""

    def test_complete_run_id_lookup_workflow(
        self, runner: CliRunner, mock_adw_dir: Path
    ) -> None:
        """Complete workflow: create run, add logs, view logs successfully."""
        run_id = "01HQXK5P3Z7V8R2M4N6T9W1Y3C"
        run_dir = mock_adw_dir / "runs" / run_id
        run_dir.mkdir(parents=True)

        # Create complete run structure
        (run_dir / "context.json").write_text(
            json.dumps(
                {
                    "run_id": run_id,
                    "status": "completed",
                    "current_phase": "build",
                }
            )
        )

        logs_dir = run_dir / "logs"
        logs_dir.mkdir()

        # Add log entries
        log_events = [
            LogEvent(
                level=LogLevel.INFO,
                category=LogCategory.PHASE,
                message="Phase plan started",
                context=LogContext(run_id=run_id, phase="plan"),
            ),
            LogEvent(
                level=LogLevel.INFO,
                category=LogCategory.PHASE,
                message="Phase plan completed",
                context=LogContext(run_id=run_id, phase="plan"),
            ),
        ]
        (logs_dir / "logs.jsonl").write_text(
            "\n".join(e.model_dump_json() for e in log_events)
        )

        # View logs should work and show content
        result = runner.invoke(app, ["logs", "show", run_id])
        assert result.exit_code == 0
        assert "plan" in result.output.lower()


# =============================================================================
# Story ISS-007: Tool Execution Log Context and Duration
# =============================================================================


class TestToolContextExtraction:
    """Tests for _extract_tool_context helper function."""

    def test_extract_tool_context_read(self) -> None:
        """Test context extraction for Read tool."""
        from adw.cli.logs import _extract_tool_context

        args = {"file_path": "/very/long/path/to/some/file.py"}
        ctx = _extract_tool_context("Read", args)
        assert ctx == "/very/long/path/to/some/file.py"

    def test_extract_tool_context_read_truncates_long_path(self) -> None:
        """Test context extraction truncates long file paths."""
        from adw.cli.logs import _extract_tool_context

        long_path = "/a" * 50 + "/file.py"
        args = {"file_path": long_path}
        ctx = _extract_tool_context("Read", args)
        assert len(ctx) <= 40
        assert ctx.endswith("...")

    def test_extract_tool_context_write(self) -> None:
        """Test context extraction for Write tool."""
        from adw.cli.logs import _extract_tool_context

        args = {"file_path": "/src/main.py"}
        ctx = _extract_tool_context("Write", args)
        assert ctx == "/src/main.py"

    def test_extract_tool_context_bash(self) -> None:
        """Test context extraction for Bash tool."""
        from adw.cli.logs import _extract_tool_context

        args = {"command": "npm run build && npm test"}
        ctx = _extract_tool_context("Bash", args)
        assert "npm run build" in ctx

    def test_extract_tool_context_bash_truncates_long_command(self) -> None:
        """Test context extraction truncates long bash commands."""
        from adw.cli.logs import _extract_tool_context

        long_cmd = "npm run build && npm test && npm lint && npm format"
        args = {"command": long_cmd}
        ctx = _extract_tool_context("Bash", args)
        assert len(ctx) <= 40
        assert ctx.endswith("...")

    def test_extract_tool_context_glob(self) -> None:
        """Test context extraction for Glob tool."""
        from adw.cli.logs import _extract_tool_context

        args = {"pattern": "**/*.py"}
        ctx = _extract_tool_context("Glob", args)
        assert ctx == "**/*.py"

    def test_extract_tool_context_grep_with_path(self) -> None:
        """Test context extraction for Grep tool with path."""
        from adw.cli.logs import _extract_tool_context

        args = {"pattern": "def test_", "path": "tests/"}
        ctx = _extract_tool_context("Grep", args)
        assert "def test_" in ctx
        assert "tests/" in ctx

    def test_extract_tool_context_grep_without_path(self) -> None:
        """Test context extraction for Grep tool without path."""
        from adw.cli.logs import _extract_tool_context

        args = {"pattern": "class MyClass"}
        ctx = _extract_tool_context("Grep", args)
        assert ctx == "class MyClass"

    def test_extract_tool_context_task_with_subagent(self) -> None:
        """Test context extraction for Task tool with subagent_type."""
        from adw.cli.logs import _extract_tool_context

        args = {"subagent_type": "Explore", "prompt": "Find auth code"}
        ctx = _extract_tool_context("Task", args)
        assert ctx == "Explore"

    def test_extract_tool_context_task_with_description(self) -> None:
        """Test context extraction for Task tool with description only."""
        from adw.cli.logs import _extract_tool_context

        args = {"description": "Search for patterns"}
        ctx = _extract_tool_context("Task", args)
        assert ctx == "Search for patterns"

    def test_extract_tool_context_edit(self) -> None:
        """Test context extraction for Edit tool."""
        from adw.cli.logs import _extract_tool_context

        args = {"file_path": "/src/models/user.py"}
        ctx = _extract_tool_context("Edit", args)
        assert ctx == "/src/models/user.py"

    def test_extract_tool_context_unknown_tool(self) -> None:
        """Test context extraction falls back for unknown tools."""
        from adw.cli.logs import _extract_tool_context

        args = {"some_key": "some_value"}
        ctx = _extract_tool_context("UnknownTool", args)
        assert ctx == "some_value"

    def test_extract_tool_context_empty_args(self) -> None:
        """Test context extraction returns dash for empty args."""
        from adw.cli.logs import _extract_tool_context

        ctx = _extract_tool_context("Read", {})
        # Returns empty string for file_path when not present
        assert ctx == ""


class TestTruncateHelper:
    """Tests for _truncate helper function."""

    def test_truncate_short_text(self) -> None:
        """Test truncate doesn't modify short text."""
        from adw.cli.logs import _truncate

        result = _truncate("short", 10)
        assert result == "short"

    def test_truncate_exact_length(self) -> None:
        """Test truncate doesn't modify text at exact length."""
        from adw.cli.logs import _truncate

        result = _truncate("exactly10c", 10)
        assert result == "exactly10c"

    def test_truncate_long_text(self) -> None:
        """Test truncate adds ellipsis for long text."""
        from adw.cli.logs import _truncate

        result = _truncate("this is a very long string", 20)
        assert result == "this is a very lo..."
        assert len(result) == 20

    def test_truncate_preserves_max_length(self) -> None:
        """Test truncated text never exceeds max_len."""
        from adw.cli.logs import _truncate

        for max_len in [10, 20, 40]:
            result = _truncate("x" * 100, max_len)
            assert len(result) <= max_len


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


class TestDurationDisplay:
    """Tests for duration display with tilde prefix."""

    def test_duration_estimate_indicator_in_display(self) -> None:
        """Verify duration display includes tilde to indicate estimate."""
        from io import StringIO

        from rich.console import Console

        from adw.cli.logs import _display_tool_summary
        from adw.models.security import ToolCallLog

        # Capture console output
        output = StringIO()
        console = Console(file=output, force_terminal=True)

        # Mock console.print temporarily
        import adw.cli.logs as logs_module

        original_console = logs_module.console
        logs_module.console = console

        try:
            entry = ToolCallLog(
                timestamp="2024-01-01T10:00:00.000000+00:00",
                tool_name="Read",
                arguments={"file_path": "/test.py"},
                result_summary="Success",
                duration_ms=100,
                blocked=False,
                block_reason=None,
                phase="plan",
            )
            _display_tool_summary([entry])
        finally:
            logs_module.console = original_console

        output_text = output.getvalue()
        assert "~100ms" in output_text
        assert "estimates" in output_text.lower()
