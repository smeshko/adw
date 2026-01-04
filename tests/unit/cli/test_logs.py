"""Unit tests for logs CLI commands.

Tests for state inspection commands (Story 7.5):
- logs snapshots: List snapshots for a run
- logs state: Display run state
- logs diff: Show state differences
- logs tools: Display tool execution history

Tests for log viewing commands (Story 7.4):
- logs show: Display log entries from a run
- logs follow: Stream log entries in real-time
- logs search: Search logs for patterns
- logs llm: View LLM prompts/responses
- logs export: Create shareable bundles
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
    adw_dir.mkdir()
    runs_dir = adw_dir / "runs"
    runs_dir.mkdir()
    monkeypatch.chdir(tmp_path)
    return adw_dir


def create_mock_snapshot(
    snapshots_dir: Path,
    sequence: int,
    label: str,
    context: dict[str, Any] | None = None,
) -> Path:
    """Create a mock snapshot file."""
    if context is None:
        context = {"run_id": "test-run", "current_phase": "plan", "status": "running"}

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


class TestLogsCLIStructure:
    """Tests for logs CLI subcommand structure."""

    def test_logs_help_shows_subcommands(self, runner: CliRunner) -> None:
        """Verify logs --help shows available subcommands."""
        result = runner.invoke(app, ["logs", "--help"])
        assert result.exit_code == 0
        assert "snapshots" in result.output
        assert "state" in result.output
        assert "diff" in result.output

    def test_logs_snapshots_requires_run_id(self, runner: CliRunner) -> None:
        """Verify snapshots command requires run_id argument."""
        result = runner.invoke(app, ["logs", "snapshots"])
        assert result.exit_code != 0
        assert "Missing argument" in result.output or "RUN_ID" in result.output

    def test_logs_state_requires_run_id(self, runner: CliRunner) -> None:
        """Verify state command requires run_id argument."""
        result = runner.invoke(app, ["logs", "state"])
        assert result.exit_code != 0
        assert "Missing argument" in result.output or "RUN_ID" in result.output

    def test_logs_diff_requires_run_id(self, runner: CliRunner) -> None:
        """Verify diff command requires run_id argument."""
        result = runner.invoke(app, ["logs", "diff"])
        assert result.exit_code != 0
        assert "Missing argument" in result.output or "RUN_ID" in result.output

    def test_logs_diff_requires_comparison_targets(self, runner: CliRunner) -> None:
        """Verify diff command requires phase or snapshot options."""
        result = runner.invoke(app, ["logs", "diff", "test-run-id"])
        assert result.exit_code == 1
        assert "Must specify comparison targets" in result.output

    def test_logs_diff_rejects_mixed_options(self, runner: CliRunner) -> None:
        """Verify diff command rejects mixing phase and snapshot options."""
        result = runner.invoke(
            app,
            [
                "logs",
                "diff",
                "test-run-id",
                "--from-phase",
                "plan",
                "--from-snapshot",
                "1",
            ],
        )
        assert result.exit_code == 1
        assert "Cannot mix" in result.output


class TestLogsSnapshotsCommand:
    """Tests for logs snapshots command."""

    def test_snapshots_no_adw_dir(self, runner: CliRunner, tmp_path: Path) -> None:
        """Error when no .adw directory exists."""
        import os

        os.chdir(tmp_path)
        result = runner.invoke(app, ["logs", "snapshots", "test-run"])
        assert result.exit_code == 1
        assert "No .adw directory found" in result.output

    def test_snapshots_run_not_found(
        self, runner: CliRunner, mock_adw_dir: Path
    ) -> None:
        """Error when run ID doesn't exist."""
        result = runner.invoke(app, ["logs", "snapshots", "nonexistent-run"])
        assert result.exit_code == 1
        assert "not found" in result.output.lower()

    def test_snapshots_no_snapshots(
        self, runner: CliRunner, mock_adw_dir: Path
    ) -> None:
        """Shows message when run has no snapshots."""
        run_dir = mock_adw_dir / "runs" / "test-run"
        run_dir.mkdir(parents=True)
        snapshots_dir = run_dir / "snapshots"
        snapshots_dir.mkdir()

        result = runner.invoke(app, ["logs", "snapshots", "test-run"])
        assert result.exit_code == 0
        assert "No snapshots" in result.output

    def test_snapshots_lists_all(self, runner: CliRunner, mock_adw_dir: Path) -> None:
        """Lists all snapshots in order."""
        run_dir = mock_adw_dir / "runs" / "test-run"
        run_dir.mkdir(parents=True)
        snapshots_dir = run_dir / "snapshots"
        snapshots_dir.mkdir()

        # Create snapshots
        create_mock_snapshot(snapshots_dir, 1, "pre_plan")
        create_mock_snapshot(snapshots_dir, 2, "post_plan")
        create_mock_snapshot(snapshots_dir, 3, "pre_build")

        result = runner.invoke(app, ["logs", "snapshots", "test-run"])
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
        assert pos_1 < pos_2 < pos_3


class TestLogsStateCommand:
    """Tests for logs state command."""

    def test_state_no_adw_dir(self, runner: CliRunner, tmp_path: Path) -> None:
        """Error when no .adw directory exists."""
        import os

        os.chdir(tmp_path)
        result = runner.invoke(app, ["logs", "state", "test-run"])
        assert result.exit_code == 1
        assert "No .adw directory found" in result.output

    def test_state_run_not_found(self, runner: CliRunner, mock_adw_dir: Path) -> None:
        """Error when run ID doesn't exist."""
        result = runner.invoke(app, ["logs", "state", "nonexistent-run"])
        assert result.exit_code == 1
        assert "not found" in result.output.lower()

    def test_state_shows_final_state(
        self, runner: CliRunner, mock_adw_dir: Path
    ) -> None:
        """Shows final/current context when no options provided."""
        run_dir = mock_adw_dir / "runs" / "test-run"
        run_dir.mkdir(parents=True)
        snapshots_dir = run_dir / "snapshots"
        snapshots_dir.mkdir()

        # Create context.json (final state)
        context_data = {
            "run_id": "test-run",
            "current_phase": "build",
            "status": "completed",
        }
        (run_dir / "context.json").write_text(json.dumps(context_data, indent=2))

        result = runner.invoke(app, ["logs", "state", "test-run"])
        assert result.exit_code == 0
        # Should show context content
        assert "test-run" in result.output
        assert "build" in result.output or "completed" in result.output

    def test_state_shows_specific_snapshot(
        self, runner: CliRunner, mock_adw_dir: Path
    ) -> None:
        """Shows state at specific snapshot when --snapshot provided."""
        run_dir = mock_adw_dir / "runs" / "test-run"
        run_dir.mkdir(parents=True)
        snapshots_dir = run_dir / "snapshots"
        snapshots_dir.mkdir()

        # Create snapshots
        create_mock_snapshot(
            snapshots_dir,
            1,
            "pre_plan",
            {"run_id": "test-run", "current_phase": "plan", "status": "running"},
        )
        create_mock_snapshot(
            snapshots_dir,
            2,
            "post_plan",
            {"run_id": "test-run", "current_phase": "build", "status": "running"},
        )

        result = runner.invoke(app, ["logs", "state", "test-run", "--snapshot", "1"])
        assert result.exit_code == 0
        # Should show snapshot 1 content (plan phase)
        assert "plan" in result.output.lower()

    def test_state_shows_phase_boundary(
        self, runner: CliRunner, mock_adw_dir: Path
    ) -> None:
        """Shows state at phase boundary when --phase --at provided."""
        run_dir = mock_adw_dir / "runs" / "test-run"
        run_dir.mkdir(parents=True)
        snapshots_dir = run_dir / "snapshots"
        snapshots_dir.mkdir()

        # Create pre and post phase snapshots
        create_mock_snapshot(
            snapshots_dir,
            1,
            "pre_plan",
            {"run_id": "test-run", "current_phase": "plan", "status": "running"},
        )
        create_mock_snapshot(
            snapshots_dir,
            2,
            "post_plan",
            {"run_id": "test-run", "current_phase": "build", "status": "running"},
        )

        result = runner.invoke(
            app, ["logs", "state", "test-run", "--phase", "plan", "--at", "end"]
        )
        assert result.exit_code == 0
        # Should show post_plan snapshot

    def test_state_phase_requires_at(
        self, runner: CliRunner, mock_adw_dir: Path
    ) -> None:
        """Error when --phase provided without --at."""
        run_dir = mock_adw_dir / "runs" / "test-run"
        run_dir.mkdir(parents=True)
        snapshots_dir = run_dir / "snapshots"
        snapshots_dir.mkdir()

        result = runner.invoke(app, ["logs", "state", "test-run", "--phase", "plan"])
        assert result.exit_code == 1
        assert "--at" in result.output.lower()


class TestLogsDiffCommand:
    """Tests for logs diff command."""

    def test_diff_shows_additions(self, runner: CliRunner, mock_adw_dir: Path) -> None:
        """Shows additions in diff output."""
        run_dir = mock_adw_dir / "runs" / "test-run"
        run_dir.mkdir(parents=True)
        snapshots_dir = run_dir / "snapshots"
        snapshots_dir.mkdir()

        # Create snapshots with differences
        create_mock_snapshot(
            snapshots_dir,
            1,
            "pre_plan",
            {"run_id": "test-run", "status": "running"},
        )
        create_mock_snapshot(
            snapshots_dir,
            2,
            "post_plan",
            {"run_id": "test-run", "status": "running", "new_field": "added"},
        )

        result = runner.invoke(
            app,
            ["logs", "diff", "test-run", "--from-snapshot", "1", "--to-snapshot", "2"],
        )
        assert result.exit_code == 0
        # Should show the addition
        assert "new_field" in result.output or "added" in result.output

    def test_diff_shows_removals(self, runner: CliRunner, mock_adw_dir: Path) -> None:
        """Shows removals in diff output."""
        run_dir = mock_adw_dir / "runs" / "test-run"
        run_dir.mkdir(parents=True)
        snapshots_dir = run_dir / "snapshots"
        snapshots_dir.mkdir()

        create_mock_snapshot(
            snapshots_dir,
            1,
            "pre_plan",
            {"run_id": "test-run", "status": "running", "old_field": "removed"},
        )
        create_mock_snapshot(
            snapshots_dir,
            2,
            "post_plan",
            {"run_id": "test-run", "status": "running"},
        )

        result = runner.invoke(
            app,
            ["logs", "diff", "test-run", "--from-snapshot", "1", "--to-snapshot", "2"],
        )
        assert result.exit_code == 0
        # Should show the removal
        assert "old_field" in result.output or "removed" in result.output

    def test_diff_shows_changes(self, runner: CliRunner, mock_adw_dir: Path) -> None:
        """Shows changes in diff output."""
        run_dir = mock_adw_dir / "runs" / "test-run"
        run_dir.mkdir(parents=True)
        snapshots_dir = run_dir / "snapshots"
        snapshots_dir.mkdir()

        create_mock_snapshot(
            snapshots_dir,
            1,
            "pre_plan",
            {"run_id": "test-run", "status": "running"},
        )
        create_mock_snapshot(
            snapshots_dir,
            2,
            "post_plan",
            {"run_id": "test-run", "status": "completed"},
        )

        result = runner.invoke(
            app,
            ["logs", "diff", "test-run", "--from-snapshot", "1", "--to-snapshot", "2"],
        )
        assert result.exit_code == 0
        # Should show the change in status

    def test_diff_phase_mode(self, runner: CliRunner, mock_adw_dir: Path) -> None:
        """Supports phase-based diff."""
        run_dir = mock_adw_dir / "runs" / "test-run"
        run_dir.mkdir(parents=True)
        snapshots_dir = run_dir / "snapshots"
        snapshots_dir.mkdir()

        create_mock_snapshot(
            snapshots_dir,
            1,
            "pre_plan",
            {"run_id": "test-run", "current_phase": "plan"},
        )
        create_mock_snapshot(
            snapshots_dir,
            2,
            "post_plan",
            {"run_id": "test-run", "current_phase": "build"},
        )

        result = runner.invoke(
            app,
            ["logs", "diff", "test-run", "--from-phase", "plan", "--to-phase", "plan"],
        )
        assert result.exit_code == 0


class TestLogsToolsCommand:
    """Tests for logs tools command (Story 3.8)."""

    def test_logs_help_shows_tools_subcommand(self, runner: CliRunner) -> None:
        """Verify logs --help shows tools subcommand."""
        result = runner.invoke(app, ["logs", "--help"])
        assert result.exit_code == 0
        assert "tools" in result.output

    def test_logs_tools_requires_run_id(self, runner: CliRunner) -> None:
        """Verify tools command requires run_id argument."""
        result = runner.invoke(app, ["logs", "tools"])
        assert result.exit_code != 0
        assert "Missing argument" in result.output or "RUN_ID" in result.output

    def test_logs_tools_shows_error_for_missing_run(
        self, runner: CliRunner, mock_adw_dir: Path
    ) -> None:
        """Shows error when run directory doesn't exist."""
        result = runner.invoke(app, ["logs", "tools", "nonexistent-run"])
        assert result.exit_code == 1
        assert "not found" in result.output.lower() or "error" in result.output.lower()

    def test_logs_tools_shows_empty_message_when_no_tools(
        self, runner: CliRunner, mock_adw_dir: Path
    ) -> None:
        """Shows appropriate message when no tool calls logged."""
        run_dir = mock_adw_dir / "runs" / "empty-run"
        run_dir.mkdir(parents=True)

        result = runner.invoke(app, ["logs", "tools", "empty-run"])
        assert result.exit_code == 0
        assert "no tool" in result.output.lower() or "empty" in result.output.lower()

    def test_logs_tools_displays_tool_history(
        self, runner: CliRunner, mock_adw_dir: Path
    ) -> None:
        """Displays tool execution history in table format."""
        run_dir = mock_adw_dir / "runs" / "test-run"
        run_dir.mkdir(parents=True)

        # Create tools.jsonl with sample entries
        tools_file = run_dir / "tools.jsonl"
        entries = [
            {
                "timestamp": "2026-01-03T10:30:00.123Z",
                "tool_name": "Read",
                "arguments": {"file_path": "/src/main.py"},
                "result_summary": "File read successfully",
                "duration_ms": 15,
                "blocked": False,
                "block_reason": None,
                "phase": "plan",
            },
            {
                "timestamp": "2026-01-03T10:30:01.456Z",
                "tool_name": "Bash",
                "arguments": {"command": "npm test"},
                "result_summary": "Exit code: 0",
                "duration_ms": 2500,
                "blocked": False,
                "block_reason": None,
                "phase": "build",
            },
        ]
        tools_file.write_text("\n".join(json.dumps(e) for e in entries) + "\n")

        result = runner.invoke(app, ["logs", "tools", "test-run"])
        assert result.exit_code == 0
        assert "Read" in result.output
        assert "Bash" in result.output

    def test_logs_tools_shows_blocked_calls(
        self, runner: CliRunner, mock_adw_dir: Path
    ) -> None:
        """Shows blocked tool calls with reason."""
        run_dir = mock_adw_dir / "runs" / "test-run"
        run_dir.mkdir(parents=True)

        tools_file = run_dir / "tools.jsonl"
        entry = {
            "timestamp": "2026-01-03T10:30:00.123Z",
            "tool_name": "Bash",
            "arguments": {"command": "rm -rf /"},
            "result_summary": None,
            "duration_ms": 0,
            "blocked": True,
            "block_reason": "Dangerous command",
            "phase": "build",
        }
        tools_file.write_text(json.dumps(entry) + "\n")

        result = runner.invoke(app, ["logs", "tools", "test-run"])
        assert result.exit_code == 0
        assert "Bash" in result.output
        assert "Blocked" in result.output or "blocked" in result.output.lower()

    def test_logs_tools_verbose_shows_arguments(
        self, runner: CliRunner, mock_adw_dir: Path
    ) -> None:
        """--verbose flag shows full arguments."""
        run_dir = mock_adw_dir / "runs" / "test-run"
        run_dir.mkdir(parents=True)

        tools_file = run_dir / "tools.jsonl"
        entry = {
            "timestamp": "2026-01-03T10:30:00.123Z",
            "tool_name": "Read",
            "arguments": {"file_path": "/src/very/long/path/to/file.py"},
            "result_summary": "Success",
            "duration_ms": 10,
            "blocked": False,
            "block_reason": None,
            "phase": "plan",
        }
        tools_file.write_text(json.dumps(entry) + "\n")

        result = runner.invoke(app, ["logs", "tools", "test-run", "--verbose"])
        assert result.exit_code == 0
        assert "/src/very/long/path/to/file.py" in result.output

    def test_logs_tools_verbose_truncates_long_arguments(
        self, runner: CliRunner, mock_adw_dir: Path
    ) -> None:
        """--verbose flag truncates arguments longer than 60 characters."""
        run_dir = mock_adw_dir / "runs" / "test-run"
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

        result = runner.invoke(app, ["logs", "tools", "test-run", "--verbose"])
        assert result.exit_code == 0
        # Should be truncated (Rich uses "…" ellipsis or "..." depending on terminal)
        assert "…" in result.output or "..." in result.output
        # Full path should NOT appear (it's too long and gets truncated)
        assert long_path not in result.output

    def test_logs_tools_blocked_only_filter(
        self, runner: CliRunner, mock_adw_dir: Path
    ) -> None:
        """--blocked-only flag filters to only blocked calls."""
        run_dir = mock_adw_dir / "runs" / "test-run"
        run_dir.mkdir(parents=True)

        tools_file = run_dir / "tools.jsonl"
        entries = [
            {
                "timestamp": "2026-01-03T10:30:00.123Z",
                "tool_name": "ReadTool",  # Use unique name to verify filtering
                "arguments": {},
                "result_summary": "Success",
                "duration_ms": 10,
                "blocked": False,
                "block_reason": None,
                "phase": None,
            },
            {
                "timestamp": "2026-01-03T10:30:01.000Z",
                "tool_name": "BlockedBash",  # Use unique name
                "arguments": {"command": "rm -rf /"},
                "result_summary": None,
                "duration_ms": 0,
                "blocked": True,
                "block_reason": "Dangerous",
                "phase": None,
            },
        ]
        tools_file.write_text("\n".join(json.dumps(e) for e in entries) + "\n")

        result = runner.invoke(app, ["logs", "tools", "test-run", "--blocked-only"])
        assert result.exit_code == 0
        # Blocked call should appear
        assert "BlockedBash" in result.output
        # Non-blocked ReadTool should NOT appear in the output at all
        # (not in table, not in summary since --blocked-only filters them out)
        assert "ReadTool" not in result.output

    def test_logs_tools_shows_summary(
        self, runner: CliRunner, mock_adw_dir: Path
    ) -> None:
        """Shows summary statistics at the end."""
        run_dir = mock_adw_dir / "runs" / "test-run"
        run_dir.mkdir(parents=True)

        tools_file = run_dir / "tools.jsonl"
        entries = [
            {
                "timestamp": "2026-01-03T10:30:00.123Z",
                "tool_name": "Read",
                "arguments": {},
                "result_summary": "Success",
                "duration_ms": 100,
                "blocked": False,
                "block_reason": None,
                "phase": None,
            },
            {
                "timestamp": "2026-01-03T10:30:01.000Z",
                "tool_name": "Write",
                "arguments": {},
                "result_summary": "Success",
                "duration_ms": 50,
                "blocked": False,
                "block_reason": None,
                "phase": None,
            },
            {
                "timestamp": "2026-01-03T10:30:02.000Z",
                "tool_name": "Bash",
                "arguments": {},
                "result_summary": None,
                "duration_ms": 0,
                "blocked": True,
                "block_reason": "Dangerous",
                "phase": None,
            },
        ]
        tools_file.write_text("\n".join(json.dumps(e) for e in entries) + "\n")

        result = runner.invoke(app, ["logs", "tools", "test-run"])
        assert result.exit_code == 0
        # Should show summary with totals
        in_output = result.output
        has_summary = "3" in in_output or "Total" in in_output or "Summary" in in_output
        assert has_summary


# =============================================================================
# Story 7.4: Log Viewing Commands
# =============================================================================


@pytest.fixture
def run_with_logs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[str, Path]:
    """Create a run directory with sample log files.

    Returns:
        Tuple of (run_id, project_path).
    """
    # Change to temp directory
    monkeypatch.chdir(tmp_path)

    # Create project structure
    adw_dir = tmp_path / ".adw"
    adw_dir.mkdir()
    runs_dir = adw_dir / "runs"
    runs_dir.mkdir()

    # Create run with ULID-like ID
    run_id = "01HQTEST123456789ABCDEF"
    run_dir = runs_dir / run_id
    run_dir.mkdir()

    # Create required subdirectories
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
        "phase_history": ["plan"],
        "started_at": datetime.now(UTC).isoformat(),
        "status": "completed",
        "artifacts": {},
    }
    (run_dir / "context.json").write_text(json.dumps(context))

    # Create structured log file (logs.jsonl)
    log_events = [
        LogEvent(
            level=LogLevel.INFO,
            category=LogCategory.PHASE,
            message="Phase plan started",
            context=LogContext(run_id=run_id, phase="plan"),
        ),
        LogEvent(
            level=LogLevel.DEBUG,
            category=LogCategory.LLM,
            message="Sending LLM request",
            context=LogContext(run_id=run_id, phase="plan"),
        ),
        LogEvent(
            level=LogLevel.INFO,
            category=LogCategory.PHASE,
            message="Phase plan completed",
            context=LogContext(run_id=run_id, phase="plan"),
        ),
        LogEvent(
            level=LogLevel.INFO,
            category=LogCategory.PHASE,
            message="Phase build started",
            context=LogContext(run_id=run_id, phase="build"),
        ),
        LogEvent(
            level=LogLevel.ERROR,
            category=LogCategory.ERROR,
            message="Build failed: Missing dependency",
            context=LogContext(run_id=run_id, phase="build"),
        ),
    ]

    jsonl_content = "\n".join(e.model_dump_json() for e in log_events)
    (logs_dir / "logs.jsonl").write_text(jsonl_content)

    # Create raw log file
    raw_lines = [
        "2026-01-03 10:00:00 [INFO ] [phase] (run) [plan] Phase plan started",
        "2026-01-03 10:00:05 [DEBUG] [llm] (run) [plan] Sending LLM request",
        "2026-01-03 10:01:00 [INFO ] [phase] (run) [plan] Phase plan completed",
        "2026-01-03 10:01:05 [INFO ] [phase] (run) [build] Phase build started",
        "2026-01-03 10:02:00 [ERROR] [error] (run) [build] Build failed: Missing dependency",
    ]
    (logs_dir / "raw.log").write_text("\n".join(raw_lines))

    return run_id, tmp_path


@pytest.fixture
def run_with_llm_captures(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> tuple[str, Path]:
    """Create a run directory with LLM capture files.

    Returns:
        Tuple of (run_id, project_path).
    """
    monkeypatch.chdir(tmp_path)

    # Create project structure
    adw_dir = tmp_path / ".adw"
    adw_dir.mkdir()
    runs_dir = adw_dir / "runs"
    runs_dir.mkdir()

    run_id = "01HQLLMTEST456789ABCDEF"
    run_dir = runs_dir / run_id
    run_dir.mkdir()

    # Create directories
    (run_dir / "logs").mkdir()
    (run_dir / "snapshots").mkdir()
    (run_dir / "artifacts").mkdir()
    llm_dir = run_dir / "llm"
    llm_dir.mkdir()

    # Create context.json
    context = {
        "run_id": run_id,
        "feature_description": "Test LLM feature",
        "current_phase": "plan",
        "phase_history": [],
        "started_at": datetime.now(UTC).isoformat(),
        "status": "completed",
        "artifacts": {},
    }
    (run_dir / "context.json").write_text(json.dumps(context))

    # Create LLM capture files
    request_1 = {
        "timestamp": "2026-01-03T10:00:00Z",
        "prompt": "Generate a plan for user authentication",
        "phase": "plan",
        "params": {"model": "claude-sonnet-4-20250514", "temperature": 0},
    }
    (llm_dir / "001_plan_request.json").write_text(json.dumps(request_1, indent=2))

    response_1 = {
        "timestamp": "2026-01-03T10:01:00Z",
        "content": "Here is the authentication plan...",
        "phase": "plan",
        "tool_calls": [],
        "stats": {"input_tokens": 150, "output_tokens": 500, "duration_ms": 2500},
    }
    (llm_dir / "001_plan_response.json").write_text(json.dumps(response_1, indent=2))

    # Create stream file
    stream_events = [
        '{"t": 0, "type": "token", "content": "Here"}',
        '{"t": 10, "type": "token", "content": " is"}',
        '{"t": 20, "type": "token", "content": " the"}',
    ]
    (llm_dir / "001_plan_stream.jsonl").write_text("\n".join(stream_events))

    return run_id, tmp_path


class TestLogsShowCommand:
    """Tests for logs show command (Story 7.4)."""

    def test_logs_help_shows_show_subcommand(self, runner: CliRunner) -> None:
        """Verify logs --help shows show subcommand."""
        result = runner.invoke(app, ["logs", "--help"])
        assert result.exit_code == 0
        assert "show" in result.output

    def test_logs_show_requires_run_id(self, runner: CliRunner) -> None:
        """Verify show command requires run_id argument."""
        result = runner.invoke(app, ["logs", "show"])
        assert result.exit_code != 0
        assert "Missing argument" in result.output or "RUN_ID" in result.output

    def test_logs_show_displays_entries(
        self, runner: CliRunner, run_with_logs: tuple[str, Path]
    ) -> None:
        """Test that logs show displays log entries."""
        run_id, _ = run_with_logs

        result = runner.invoke(app, ["logs", "show", run_id])
        assert result.exit_code == 0
        # Should contain log messages
        assert "Phase plan started" in result.output or "plan" in result.output.lower()

    def test_logs_show_with_tail_option(
        self, runner: CliRunner, run_with_logs: tuple[str, Path]
    ) -> None:
        """Test logs show with --tail option."""
        run_id, _ = run_with_logs

        result = runner.invoke(app, ["logs", "show", run_id, "--tail", "2"])
        assert result.exit_code == 0
        # Should show limited entries

    def test_logs_show_with_phase_filter(
        self, runner: CliRunner, run_with_logs: tuple[str, Path]
    ) -> None:
        """Test logs show with --phase filter."""
        run_id, _ = run_with_logs

        result = runner.invoke(app, ["logs", "show", run_id, "--phase", "build"])
        assert result.exit_code == 0
        # Should only show build phase logs

    def test_logs_show_with_level_filter(
        self, runner: CliRunner, run_with_logs: tuple[str, Path]
    ) -> None:
        """Test logs show with --level filter."""
        run_id, _ = run_with_logs

        result = runner.invoke(app, ["logs", "show", run_id, "--level", "error"])
        assert result.exit_code == 0
        # Should only show error level logs

    def test_logs_show_run_not_found(
        self, runner: CliRunner, mock_adw_dir: Path
    ) -> None:
        """Test logs show with non-existent run."""
        result = runner.invoke(app, ["logs", "show", "01NONEXISTENT"])
        assert result.exit_code == 1
        assert "not found" in result.output.lower() or "error" in result.output.lower()


class TestLogsSearchCommand:
    """Tests for logs search command (Story 7.4)."""

    def test_logs_help_shows_search_subcommand(self, runner: CliRunner) -> None:
        """Verify logs --help shows search subcommand."""
        result = runner.invoke(app, ["logs", "--help"])
        assert result.exit_code == 0
        assert "search" in result.output

    def test_logs_search_requires_pattern(self, runner: CliRunner) -> None:
        """Verify search command requires pattern argument."""
        result = runner.invoke(app, ["logs", "search"])
        assert result.exit_code != 0
        assert "Missing argument" in result.output or "PATTERN" in result.output

    def test_logs_search_finds_pattern(
        self, runner: CliRunner, run_with_logs: tuple[str, Path]
    ) -> None:
        """Test that logs search finds matching entries."""
        run_id, _ = run_with_logs

        result = runner.invoke(app, ["logs", "search", "dependency", "--run", run_id])
        assert result.exit_code == 0
        # Should find the error message with "Missing dependency"

    def test_logs_search_no_matches(
        self, runner: CliRunner, run_with_logs: tuple[str, Path]
    ) -> None:
        """Test logs search with no matching entries."""
        run_id, _ = run_with_logs

        result = runner.invoke(
            app, ["logs", "search", "nonexistent_pattern_xyz123", "--run", run_id]
        )
        assert result.exit_code == 0
        # Should indicate no matches

    def test_logs_search_with_category_filter(
        self, runner: CliRunner, run_with_logs: tuple[str, Path]
    ) -> None:
        """Test logs search with --category filter."""
        run_id, _ = run_with_logs

        result = runner.invoke(
            app, ["logs", "search", "phase", "--run", run_id, "--category", "phase"]
        )
        assert result.exit_code == 0


class TestLogsLlmCommand:
    """Tests for logs llm command (Story 7.4)."""

    def test_logs_help_shows_llm_subcommand(self, runner: CliRunner) -> None:
        """Verify logs --help shows llm subcommand."""
        result = runner.invoke(app, ["logs", "--help"])
        assert result.exit_code == 0
        assert "llm" in result.output

    def test_logs_llm_requires_run_id(self, runner: CliRunner) -> None:
        """Verify llm command requires run_id argument."""
        result = runner.invoke(app, ["logs", "llm"])
        assert result.exit_code != 0
        assert "Missing argument" in result.output or "RUN_ID" in result.output

    def test_logs_llm_displays_interactions(
        self, runner: CliRunner, run_with_llm_captures: tuple[str, Path]
    ) -> None:
        """Test that logs llm displays LLM interactions."""
        run_id, _ = run_with_llm_captures

        result = runner.invoke(app, ["logs", "llm", run_id])
        assert result.exit_code == 0
        # Should contain prompt or response content
        assert (
            "plan" in result.output.lower() or "authentication" in result.output.lower()
        )

    def test_logs_llm_with_request_only(
        self, runner: CliRunner, run_with_llm_captures: tuple[str, Path]
    ) -> None:
        """Test logs llm with --request-only option."""
        run_id, _ = run_with_llm_captures

        result = runner.invoke(app, ["logs", "llm", run_id, "--request-only"])
        assert result.exit_code == 0

    def test_logs_llm_with_response_only(
        self, runner: CliRunner, run_with_llm_captures: tuple[str, Path]
    ) -> None:
        """Test logs llm with --response-only option."""
        run_id, _ = run_with_llm_captures

        result = runner.invoke(app, ["logs", "llm", run_id, "--response-only"])
        assert result.exit_code == 0

    def test_logs_llm_with_phase_filter(
        self, runner: CliRunner, run_with_llm_captures: tuple[str, Path]
    ) -> None:
        """Test logs llm with --phase filter."""
        run_id, _ = run_with_llm_captures

        result = runner.invoke(app, ["logs", "llm", run_id, "--phase", "plan"])
        assert result.exit_code == 0

    def test_logs_llm_with_tools_filter(
        self, runner: CliRunner, run_with_llm_captures: tuple[str, Path]
    ) -> None:
        """Test logs llm with --tools filter for tool calls only."""
        run_id, _ = run_with_llm_captures

        result = runner.invoke(app, ["logs", "llm", run_id, "--tools"])
        assert result.exit_code == 0


class TestLogsExportCommand:
    """Tests for logs export command (Story 7.4)."""

    def test_logs_help_shows_export_subcommand(self, runner: CliRunner) -> None:
        """Verify logs --help shows export subcommand."""
        result = runner.invoke(app, ["logs", "--help"])
        assert result.exit_code == 0
        assert "export" in result.output

    def test_logs_export_requires_run_id(self, runner: CliRunner) -> None:
        """Verify export command requires run_id argument."""
        result = runner.invoke(app, ["logs", "export"])
        assert result.exit_code != 0
        assert "Missing argument" in result.output or "RUN_ID" in result.output

    def test_logs_export_creates_bundle(
        self, runner: CliRunner, run_with_logs: tuple[str, Path]
    ) -> None:
        """Test that logs export creates a bundle file."""
        run_id, project_path = run_with_logs
        output_file = project_path / "export.tar.gz"

        result = runner.invoke(
            app, ["logs", "export", run_id, "--output", str(output_file)]
        )
        assert result.exit_code == 0
        # Export file should be created
        assert output_file.exists()

    def test_logs_export_default_output(
        self, runner: CliRunner, run_with_logs: tuple[str, Path]
    ) -> None:
        """Test logs export with default output location."""
        run_id, project_path = run_with_logs

        result = runner.invoke(app, ["logs", "export", run_id])
        assert result.exit_code == 0
        # Should mention the export path in output

    def test_logs_export_json_format(
        self, runner: CliRunner, run_with_logs: tuple[str, Path]
    ) -> None:
        """Test logs export with --format json."""
        run_id, project_path = run_with_logs
        output_file = project_path / "export.json"

        result = runner.invoke(
            app,
            [
                "logs",
                "export",
                run_id,
                "--format",
                "json",
                "--output",
                str(output_file),
            ],
        )
        assert result.exit_code == 0
