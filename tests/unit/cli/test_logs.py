"""Unit tests for logs CLI commands."""

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from adw.cli.app import app


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

    def test_state_run_not_found(
        self, runner: CliRunner, mock_adw_dir: Path
    ) -> None:
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

        result = runner.invoke(
            app, ["logs", "state", "test-run", "--snapshot", "1"]
        )
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

        result = runner.invoke(
            app, ["logs", "state", "test-run", "--phase", "plan"]
        )
        assert result.exit_code == 1
        assert "--at" in result.output.lower()
