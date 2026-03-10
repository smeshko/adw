"""Tests for core/run_trigger.py – extracted run trigger logic.

Covers command building, subprocess spawning, error handling,
and the RunTrigger class that the dashboard uses to start runs.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from adw.core.run_trigger import RunTrigger, RunTriggerResult


class TestRunTriggerResult:
    """Tests for the RunTriggerResult dataclass."""

    def test_success_result(self) -> None:
        """Successful result has correct attributes."""
        result = RunTriggerResult(success=True, process_id=1234)
        assert result.success is True
        assert result.process_id == 1234
        assert result.run_id is None
        assert result.error is None

    def test_failure_result(self) -> None:
        """Failed result includes error message."""
        result = RunTriggerResult(success=False, error="Command not found")
        assert result.success is False
        assert result.error == "Command not found"
        assert result.process_id is None


class TestRunTriggerBuildCommand:
    """Tests for RunTrigger._build_command."""

    def test_basic_command(self) -> None:
        """Basic command without phases."""
        trigger = RunTrigger(project_dir=Path("/projects/test"))
        cmd = trigger._build_command("Add dark mode", None)
        assert cmd == ["adw", "run", "Add dark mode"]

    def test_single_phase(self) -> None:
        """Command with single phase."""
        trigger = RunTrigger(project_dir=Path("/projects/test"))
        cmd = trigger._build_command("Add login", ["plan"])
        assert cmd == ["adw", "run", "--phase", "plan", "Add login"]

    def test_multiple_phases_uses_first(self) -> None:
        """Multiple phases uses first phase only (CLI limitation)."""
        trigger = RunTrigger(project_dir=Path("/projects/test"))
        cmd = trigger._build_command("Add login", ["plan", "build"])
        assert cmd == ["adw", "run", "--phase", "plan", "Add login"]

    def test_custom_adw_command(self) -> None:
        """Custom ADW command path."""
        trigger = RunTrigger(
            project_dir=Path("/projects/test"),
            adw_command="/usr/local/bin/adw",
        )
        cmd = trigger._build_command("Test feature", None)
        assert cmd[0] == "/usr/local/bin/adw"

    def test_default_project_dir(self) -> None:
        """Default project dir is cwd."""
        trigger = RunTrigger()
        assert trigger._project_dir == Path.cwd()


class TestRunTriggerStartRun:
    """Tests for RunTrigger.start_run async method."""

    @pytest.mark.asyncio
    async def test_successful_start(self) -> None:
        """Successful run start returns success result with PID."""
        trigger = RunTrigger(project_dir=Path("/projects/test"))

        mock_process = MagicMock()
        mock_process.pid = 42

        with patch(
            "adw.core.run_trigger.subprocess.Popen", return_value=mock_process
        ) as mock_popen:
            result = await trigger.start_run(
                project_path="/projects/test",
                feature="Add dark mode",
            )

        assert result.success is True
        assert result.process_id == 42
        mock_popen.assert_called_once()
        call_kwargs = mock_popen.call_args
        assert call_kwargs.kwargs["cwd"] == Path("/projects/test")
        assert call_kwargs.kwargs["stdout"] == subprocess.DEVNULL
        assert call_kwargs.kwargs["stderr"] == subprocess.DEVNULL
        assert call_kwargs.kwargs["start_new_session"] is True

    @pytest.mark.asyncio
    async def test_start_with_phases(self) -> None:
        """Run start passes phases to command builder."""
        trigger = RunTrigger(project_dir=Path("/projects/test"))

        mock_process = MagicMock()
        mock_process.pid = 100

        with patch("adw.core.run_trigger.subprocess.Popen", return_value=mock_process):
            result = await trigger.start_run(
                project_path="/projects/test",
                feature="Add login",
                phases=["plan"],
            )

        assert result.success is True

    @pytest.mark.asyncio
    async def test_command_not_found(self) -> None:
        """FileNotFoundError returns failure result."""
        trigger = RunTrigger(project_dir=Path("/projects/test"))

        with patch(
            "adw.core.run_trigger.subprocess.Popen",
            side_effect=FileNotFoundError("adw not found"),
        ):
            result = await trigger.start_run(
                project_path="/projects/test",
                feature="Test",
            )

        assert result.success is False
        assert "not found" in result.error.lower()

    @pytest.mark.asyncio
    async def test_os_error(self) -> None:
        """OSError during subprocess start returns failure."""
        trigger = RunTrigger(project_dir=Path("/projects/test"))

        with patch(
            "adw.core.run_trigger.subprocess.Popen",
            side_effect=OSError("Permission denied"),
        ):
            result = await trigger.start_run(
                project_path="/projects/test",
                feature="Test",
            )

        assert result.success is False
        assert "Permission denied" in result.error

    @pytest.mark.asyncio
    async def test_project_path_overrides_default(self) -> None:
        """project_path parameter overrides the default project_dir."""
        trigger = RunTrigger(project_dir=Path("/default/dir"))

        mock_process = MagicMock()
        mock_process.pid = 55

        with patch(
            "adw.core.run_trigger.subprocess.Popen", return_value=mock_process
        ) as mock_popen:
            await trigger.start_run(
                project_path="/custom/project",
                feature="Test",
            )

        call_kwargs = mock_popen.call_args
        assert call_kwargs.kwargs["cwd"] == Path("/custom/project")
