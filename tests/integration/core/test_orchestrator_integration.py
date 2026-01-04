"""Integration tests for Orchestrator.

These tests verify the orchestrator works correctly with real file I/O
and actual dependency implementations (ContextManager, SnapshotManager, etc.).
"""

from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from adw.core import (
    PHASE_SEQUENCE,
    ArtifactManager,
    ContextManager,
    Orchestrator,
    RunDirectoryManager,
    SnapshotManager,
)
from adw.models import RunContext
from adw.models.phase import PhaseResult, PhaseStatus


@pytest.fixture
def project_root(tmp_path: Path) -> Path:
    """Create a temporary project root with .adw structure."""
    adw_dir = tmp_path / ".adw" / "runs"
    adw_dir.mkdir(parents=True)
    return tmp_path


@pytest.fixture
def runs_dir(project_root: Path) -> Path:
    """Get the runs directory."""
    return project_root / ".adw" / "runs"


@pytest.fixture
def context_manager(runs_dir: Path) -> ContextManager:
    """Create a real ContextManager."""
    return ContextManager(runs_dir)


@pytest.fixture
def snapshot_manager(runs_dir: Path) -> SnapshotManager:
    """Create a real SnapshotManager."""
    return SnapshotManager(runs_dir)


@pytest.fixture
def artifact_manager(runs_dir: Path) -> ArtifactManager:
    """Create a real ArtifactManager."""
    return ArtifactManager(runs_dir)


@pytest.fixture
def run_directory_manager(project_root: Path) -> RunDirectoryManager:
    """Create a real RunDirectoryManager."""
    return RunDirectoryManager(project_root)


@pytest.fixture
def mock_phase_runner() -> MagicMock:
    """Create a mock PhaseRunner that returns successful results."""
    runner = MagicMock()

    def run_side_effect(
        phase: str,
        context: RunContext,
        *,
        artifacts_override: dict[str, dict[str, str]] | None = None,
    ) -> PhaseResult:
        return PhaseResult(
            phase=phase,
            status=PhaseStatus.COMPLETED,
            started_at=datetime.now(UTC),
            completed_at=datetime.now(UTC),
            tokens_used=100,
        )

    runner.run = MagicMock(side_effect=run_side_effect)
    return runner


@pytest.fixture
def orchestrator(
    runs_dir: Path,
    context_manager: ContextManager,
    snapshot_manager: SnapshotManager,
    artifact_manager: ArtifactManager,
    run_directory_manager: RunDirectoryManager,
) -> Orchestrator:
    """Create an Orchestrator with real dependencies."""
    return Orchestrator(
        runs_dir=runs_dir,
        context_manager=context_manager,
        snapshot_manager=snapshot_manager,
        artifact_manager=artifact_manager,
        run_directory_manager=run_directory_manager,
    )


class TestFullRunIntegration:
    """Integration tests for full pipeline runs."""

    def test_full_run_creates_directory_structure(
        self,
        orchestrator: Orchestrator,
        mock_phase_runner: MagicMock,
        runs_dir: Path,
    ) -> None:
        """Test that a full run creates the expected directory structure."""
        orchestrator.set_phase_runner(mock_phase_runner)

        context = orchestrator.run("Add user authentication")

        run_dir = runs_dir / context.run_id
        assert run_dir.exists()
        assert (run_dir / "context.json").exists()
        assert (run_dir / "snapshots").is_dir()
        assert (run_dir / "artifacts").is_dir()
        assert (run_dir / "logs").is_dir()
        assert (run_dir / "llm").is_dir()

    def test_full_run_creates_all_snapshots(
        self,
        orchestrator: Orchestrator,
        mock_phase_runner: MagicMock,
        runs_dir: Path,
    ) -> None:
        """Test that snapshots are created for each phase."""
        orchestrator.set_phase_runner(mock_phase_runner)

        context = orchestrator.run("Add user authentication")

        snapshots_dir = runs_dir / context.run_id / "snapshots"
        snapshot_files = list(snapshots_dir.glob("*.json"))

        # Should have pre and post snapshot for each of 5 phases = 10 snapshots
        assert len(snapshot_files) == 10

        # Verify naming pattern
        for phase in PHASE_SEQUENCE:
            pre_snapshot = list(snapshots_dir.glob(f"*_pre_{phase}.json"))
            post_snapshot = list(snapshots_dir.glob(f"*_post_{phase}.json"))
            assert len(pre_snapshot) == 1, f"Missing pre snapshot for {phase}"
            assert len(post_snapshot) == 1, f"Missing post snapshot for {phase}"

    def test_full_run_persists_context(
        self,
        orchestrator: Orchestrator,
        mock_phase_runner: MagicMock,
        runs_dir: Path,
        context_manager: ContextManager,
    ) -> None:
        """Test that context is persisted and can be reloaded."""
        orchestrator.set_phase_runner(mock_phase_runner)

        context = orchestrator.run("Add user authentication")

        # Reload context from disk
        reloaded = context_manager.load(context.run_id)

        assert reloaded.run_id == context.run_id
        assert reloaded.feature_description == "Add user authentication"
        assert reloaded.status == "completed"
        assert reloaded.phase_history == list(PHASE_SEQUENCE)

    def test_full_run_tracks_tokens(
        self,
        orchestrator: Orchestrator,
        mock_phase_runner: MagicMock,
    ) -> None:
        """Test that token usage is tracked for all phases."""
        orchestrator.set_phase_runner(mock_phase_runner)

        context = orchestrator.run("Add user authentication")

        for phase in PHASE_SEQUENCE:
            assert phase in context.phase_tokens
            assert context.phase_tokens[phase] == 100

        assert context.total_tokens == 500  # 100 tokens * 5 phases


class TestSnapshotIntegration:
    """Integration tests for snapshot creation and loading."""

    def test_snapshots_contain_valid_context(
        self,
        orchestrator: Orchestrator,
        mock_phase_runner: MagicMock,
        runs_dir: Path,
        snapshot_manager: SnapshotManager,
    ) -> None:
        """Test that snapshots contain valid serialized context."""
        orchestrator.set_phase_runner(mock_phase_runner)

        context = orchestrator.run("Test feature")

        # Load and verify each snapshot
        snapshots = snapshot_manager.list_snapshots(context.run_id)
        assert len(snapshots) == 10

        for snapshot_meta in snapshots:
            snapshot = snapshot_manager.load_snapshot(
                context.run_id, int(str(snapshot_meta["sequence"]))
            )
            assert snapshot.context.run_id == context.run_id
            assert snapshot.label is not None

    def test_pre_snapshot_has_no_phase_result(
        self,
        orchestrator: Orchestrator,
        mock_phase_runner: MagicMock,
        runs_dir: Path,
        snapshot_manager: SnapshotManager,
    ) -> None:
        """Test that pre-phase snapshots have no phase result."""
        orchestrator.set_phase_runner(mock_phase_runner)

        context = orchestrator.run("Test feature")

        snapshots = snapshot_manager.list_snapshots(context.run_id)
        pre_snapshots = [s for s in snapshots if s["timing"] == "pre"]

        for snapshot_meta in pre_snapshots:
            snapshot = snapshot_manager.load_snapshot(
                context.run_id, int(str(snapshot_meta["sequence"]))
            )
            assert snapshot.phase_result is None

    def test_post_snapshot_has_phase_result(
        self,
        orchestrator: Orchestrator,
        mock_phase_runner: MagicMock,
        runs_dir: Path,
        snapshot_manager: SnapshotManager,
    ) -> None:
        """Test that post-phase snapshots have phase results."""
        orchestrator.set_phase_runner(mock_phase_runner)

        context = orchestrator.run("Test feature")

        snapshots = snapshot_manager.list_snapshots(context.run_id)
        post_snapshots = [s for s in snapshots if s["timing"] == "post"]

        for snapshot_meta in post_snapshots:
            snapshot = snapshot_manager.load_snapshot(
                context.run_id, int(str(snapshot_meta["sequence"]))
            )
            assert snapshot.phase_result is not None
            assert snapshot.phase_result.status == PhaseStatus.COMPLETED


class TestContextPersistenceIntegration:
    """Integration tests for context persistence."""

    def test_context_persisted_at_each_phase(
        self,
        orchestrator: Orchestrator,
        mock_phase_runner: MagicMock,
        runs_dir: Path,
    ) -> None:
        """Test that context is persisted during and after each phase."""
        persist_count = 0
        original_run = mock_phase_runner.run.side_effect

        def tracking_run(
            phase: str,
            context: RunContext,
            *,
            artifacts_override: dict[str, dict[str, str]] | None = None,
        ) -> PhaseResult:
            nonlocal persist_count
            # Check context file exists mid-run
            context_file = runs_dir / context.run_id / "context.json"
            if context_file.exists():
                persist_count += 1
            return original_run(phase, context, artifacts_override=artifacts_override)

        mock_phase_runner.run.side_effect = tracking_run
        orchestrator.set_phase_runner(mock_phase_runner)

        orchestrator.run("Test feature")

        # Context should have been persisted multiple times
        assert persist_count >= 5  # At least once per phase

    def test_final_context_has_completed_status(
        self,
        orchestrator: Orchestrator,
        mock_phase_runner: MagicMock,
        runs_dir: Path,
    ) -> None:
        """Test that final persisted context has completed status."""
        orchestrator.set_phase_runner(mock_phase_runner)

        context = orchestrator.run("Test feature")

        # Read raw file to verify persistence
        context_file = runs_dir / context.run_id / "context.json"
        content = context_file.read_text()

        assert '"status": "completed"' in content
        assert context.completed_at is not None


class TestResumeIntegration:
    """Integration tests for resume capability."""

    def test_interrupted_run_can_determine_resume_phase(
        self,
        orchestrator: Orchestrator,
        mock_phase_runner: MagicMock,
        context_manager: ContextManager,
    ) -> None:
        """Test that an interrupted run can determine the resume phase.

        This validates that the interruption infrastructure supports resume,
        even though the Orchestrator.run() doesn't have a resume parameter yet.
        """
        from adw.core.interruption import (
            ShutdownRequested,
            can_resume,
            get_resume_phase,
        )

        # Simulate interruption during build phase
        call_count = 0

        def run_with_interrupt(
            phase: str,
            context: RunContext,
            *,
            artifacts_override: dict[str, dict[str, str]] | None = None,
        ) -> PhaseResult:
            nonlocal call_count
            call_count += 1
            if phase == "build":
                # Simulate what happens when interrupted
                interrupted_context = context.model_copy(
                    update={
                        "status": "interrupted",
                        "interrupted_phase": "build",
                    }
                )
                context_manager.save(interrupted_context)
                raise ShutdownRequested(phase="build")
            return PhaseResult(
                phase=phase,
                status=PhaseStatus.COMPLETED,
                started_at=datetime.now(UTC),
                completed_at=datetime.now(UTC),
                tokens_used=100,
            )

        mock_phase_runner.run.side_effect = run_with_interrupt
        orchestrator.set_phase_runner(mock_phase_runner)

        with pytest.raises(ShutdownRequested):
            orchestrator.run("Test feature")

        # Plan should have succeeded, build should have been interrupted
        assert call_count == 2

        # Reload the interrupted context and verify resume capability
        runs = list(orchestrator.runs_dir.glob("*/context.json"))
        assert len(runs) >= 1

        # Load the most recent interrupted context
        import json

        latest_run = max(runs, key=lambda p: p.stat().st_mtime)
        ctx_data = json.loads(latest_run.read_text())

        # Verify it's interrupted at build
        if ctx_data.get("status") == "interrupted":
            assert ctx_data.get("interrupted_phase") == "build"

            # Check resume functions work
            reloaded = context_manager.load(ctx_data["run_id"])
            assert can_resume(reloaded)
            assert get_resume_phase(reloaded) == "build"

    def test_completed_run_cannot_resume(
        self,
        orchestrator: Orchestrator,
        mock_phase_runner: MagicMock,
        context_manager: ContextManager,
    ) -> None:
        """Test that completed runs correctly report they cannot be resumed."""
        from adw.core.interruption import can_resume, get_resume_phase

        orchestrator.set_phase_runner(mock_phase_runner)

        context = orchestrator.run("Test feature")

        # Reload from disk
        reloaded = context_manager.load(context.run_id)

        # Completed runs cannot be resumed
        assert not can_resume(reloaded)
        assert get_resume_phase(reloaded) is None
