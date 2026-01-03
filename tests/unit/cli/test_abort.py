"""Tests for abort CLI command."""

from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from adw.cli.app import app
from adw.exceptions import ConfigError, StateError
from adw.models import RunContext


@pytest.fixture
def runner() -> CliRunner:
    """Create CLI test runner."""
    return CliRunner()


@pytest.fixture
def sample_context() -> RunContext:
    """Create sample running context."""
    return RunContext(
        run_id="01JFTEST000000000000000001",
        feature_description="Test feature",
        current_phase="build",
        phase_history=["plan"],
        started_at=datetime.now(UTC),
        status="running",
    )


class TestAbortCommand:
    """Tests for abort command."""

    def test_abort_not_found_run(
        self,
        runner: CliRunner,
    ) -> None:
        """Test abort fails when run not found."""
        with patch("adw.cli.abort.get_runs_dir") as mock_runs_dir:
            mock_runs_dir.return_value = Path("/tmp/runs")

            with patch("adw.cli.abort.ContextManager") as mock_cm:
                mock_cm.return_value.load.side_effect = StateError(
                    code="CONTEXT_NOT_FOUND",
                    message="Context not found",
                    suggestion="Check ID",
                    recoverable=False,
                )

                result = runner.invoke(
                    app, ["abort", "01JFTEST000000000000000001", "--force"]
                )

                assert result.exit_code == 1
                assert "not found" in result.output.lower()

    def test_abort_not_active_run(
        self,
        runner: CliRunner,
        sample_context: RunContext,
    ) -> None:
        """Test abort fails when run is not active."""
        completed_context = sample_context.model_copy(update={"status": "completed"})

        with patch("adw.cli.abort.get_runs_dir") as mock_runs_dir:
            mock_runs_dir.return_value = Path("/tmp/runs")

            with patch("adw.cli.abort.ContextManager") as mock_cm:
                mock_cm.return_value.load.return_value = completed_context

                result = runner.invoke(
                    app, ["abort", "01JFTEST000000000000000001", "--force"]
                )

                assert result.exit_code == 1
                assert "not active" in result.output.lower()

    def test_abort_with_force_flag(
        self,
        runner: CliRunner,
        sample_context: RunContext,
    ) -> None:
        """Test abort with --force skips confirmation."""
        with patch("adw.cli.abort.get_runs_dir") as mock_runs_dir:
            mock_runs_dir.return_value = Path("/tmp/runs")

            with (
                patch("adw.cli.abort.ContextManager") as mock_cm,
                patch("adw.cli.abort.SnapshotManager") as mock_sm,
                patch("adw.cli.abort.InterruptionHandler") as mock_handler,
            ):
                mock_cm.return_value.load.return_value = sample_context

                result = runner.invoke(
                    app, ["abort", "01JFTEST000000000000000001", "--force"]
                )

                assert result.exit_code == 0
                mock_handler.return_value.abort_gracefully.assert_called_once()

    def test_abort_cancelled_by_user(
        self,
        runner: CliRunner,
        sample_context: RunContext,
    ) -> None:
        """Test abort cancelled when user declines confirmation."""
        with patch("adw.cli.abort.get_runs_dir") as mock_runs_dir:
            mock_runs_dir.return_value = Path("/tmp/runs")

            with (
                patch("adw.cli.abort.ContextManager") as mock_cm,
                patch("adw.cli.abort.SnapshotManager"),
                patch("adw.cli.abort.Confirm") as mock_confirm,
            ):
                mock_cm.return_value.load.return_value = sample_context
                mock_confirm.ask.return_value = False

                result = runner.invoke(
                    app, ["abort", "01JFTEST000000000000000001"]
                )

                assert result.exit_code == 0
                assert "cancelled" in result.output.lower()
