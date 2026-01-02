"""Tests for SnapshotManager (Story 4.3).

SnapshotManager creates, lists, and loads state snapshots at phase boundaries for:
- Debugging failures
- Resuming from known-good states
- Time-travel debugging (NFR13)
"""

import json
import time
from datetime import datetime, timezone
from pathlib import Path

import pytest

from adw.core import SnapshotManager
from adw.exceptions import StateError
from adw.models import PhaseResult, PhaseStatus, RunContext, StateSnapshot


class TestSnapshotManagerInit:
    """Tests for SnapshotManager initialization."""

    def test_init_with_valid_path(self, tmp_path: Path) -> None:
        """SnapshotManager initializes with valid path."""
        runs_dir = tmp_path / ".adw" / "runs"
        manager = SnapshotManager(runs_dir)
        assert manager.runs_dir == runs_dir

    def test_init_sequence_cache_empty(self, tmp_path: Path) -> None:
        """Sequence cache is empty on init."""
        manager = SnapshotManager(tmp_path)
        assert manager._sequence_cache == {}


class TestPrePhaseSnapshot:
    """Tests for pre-phase snapshot creation."""

    @pytest.fixture
    def sample_context(self) -> RunContext:
        """Create a sample RunContext for testing."""
        return RunContext(
            run_id="01KDSG2VDHNK0W4HSCZWJZXWSQ",
            feature_description="Add user authentication",
            current_phase="plan",
            started_at=datetime.now(timezone.utc),
        )

    @pytest.fixture
    def setup_run_dir(self, tmp_path: Path) -> Path:
        """Set up run directory structure."""
        runs_dir = tmp_path / ".adw" / "runs"
        run_dir = runs_dir / "01KDSG2VDHNK0W4HSCZWJZXWSQ"
        snapshots_dir = run_dir / "snapshots"
        snapshots_dir.mkdir(parents=True)
        return runs_dir

    def test_pre_phase_snapshot_created(
        self, setup_run_dir: Path, sample_context: RunContext
    ) -> None:
        """Pre-phase snapshot is created correctly."""
        manager = SnapshotManager(setup_run_dir)
        path = manager.create_pre_phase_snapshot(sample_context, "plan")

        assert path.exists()
        assert path.name == "001_pre_plan.json"

    def test_pre_phase_snapshot_content(
        self, setup_run_dir: Path, sample_context: RunContext
    ) -> None:
        """Pre-phase snapshot contains correct content."""
        manager = SnapshotManager(setup_run_dir)
        path = manager.create_pre_phase_snapshot(sample_context, "plan")

        snapshot = StateSnapshot.model_validate_json(path.read_text())
        assert snapshot.label == "pre_plan"
        assert snapshot.phase_result is None
        assert snapshot.sequence == 1
        assert snapshot.context.run_id == sample_context.run_id

    def test_pre_phase_snapshot_missing_dir_raises(
        self, tmp_path: Path, sample_context: RunContext
    ) -> None:
        """Pre-phase snapshot raises when snapshots dir missing."""
        runs_dir = tmp_path / ".adw" / "runs"
        run_dir = runs_dir / "01KDSG2VDHNK0W4HSCZWJZXWSQ"
        run_dir.mkdir(parents=True)  # No snapshots subdir

        manager = SnapshotManager(runs_dir)
        with pytest.raises(StateError) as exc_info:
            manager.create_pre_phase_snapshot(sample_context, "plan")

        assert exc_info.value.code == "SNAPSHOTS_DIR_NOT_FOUND"


class TestPostPhaseSnapshot:
    """Tests for post-phase snapshot creation."""

    @pytest.fixture
    def sample_context(self) -> RunContext:
        """Create a sample RunContext for testing."""
        return RunContext(
            run_id="01KDSG2VDHNK0W4HSCZWJZXWSQ",
            feature_description="Add user authentication",
            current_phase="plan",
            started_at=datetime.now(timezone.utc),
        )

    @pytest.fixture
    def sample_result(self) -> PhaseResult:
        """Create a sample PhaseResult for testing."""
        return PhaseResult(
            phase="plan",
            status=PhaseStatus.COMPLETED,
            started_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc),
            artifacts=["plan.md"],
            tokens_used=500,
        )

    @pytest.fixture
    def setup_run_dir(self, tmp_path: Path) -> Path:
        """Set up run directory structure."""
        runs_dir = tmp_path / ".adw" / "runs"
        run_dir = runs_dir / "01KDSG2VDHNK0W4HSCZWJZXWSQ"
        snapshots_dir = run_dir / "snapshots"
        snapshots_dir.mkdir(parents=True)
        return runs_dir

    def test_post_phase_snapshot_includes_result(
        self, setup_run_dir: Path, sample_context: RunContext, sample_result: PhaseResult
    ) -> None:
        """Post-phase snapshot includes phase result."""
        manager = SnapshotManager(setup_run_dir)
        path = manager.create_post_phase_snapshot(
            sample_context, "plan", sample_result
        )

        snapshot = StateSnapshot.model_validate_json(path.read_text())
        assert snapshot.phase_result is not None
        assert snapshot.phase_result.phase == "plan"
        assert snapshot.phase_result.tokens_used == 500
        assert snapshot.label == "post_plan"


class TestSequentialNumbering:
    """Tests for sequential snapshot numbering."""

    @pytest.fixture
    def sample_context(self) -> RunContext:
        """Create a sample RunContext for testing."""
        return RunContext(
            run_id="01KDSG2VDHNK0W4HSCZWJZXWSQ",
            feature_description="Add user authentication",
            current_phase="plan",
            started_at=datetime.now(timezone.utc),
        )

    @pytest.fixture
    def sample_result(self) -> PhaseResult:
        """Create a sample PhaseResult for testing."""
        return PhaseResult(
            phase="plan",
            status=PhaseStatus.COMPLETED,
            started_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc),
        )

    @pytest.fixture
    def setup_run_dir(self, tmp_path: Path) -> Path:
        """Set up run directory structure."""
        runs_dir = tmp_path / ".adw" / "runs"
        run_dir = runs_dir / "01KDSG2VDHNK0W4HSCZWJZXWSQ"
        snapshots_dir = run_dir / "snapshots"
        snapshots_dir.mkdir(parents=True)
        return runs_dir

    def test_snapshots_numbered_sequentially(
        self, setup_run_dir: Path, sample_context: RunContext, sample_result: PhaseResult
    ) -> None:
        """Snapshots are numbered 001, 002, etc."""
        manager = SnapshotManager(setup_run_dir)

        manager.create_pre_phase_snapshot(sample_context, "plan")
        manager.create_post_phase_snapshot(sample_context, "plan", sample_result)
        manager.create_pre_phase_snapshot(sample_context, "build")

        snapshots = manager.list_snapshots(sample_context.run_id)

        assert [s["sequence"] for s in snapshots] == [1, 2, 3]
        assert [s["filename"] for s in snapshots] == [
            "001_pre_plan.json",
            "002_post_plan.json",
            "003_pre_build.json",
        ]

    def test_sequence_uses_zero_padding(
        self, setup_run_dir: Path, sample_context: RunContext
    ) -> None:
        """Sequence numbers are zero-padded to 3 digits."""
        manager = SnapshotManager(setup_run_dir)
        path = manager.create_pre_phase_snapshot(sample_context, "plan")

        assert "001_" in path.name


class TestSnapshotListing:
    """Tests for snapshot listing."""

    @pytest.fixture
    def sample_context(self) -> RunContext:
        """Create a sample RunContext for testing."""
        return RunContext(
            run_id="01KDSG2VDHNK0W4HSCZWJZXWSQ",
            feature_description="Add user authentication",
            current_phase="plan",
            started_at=datetime.now(timezone.utc),
        )

    @pytest.fixture
    def sample_result(self) -> PhaseResult:
        """Create a sample PhaseResult for testing."""
        return PhaseResult(
            phase="plan",
            status=PhaseStatus.COMPLETED,
            started_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc),
        )

    @pytest.fixture
    def setup_run_dir(self, tmp_path: Path) -> Path:
        """Set up run directory structure."""
        runs_dir = tmp_path / ".adw" / "runs"
        run_dir = runs_dir / "01KDSG2VDHNK0W4HSCZWJZXWSQ"
        snapshots_dir = run_dir / "snapshots"
        snapshots_dir.mkdir(parents=True)
        return runs_dir

    def test_list_empty_directory(self, setup_run_dir: Path) -> None:
        """Listing empty directory returns empty list."""
        manager = SnapshotManager(setup_run_dir)
        snapshots = manager.list_snapshots("01KDSG2VDHNK0W4HSCZWJZXWSQ")
        assert snapshots == []

    def test_list_nonexistent_run(self, setup_run_dir: Path) -> None:
        """Listing nonexistent run returns empty list."""
        manager = SnapshotManager(setup_run_dir)
        snapshots = manager.list_snapshots("NONEXISTENT0000000000000")
        assert snapshots == []

    def test_list_returns_metadata(
        self, setup_run_dir: Path, sample_context: RunContext, sample_result: PhaseResult
    ) -> None:
        """Listing returns metadata for each snapshot."""
        manager = SnapshotManager(setup_run_dir)

        manager.create_pre_phase_snapshot(sample_context, "plan")
        manager.create_post_phase_snapshot(sample_context, "plan", sample_result)

        snapshots = manager.list_snapshots(sample_context.run_id)

        assert len(snapshots) == 2
        assert snapshots[0]["sequence"] == 1
        assert snapshots[0]["timing"] == "pre"
        assert snapshots[0]["phase"] == "plan"
        assert "path" in snapshots[0]
        assert "filename" in snapshots[0]


class TestSnapshotLoading:
    """Tests for snapshot loading."""

    @pytest.fixture
    def sample_context(self) -> RunContext:
        """Create a sample RunContext for testing."""
        return RunContext(
            run_id="01KDSG2VDHNK0W4HSCZWJZXWSQ",
            feature_description="Add user authentication",
            current_phase="plan",
            started_at=datetime.now(timezone.utc),
        )

    @pytest.fixture
    def sample_result(self) -> PhaseResult:
        """Create a sample PhaseResult for testing."""
        return PhaseResult(
            phase="plan",
            status=PhaseStatus.COMPLETED,
            started_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc),
            tokens_used=500,
        )

    @pytest.fixture
    def setup_run_dir(self, tmp_path: Path) -> Path:
        """Set up run directory structure."""
        runs_dir = tmp_path / ".adw" / "runs"
        run_dir = runs_dir / "01KDSG2VDHNK0W4HSCZWJZXWSQ"
        snapshots_dir = run_dir / "snapshots"
        snapshots_dir.mkdir(parents=True)
        return runs_dir

    def test_load_pre_phase_snapshot(
        self, setup_run_dir: Path, sample_context: RunContext
    ) -> None:
        """Loading pre-phase snapshot returns valid StateSnapshot."""
        manager = SnapshotManager(setup_run_dir)
        manager.create_pre_phase_snapshot(sample_context, "plan")

        snapshot = manager.load_snapshot(sample_context.run_id, 1)

        assert snapshot.label == "pre_plan"
        assert snapshot.phase_result is None
        assert snapshot.context.run_id == sample_context.run_id

    def test_load_post_phase_snapshot(
        self, setup_run_dir: Path, sample_context: RunContext, sample_result: PhaseResult
    ) -> None:
        """Loading post-phase snapshot includes phase result."""
        manager = SnapshotManager(setup_run_dir)
        manager.create_post_phase_snapshot(sample_context, "plan", sample_result)

        snapshot = manager.load_snapshot(sample_context.run_id, 1)

        assert snapshot.label == "post_plan"
        assert snapshot.phase_result is not None
        assert snapshot.phase_result.tokens_used == 500

    def test_load_nonexistent_snapshot_raises(self, setup_run_dir: Path) -> None:
        """Loading nonexistent snapshot raises StateError."""
        manager = SnapshotManager(setup_run_dir)

        with pytest.raises(StateError) as exc_info:
            manager.load_snapshot("01KDSG2VDHNK0W4HSCZWJZXWSQ", 999)

        assert exc_info.value.code == "SNAPSHOT_NOT_FOUND"

    def test_load_corrupted_snapshot_raises(
        self, setup_run_dir: Path, sample_context: RunContext
    ) -> None:
        """Loading corrupted snapshot raises StateError."""
        manager = SnapshotManager(setup_run_dir)
        manager.create_pre_phase_snapshot(sample_context, "plan")

        # Corrupt the snapshot file
        snapshots_dir = setup_run_dir / sample_context.run_id / "snapshots"
        snapshot_file = snapshots_dir / "001_pre_plan.json"
        snapshot_file.write_text("{invalid json")

        with pytest.raises(StateError) as exc_info:
            manager.load_snapshot(sample_context.run_id, 1)

        assert exc_info.value.code == "SNAPSHOT_CORRUPTED"


class TestPerformance:
    """Tests for performance requirements (NFR4)."""

    @pytest.fixture
    def sample_context(self) -> RunContext:
        """Create a sample RunContext for testing."""
        return RunContext(
            run_id="01KDSG2VDHNK0W4HSCZWJZXWSQ",
            feature_description="Add user authentication",
            current_phase="plan",
            started_at=datetime.now(timezone.utc),
        )

    @pytest.fixture
    def setup_run_dir(self, tmp_path: Path) -> Path:
        """Set up run directory structure."""
        runs_dir = tmp_path / ".adw" / "runs"
        run_dir = runs_dir / "01KDSG2VDHNK0W4HSCZWJZXWSQ"
        snapshots_dir = run_dir / "snapshots"
        snapshots_dir.mkdir(parents=True)
        return runs_dir

    def test_snapshot_creation_under_500ms(
        self, setup_run_dir: Path, sample_context: RunContext
    ) -> None:
        """Snapshot creation completes within 500ms (NFR4)."""
        manager = SnapshotManager(setup_run_dir)

        start = time.monotonic()
        manager.create_pre_phase_snapshot(sample_context, "plan")
        elapsed_ms = (time.monotonic() - start) * 1000

        assert elapsed_ms < 500, f"Snapshot took {elapsed_ms}ms, should be <500ms"


class TestSequenceCache:
    """Tests for sequence number caching."""

    @pytest.fixture
    def sample_context(self) -> RunContext:
        """Create a sample RunContext for testing."""
        return RunContext(
            run_id="01KDSG2VDHNK0W4HSCZWJZXWSQ",
            feature_description="Add user authentication",
            current_phase="plan",
            started_at=datetime.now(timezone.utc),
        )

    @pytest.fixture
    def setup_run_dir(self, tmp_path: Path) -> Path:
        """Set up run directory structure."""
        runs_dir = tmp_path / ".adw" / "runs"
        run_dir = runs_dir / "01KDSG2VDHNK0W4HSCZWJZXWSQ"
        snapshots_dir = run_dir / "snapshots"
        snapshots_dir.mkdir(parents=True)
        return runs_dir

    def test_cache_is_populated(
        self, setup_run_dir: Path, sample_context: RunContext
    ) -> None:
        """Sequence cache is populated after first snapshot."""
        manager = SnapshotManager(setup_run_dir)
        assert sample_context.run_id not in manager._sequence_cache

        manager.create_pre_phase_snapshot(sample_context, "plan")

        assert sample_context.run_id in manager._sequence_cache
        assert manager._sequence_cache[sample_context.run_id] == 1

    def test_cache_is_incremented(
        self, setup_run_dir: Path, sample_context: RunContext
    ) -> None:
        """Sequence cache increments with each snapshot."""
        manager = SnapshotManager(setup_run_dir)

        manager.create_pre_phase_snapshot(sample_context, "plan")
        assert manager._sequence_cache[sample_context.run_id] == 1

        manager.create_pre_phase_snapshot(sample_context, "build")
        assert manager._sequence_cache[sample_context.run_id] == 2

        manager.create_pre_phase_snapshot(sample_context, "test")
        assert manager._sequence_cache[sample_context.run_id] == 3
