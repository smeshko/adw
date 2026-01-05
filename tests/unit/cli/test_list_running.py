"""Tests for the list --running flag functionality."""

import json
import os
from pathlib import Path

import pytest

from adw.cli.list import _format_elapsed, _list_running_runs
from adw.worktree import ConcurrentRunManager


class TestFormatElapsed:
    """Tests for the elapsed time formatting function."""

    def test_format_seconds(self) -> None:
        """Formats times under 60 seconds."""
        assert _format_elapsed(0) == "0s"
        assert _format_elapsed(45) == "45s"
        assert _format_elapsed(59) == "59s"

    def test_format_minutes(self) -> None:
        """Formats times under 1 hour."""
        assert _format_elapsed(60) == "1m 0s"
        assert _format_elapsed(90) == "1m 30s"
        assert _format_elapsed(323) == "5m 23s"  # Story example: 5m 23s
        assert _format_elapsed(130) == "2m 10s"  # Story example: 2m 10s

    def test_format_hours(self) -> None:
        """Formats times over 1 hour."""
        assert _format_elapsed(3600) == "1h 0m"
        assert _format_elapsed(5400) == "1h 30m"  # Story example: 1h 30m
        assert _format_elapsed(7320) == "2h 2m"


class TestListRunningCommand:
    """Tests for the list --running command."""

    @pytest.fixture
    def manager(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> ConcurrentRunManager:
        """Create a ConcurrentRunManager with mocked cwd."""
        # Mock Path.cwd() to return tmp_path
        monkeypatch.setattr(Path, "cwd", lambda: tmp_path)
        return ConcurrentRunManager(tmp_path)

    def test_list_running_shows_active_runs(
        self,
        tmp_path: Path,
        manager: ConcurrentRunManager,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """--running flag shows active runs."""
        # Register a run with current PID (will show as active)
        run_id = "01HQTEST123456789ABCD"
        worktree_path = tmp_path / "trees" / run_id

        manager.register_run(
            run_id=run_id,
            worktree_path=worktree_path,
            backend_port=9100,
            frontend_port=9200,
        )

        # Call the list running function
        _list_running_runs(json_output=False)

        # Check output contains expected information
        captured = capsys.readouterr()
        assert run_id in captured.out
        assert "9100/9200" in captured.out
        assert "1 of 15" in captured.out  # "Active Runs (1 of 15)"

    def test_list_running_json_output(
        self,
        tmp_path: Path,
        manager: ConcurrentRunManager,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """--running with --json outputs valid JSON."""
        run_id = "01HQTEST123456789ABCD"
        worktree_path = tmp_path / "trees" / run_id

        manager.register_run(
            run_id=run_id,
            worktree_path=worktree_path,
            backend_port=9100,
            frontend_port=9200,
        )

        _list_running_runs(json_output=True)

        captured = capsys.readouterr()
        data = json.loads(captured.out)

        assert data["active_count"] == 1
        assert data["max_concurrent"] == 15
        assert len(data["runs"]) == 1
        assert data["runs"][0]["run_id"] == run_id
        assert data["runs"][0]["backend_port"] == 9100
        assert data["runs"][0]["frontend_port"] == 9200
        assert data["runs"][0]["pid"] == os.getpid()

    def test_list_running_empty(
        self,
        tmp_path: Path,
        manager: ConcurrentRunManager,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """--running shows message when no active runs."""
        _list_running_runs(json_output=False)

        captured = capsys.readouterr()
        assert "No active runs" in captured.out

    def test_list_running_multiple_runs(
        self,
        tmp_path: Path,
        manager: ConcurrentRunManager,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """--running shows multiple active runs."""
        run_ids = [
            "01HQTEST1111111111111111",
            "01HQTEST2222222222222222",
            "01HQTEST3333333333333333",
        ]

        for i, run_id in enumerate(run_ids):
            manager.register_run(
                run_id=run_id,
                worktree_path=tmp_path / "trees" / run_id,
                backend_port=9100 + i,
                frontend_port=9200 + i,
            )

        _list_running_runs(json_output=False)

        captured = capsys.readouterr()
        assert "3 of 15" in captured.out
        for run_id in run_ids:
            assert run_id in captured.out
