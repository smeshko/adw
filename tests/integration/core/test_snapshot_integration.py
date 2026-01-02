"""Integration tests for SnapshotManager (Story 4.3).

These tests verify the SnapshotManager works correctly in integration
with the RunDirectoryManager to create, list, and load snapshots
across a full phase lifecycle.
"""

from datetime import datetime, timezone
from pathlib import Path

import pytest

from adw.core import RunDirectoryManager, SnapshotManager
from adw.models import PhaseResult, PhaseStatus, RunContext, StateSnapshot


class TestPhaseLifecycleWithSnapshots:
    """Integration tests for full phase lifecycle with snapshots."""

    @pytest.fixture
    def project_root(self, tmp_path: Path) -> Path:
        """Create a temporary project root."""
        return tmp_path

    @pytest.fixture
    def sample_context(self) -> RunContext:
        """Create a sample RunContext for testing."""
        return RunContext(
            run_id="01KDSG2VDHNK0W4HSCZWJZXWSQ",
            feature_description="Add user authentication",
            current_phase="plan",
            started_at=datetime.now(timezone.utc),
        )

    def test_full_phase_lifecycle(
        self, project_root: Path, sample_context: RunContext
    ) -> None:
        """Test snapshots through full phase lifecycle."""
        # Create run directory structure first
        run_dir_manager = RunDirectoryManager(project_root)
        run_dir_manager.create(sample_context)

        snapshot_manager = SnapshotManager(run_dir_manager.runs_dir)

        # Phase 1: Plan
        pre_plan_path = snapshot_manager.create_pre_phase_snapshot(
            sample_context, "plan"
        )
        assert pre_plan_path.exists()
        assert pre_plan_path.name == "001_pre_plan.json"

        plan_result = PhaseResult(
            phase="plan",
            status=PhaseStatus.COMPLETED,
            started_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc),
            artifacts=["plan.md"],
            tokens_used=500,
        )
        post_plan_path = snapshot_manager.create_post_phase_snapshot(
            sample_context, "plan", plan_result
        )
        assert post_plan_path.exists()
        assert post_plan_path.name == "002_post_plan.json"

        # Phase 2: Build
        build_context = sample_context.model_copy(update={"current_phase": "build"})
        pre_build_path = snapshot_manager.create_pre_phase_snapshot(
            build_context, "build"
        )
        assert pre_build_path.name == "003_pre_build.json"

        build_result = PhaseResult(
            phase="build",
            status=PhaseStatus.COMPLETED,
            started_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc),
            artifacts=["src/auth.py"],
            tokens_used=1200,
        )
        post_build_path = snapshot_manager.create_post_phase_snapshot(
            build_context, "build", build_result
        )
        assert post_build_path.name == "004_post_build.json"

        # Verify all snapshots are listed
        snapshots = snapshot_manager.list_snapshots(sample_context.run_id)
        assert len(snapshots) == 4
        assert [s["filename"] for s in snapshots] == [
            "001_pre_plan.json",
            "002_post_plan.json",
            "003_pre_build.json",
            "004_post_build.json",
        ]

    def test_snapshot_content_integrity(
        self, project_root: Path, sample_context: RunContext
    ) -> None:
        """Verify snapshot content is preserved correctly through save/load."""
        run_dir_manager = RunDirectoryManager(project_root)
        run_dir_manager.create(sample_context)

        snapshot_manager = SnapshotManager(run_dir_manager.runs_dir)

        # Create a snapshot with specific content
        phase_result = PhaseResult(
            phase="verify",
            status=PhaseStatus.COMPLETED,
            started_at=datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc),
            completed_at=datetime(2024, 1, 15, 10, 35, 0, tzinfo=timezone.utc),
            artifacts=["test_results.xml", "coverage.xml"],
            tokens_used=750,
        )

        snapshot_manager.create_post_phase_snapshot(
            sample_context, "verify", phase_result
        )

        # Load and verify content
        snapshot = snapshot_manager.load_snapshot(sample_context.run_id, 1)

        assert snapshot.context.run_id == sample_context.run_id
        assert snapshot.context.feature_description == "Add user authentication"
        assert snapshot.label == "post_verify"
        assert snapshot.sequence == 1

        assert snapshot.phase_result is not None
        assert snapshot.phase_result.phase == "verify"
        assert snapshot.phase_result.tokens_used == 750
        assert snapshot.phase_result.artifacts == ["test_results.xml", "coverage.xml"]


class TestSnapshotListingAcrossPhases:
    """Integration tests for snapshot listing across phases."""

    @pytest.fixture
    def project_root(self, tmp_path: Path) -> Path:
        """Create a temporary project root."""
        return tmp_path

    @pytest.fixture
    def sample_context(self) -> RunContext:
        """Create a sample RunContext for testing."""
        return RunContext(
            run_id="01KDSG2VDHNK0W4HSCZWJZXWSQ",
            feature_description="Test feature",
            current_phase="plan",
            started_at=datetime.now(timezone.utc),
        )

    def test_list_snapshots_sorted_by_sequence(
        self, project_root: Path, sample_context: RunContext
    ) -> None:
        """Snapshots are listed in sequence order."""
        run_dir_manager = RunDirectoryManager(project_root)
        run_dir_manager.create(sample_context)

        snapshot_manager = SnapshotManager(run_dir_manager.runs_dir)

        # Create snapshots for multiple phases
        phases = ["plan", "build", "test", "verify"]
        for phase in phases:
            context = sample_context.model_copy(update={"current_phase": phase})
            snapshot_manager.create_pre_phase_snapshot(context, phase)

            result = PhaseResult(
                phase=phase,
                status=PhaseStatus.COMPLETED,
                started_at=datetime.now(timezone.utc),
                completed_at=datetime.now(timezone.utc),
            )
            snapshot_manager.create_post_phase_snapshot(context, phase, result)

        snapshots = snapshot_manager.list_snapshots(sample_context.run_id)

        # Should have 8 snapshots (pre + post for 4 phases)
        assert len(snapshots) == 8

        # Verify sequence order
        sequences = [s["sequence"] for s in snapshots]
        assert sequences == [1, 2, 3, 4, 5, 6, 7, 8]

        # Verify phases are in order
        expected_labels = [
            "pre_plan", "post_plan",
            "pre_build", "post_build",
            "pre_test", "post_test",
            "pre_verify", "post_verify",
        ]
        actual_labels = [f"{s['timing']}_{s['phase']}" for s in snapshots]
        assert actual_labels == expected_labels

    def test_listing_includes_metadata_not_content(
        self, project_root: Path, sample_context: RunContext
    ) -> None:
        """Listing returns metadata without loading full snapshot content."""
        run_dir_manager = RunDirectoryManager(project_root)
        run_dir_manager.create(sample_context)

        snapshot_manager = SnapshotManager(run_dir_manager.runs_dir)
        snapshot_manager.create_pre_phase_snapshot(sample_context, "plan")

        snapshots = snapshot_manager.list_snapshots(sample_context.run_id)

        # Metadata should be present
        assert len(snapshots) == 1
        snapshot = snapshots[0]
        assert "sequence" in snapshot
        assert "timing" in snapshot
        assert "phase" in snapshot
        assert "path" in snapshot
        assert "filename" in snapshot

        # Should NOT have full snapshot content
        assert "context" not in snapshot
        assert "phase_result" not in snapshot
        assert "timestamp" not in snapshot


class TestSnapshotRecovery:
    """Integration tests for recovering state from snapshots."""

    @pytest.fixture
    def project_root(self, tmp_path: Path) -> Path:
        """Create a temporary project root."""
        return tmp_path

    def test_recover_context_from_snapshot(self, project_root: Path) -> None:
        """Can recover full context from a snapshot."""
        # Create initial context
        initial_context = RunContext(
            run_id="01KDSG2VDHNK0W4HSCZWJZXWSQ",
            feature_description="Add user authentication",
            current_phase="build",
            phase_history=["plan"],
            started_at=datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc),
            phase_tokens={"plan": 500},
        )

        run_dir_manager = RunDirectoryManager(project_root)
        run_dir_manager.create(initial_context)

        snapshot_manager = SnapshotManager(run_dir_manager.runs_dir)

        # Create snapshot at known-good state
        plan_result = PhaseResult(
            phase="plan",
            status=PhaseStatus.COMPLETED,
            started_at=datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc),
            completed_at=datetime(2024, 1, 15, 10, 5, 0, tzinfo=timezone.utc),
            artifacts=["plan.md"],
            tokens_used=500,
        )
        snapshot_manager.create_post_phase_snapshot(
            initial_context, "plan", plan_result
        )

        # Later: recover from snapshot
        recovered_snapshot = snapshot_manager.load_snapshot(
            initial_context.run_id, 1
        )

        # Verify recovered context matches original
        assert recovered_snapshot.context.run_id == initial_context.run_id
        assert recovered_snapshot.context.feature_description == initial_context.feature_description
        assert recovered_snapshot.context.current_phase == initial_context.current_phase
        assert recovered_snapshot.context.phase_history == initial_context.phase_history
        assert recovered_snapshot.context.phase_tokens == initial_context.phase_tokens

        # Verify phase result is preserved
        assert recovered_snapshot.phase_result is not None
        assert recovered_snapshot.phase_result.phase == "plan"
        assert recovered_snapshot.phase_result.tokens_used == 500
        assert recovered_snapshot.phase_result.artifacts == ["plan.md"]

    def test_recover_pre_failure_state(self, project_root: Path) -> None:
        """Can recover state from pre-phase snapshot after failure."""
        context = RunContext(
            run_id="01KDSG2VDHNK0W4HSCZWJZXWSQ",
            feature_description="Test feature",
            current_phase="build",
            phase_history=["plan"],
            started_at=datetime.now(timezone.utc),
        )

        run_dir_manager = RunDirectoryManager(project_root)
        run_dir_manager.create(context)

        snapshot_manager = SnapshotManager(run_dir_manager.runs_dir)

        # Take pre-phase snapshot before risky operation
        snapshot_manager.create_pre_phase_snapshot(context, "build")

        # Simulate: build phase fails (no post snapshot created)
        # Recovery: load pre-build snapshot to restore context
        recovered = snapshot_manager.load_snapshot(context.run_id, 1)

        assert recovered.label == "pre_build"
        assert recovered.phase_result is None  # Pre-phase has no result
        assert recovered.context.current_phase == "build"
        assert recovered.context.phase_history == ["plan"]


class TestMultipleRunsIsolation:
    """Integration tests for snapshot isolation between runs."""

    @pytest.fixture
    def project_root(self, tmp_path: Path) -> Path:
        """Create a temporary project root."""
        return tmp_path

    def test_snapshots_isolated_between_runs(self, project_root: Path) -> None:
        """Snapshots from different runs are isolated."""
        run_dir_manager = RunDirectoryManager(project_root)

        # Create two runs
        context1 = RunContext(
            run_id="01KDSG2VDHNK0W4HSCZWJZXWSQ",
            feature_description="Feature 1",
            current_phase="plan",
            started_at=datetime.now(timezone.utc),
        )
        context2 = RunContext(
            run_id="01KDSG2VDHNK0W4HSCZWJZXWSR",
            feature_description="Feature 2",
            current_phase="plan",
            started_at=datetime.now(timezone.utc),
        )

        run_dir_manager.create(context1)
        run_dir_manager.create(context2)

        snapshot_manager = SnapshotManager(run_dir_manager.runs_dir)

        # Create snapshots for both runs
        snapshot_manager.create_pre_phase_snapshot(context1, "plan")
        snapshot_manager.create_pre_phase_snapshot(context1, "build")
        snapshot_manager.create_pre_phase_snapshot(context2, "plan")

        # Verify isolation
        run1_snapshots = snapshot_manager.list_snapshots(context1.run_id)
        run2_snapshots = snapshot_manager.list_snapshots(context2.run_id)

        assert len(run1_snapshots) == 2
        assert len(run2_snapshots) == 1

        # Verify content isolation
        run1_snapshot = snapshot_manager.load_snapshot(context1.run_id, 1)
        run2_snapshot = snapshot_manager.load_snapshot(context2.run_id, 1)

        assert run1_snapshot.context.feature_description == "Feature 1"
        assert run2_snapshot.context.feature_description == "Feature 2"
