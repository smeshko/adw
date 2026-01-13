"""Integration tests for abort CLI command.

These tests verify the full abort flow end-to-end, including state
persistence and snapshot creation.
"""

from datetime import UTC, datetime
from pathlib import Path

import pytest

from adw.core import ContextManager, SnapshotManager
from adw.models import RunContext


@pytest.fixture
def runs_dir(tmp_path: Path) -> Path:
    """Create a temporary runs directory."""
    runs = tmp_path / ".adw" / "runs"
    runs.mkdir(parents=True)
    return runs


@pytest.fixture
def running_context(runs_dir: Path) -> RunContext:
    """Create a running context with proper directory structure."""
    run_id = "01JFTEST000000000000000001"
    run_dir = runs_dir / run_id
    run_dir.mkdir(parents=True)
    (run_dir / "snapshots").mkdir()

    context = RunContext(
        run_id=run_id,
        feature_description="Test feature for abort",
        current_phase="build",
        phase_history=["plan"],
        started_at=datetime.now(UTC),
        status="running",
    )

    # Save initial context
    context_manager = ContextManager(runs_dir)
    context_manager.save(context)

    return context


class TestAbortIntegration:
    """Integration tests for abort functionality."""

    def test_abort_saves_state(
        self,
        runs_dir: Path,
        running_context: RunContext,
    ) -> None:
        """Test that abort saves context with aborted status."""
        from adw.core import InterruptionHandler

        context_manager = ContextManager(runs_dir)
        snapshot_manager = SnapshotManager(runs_dir)

        handler = InterruptionHandler(
            context_manager=context_manager,
            snapshot_manager=snapshot_manager,
        )

        # Abort the run
        result = handler.abort_gracefully(running_context)

        # Verify context was saved
        assert result.status == "aborted"
        assert result.completed_at is not None

        # Reload and verify persistence
        reloaded = context_manager.load(running_context.run_id)
        assert reloaded.status == "aborted"

    def test_abort_creates_snapshot(
        self,
        runs_dir: Path,
        running_context: RunContext,
    ) -> None:
        """Test that abort creates an abort snapshot."""
        from adw.core import InterruptionHandler

        context_manager = ContextManager(runs_dir)
        snapshot_manager = SnapshotManager(runs_dir)

        handler = InterruptionHandler(
            context_manager=context_manager,
            snapshot_manager=snapshot_manager,
        )

        # Abort the run
        handler.abort_gracefully(running_context, reason="test_abort")

        # Verify snapshot was created
        snapshots = snapshot_manager.list_snapshots(running_context.run_id)
        assert len(snapshots) > 0

        # Find abort snapshot
        abort_snapshots = [s for s in snapshots if "abort" in s["phase"]]
        assert len(abort_snapshots) == 1
        assert "test_abort" in abort_snapshots[0]["phase"]

    def test_aborted_run_can_be_resumed(
        self,
        runs_dir: Path,
        running_context: RunContext,
    ) -> None:
        """Test that aborted runs can be resumed."""
        from adw.core import InterruptionHandler, ResumeManager
        from adw.core.run_lookup import RunLookup

        context_manager = ContextManager(runs_dir)
        snapshot_manager = SnapshotManager(runs_dir)

        handler = InterruptionHandler(
            context_manager=context_manager,
            snapshot_manager=snapshot_manager,
        )

        resume_manager = ResumeManager(
            runs_dir=runs_dir,
            run_lookup=RunLookup(runs_dir),
            context_manager=context_manager,
        )

        # Abort the run
        aborted = handler.abort_gracefully(running_context)
        assert aborted.status == "aborted"

        # Verify can resume
        assert resume_manager.can_resume(aborted) is True

        # Prepare for resume
        resumed = resume_manager.prepare_for_resume(aborted)
        assert resumed.status == "running"
        assert resumed.phase_history == running_context.phase_history

    def test_full_abort_flow_via_orchestrator(
        self,
        runs_dir: Path,
        running_context: RunContext,
    ) -> None:
        """Test full abort flow using Orchestrator."""
        from unittest.mock import MagicMock

        from adw.core import (
            ArtifactManager,
            InterruptionHandler,
            Orchestrator,
            RunDirectoryManager,
        )

        context_manager = ContextManager(runs_dir)
        snapshot_manager = SnapshotManager(runs_dir)
        artifact_manager = ArtifactManager(runs_dir)
        run_directory_manager = RunDirectoryManager(runs_dir.parent.parent)
        interruption_handler = InterruptionHandler(context_manager, snapshot_manager)
        mock_phase_runner = MagicMock()

        orchestrator = Orchestrator(
            runs_dir=runs_dir,
            context_manager=context_manager,
            snapshot_manager=snapshot_manager,
            artifact_manager=artifact_manager,
            run_directory_manager=run_directory_manager,
            phase_runner=mock_phase_runner,
            interruption_handler=interruption_handler,
        )

        # Abort via orchestrator
        result = orchestrator.abort(running_context.run_id)

        assert result.status == "aborted"
        assert result.completed_at is not None

        # Verify persistence
        reloaded = context_manager.load(running_context.run_id)
        assert reloaded.status == "aborted"
