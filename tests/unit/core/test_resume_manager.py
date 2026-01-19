"""Tests for ResumeManager centralized resume logic.

Tests verify ResumeManager consolidates resume behavior correctly:
- can_resume: checks completion status
- validate_resumable: validates resume preconditions
- find_run_to_resume: finds by ID or most recent incomplete
- get_resume_phase: determines phase to resume from
- prepare_for_resume: prepares context for execution
- get_resume_status: returns status summary
"""

from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import MagicMock, create_autospec

import pytest

from adw.core.context_manager import ContextManager
from adw.core.resume_manager import ResumeManager
from adw.core.run_lookup import RunLookup
from adw.exceptions import ConfigError, StateError
from adw.models import RunContext

# Valid 26-character ULIDs for testing (Crockford Base32 - no I,L,O,U)
SAMPLE_RUN_ID = "01HQTEST1234567890ABCDEF12"
INTERRUPTED_RUN_ID = "01HQTEST789ABC000000001234"
COMPLETED_RUN_ID = "01HQTESTD0NE00000000001234"


@pytest.fixture
def runs_dir(tmp_path: Path) -> Path:
    """Create a temporary runs directory."""
    runs = tmp_path / ".adw" / "runs"
    runs.mkdir(parents=True)
    return runs


@pytest.fixture
def mock_run_lookup() -> MagicMock:
    """Create a mock RunLookup."""
    return create_autospec(RunLookup, instance=True)


@pytest.fixture
def mock_context_manager() -> MagicMock:
    """Create a mock ContextManager."""
    return create_autospec(ContextManager, instance=True)


@pytest.fixture
def resume_manager(
    runs_dir: Path,
    mock_run_lookup: MagicMock,
    mock_context_manager: MagicMock,
) -> ResumeManager:
    """Create a ResumeManager with mocked dependencies."""
    return ResumeManager(
        runs_dir=runs_dir,
        run_lookup=mock_run_lookup,
        context_manager=mock_context_manager,
    )


@pytest.fixture
def sample_context() -> RunContext:
    """Create a sample run context for testing."""
    return RunContext(
        run_id=SAMPLE_RUN_ID,
        feature_description="Test feature",
        current_phase="build",
        status="running",
        phase_history=["plan"],
        started_at=datetime.now(UTC),
    )


@pytest.fixture
def interrupted_context() -> RunContext:
    """Create an interrupted run context."""
    return RunContext(
        run_id=INTERRUPTED_RUN_ID,
        feature_description="Interrupted feature",
        current_phase="build",
        status="interrupted",
        phase_history=["plan"],
        interrupted_phase="build",
        interrupted_at=datetime.now(UTC),
        started_at=datetime.now(UTC),
    )


@pytest.fixture
def completed_context() -> RunContext:
    """Create a completed run context."""
    return RunContext(
        run_id=COMPLETED_RUN_ID,
        feature_description="Completed feature",
        current_phase="document",
        status="completed",
        phase_history=["plan", "build", "validate", "document"],
        started_at=datetime.now(UTC),
        completed_at=datetime.now(UTC),
    )


class TestCanResume:
    """Tests for can_resume method."""

    def test_running_can_resume(
        self, resume_manager: ResumeManager, sample_context: RunContext
    ) -> None:
        """Running run can be resumed."""
        assert resume_manager.can_resume(sample_context) is True

    def test_interrupted_can_resume(
        self, resume_manager: ResumeManager, interrupted_context: RunContext
    ) -> None:
        """Interrupted run can be resumed."""
        assert resume_manager.can_resume(interrupted_context) is True

    def test_failed_can_resume(
        self, resume_manager: ResumeManager, sample_context: RunContext
    ) -> None:
        """Failed run can be resumed."""
        failed = sample_context.model_copy(update={"status": "failed"})
        assert resume_manager.can_resume(failed) is True

    def test_completed_cannot_resume(
        self, resume_manager: ResumeManager, completed_context: RunContext
    ) -> None:
        """Completed run cannot be resumed."""
        assert resume_manager.can_resume(completed_context) is False


class TestValidateResumable:
    """Tests for validate_resumable method."""

    def test_running_passes_validation(
        self, resume_manager: ResumeManager, sample_context: RunContext
    ) -> None:
        """Running context passes validation."""
        resume_manager.validate_resumable(sample_context)  # Should not raise

    def test_completed_fails_validation(
        self, resume_manager: ResumeManager, completed_context: RunContext
    ) -> None:
        """Completed context raises ConfigError."""
        with pytest.raises(ConfigError) as exc_info:
            resume_manager.validate_resumable(completed_context)
        assert exc_info.value.code == "RUN_COMPLETED"

    def test_invalid_phase_fails_validation(
        self, resume_manager: ResumeManager, sample_context: RunContext
    ) -> None:
        """Invalid from_phase raises ConfigError."""
        with pytest.raises(ConfigError) as exc_info:
            resume_manager.validate_resumable(sample_context, from_phase="invalid")
        assert exc_info.value.code == "INVALID_PHASE"

    def test_valid_phase_passes_validation(
        self, resume_manager: ResumeManager, sample_context: RunContext
    ) -> None:
        """Valid from_phase passes validation."""
        resume_manager.validate_resumable(
            sample_context, from_phase="build"
        )  # Should not raise


class TestFindRunToResume:
    """Tests for find_run_to_resume method."""

    def test_find_by_id_returns_info(
        self,
        resume_manager: ResumeManager,
        mock_run_lookup: MagicMock,
        sample_context: RunContext,
    ) -> None:
        """Finding by ID returns valid ResumeInfo."""
        mock_run_lookup.find_by_id.return_value = sample_context

        info = resume_manager.find_run_to_resume(run_id=SAMPLE_RUN_ID)

        assert info.is_valid
        assert info.run_id == SAMPLE_RUN_ID
        assert info.resume_phase == "build"
        mock_run_lookup.find_by_id.assert_called_once_with(SAMPLE_RUN_ID)

    def test_find_most_recent_incomplete(
        self,
        resume_manager: ResumeManager,
        mock_run_lookup: MagicMock,
        sample_context: RunContext,
    ) -> None:
        """Finding most recent incomplete returns valid ResumeInfo."""
        mock_run_lookup.find_most_recent_incomplete.return_value = sample_context

        info = resume_manager.find_run_to_resume()

        assert info.is_valid
        assert info.run_id == SAMPLE_RUN_ID
        mock_run_lookup.find_most_recent_incomplete.assert_called_once()

    def test_run_not_found_raises(
        self,
        resume_manager: ResumeManager,
        mock_run_lookup: MagicMock,
        runs_dir: Path,
    ) -> None:
        """Run not found raises ConfigError."""
        mock_run_lookup.find_by_id.return_value = None

        with pytest.raises(ConfigError) as exc_info:
            resume_manager.find_run_to_resume(run_id="nonexistent")
        assert exc_info.value.code == "RUN_NOT_FOUND"

    def test_corrupted_state_raises(
        self,
        resume_manager: ResumeManager,
        mock_run_lookup: MagicMock,
        runs_dir: Path,
    ) -> None:
        """Corrupted state raises StateError."""
        mock_run_lookup.find_by_id.return_value = None
        # Create the run directory to simulate corrupted state
        (runs_dir / "corrupted_run").mkdir()

        with pytest.raises(StateError) as exc_info:
            resume_manager.find_run_to_resume(run_id="corrupted_run")
        assert exc_info.value.code == "STATE_CORRUPTED"

    def test_no_incomplete_runs_raises(
        self,
        resume_manager: ResumeManager,
        mock_run_lookup: MagicMock,
    ) -> None:
        """No incomplete runs raises ConfigError."""
        mock_run_lookup.find_most_recent_incomplete.return_value = None

        with pytest.raises(ConfigError) as exc_info:
            resume_manager.find_run_to_resume()
        assert exc_info.value.code == "NO_INCOMPLETE_RUNS"

    def test_completed_returns_invalid_info(
        self,
        resume_manager: ResumeManager,
        mock_run_lookup: MagicMock,
        completed_context: RunContext,
    ) -> None:
        """Completed run returns invalid ResumeInfo."""
        mock_run_lookup.find_by_id.return_value = completed_context

        info = resume_manager.find_run_to_resume(run_id=COMPLETED_RUN_ID)

        assert not info.is_valid
        assert "already completed" in info.validation_error.lower()


class TestGetResumePhase:
    """Tests for get_resume_phase method."""

    def test_completed_returns_none(
        self, resume_manager: ResumeManager, completed_context: RunContext
    ) -> None:
        """Completed run returns None."""
        assert resume_manager.get_resume_phase(completed_context) is None

    def test_interrupted_returns_interrupted_phase(
        self, resume_manager: ResumeManager, interrupted_context: RunContext
    ) -> None:
        """Interrupted run returns interrupted_phase."""
        assert resume_manager.get_resume_phase(interrupted_context) == "build"

    def test_running_returns_next_uncompleted(
        self, resume_manager: ResumeManager, sample_context: RunContext
    ) -> None:
        """Running run returns next uncompleted phase."""
        # phase_history=["plan"], so next should be "build"
        assert resume_manager.get_resume_phase(sample_context) == "build"

    def test_all_phases_complete_returns_none(
        self, resume_manager: ResumeManager, sample_context: RunContext
    ) -> None:
        """All phases complete returns None."""
        all_done = sample_context.model_copy(
            update={
                # Story 15.1: ship is now the 5th phase
                "phase_history": ["plan", "build", "validate", "document", "ship"],
                "status": "running",  # Not completed status but all phases done
            }
        )
        assert resume_manager.get_resume_phase(all_done) is None


class TestPrepareForResume:
    """Tests for prepare_for_resume method."""

    def test_sets_status_running(
        self, resume_manager: ResumeManager, sample_context: RunContext
    ) -> None:
        """Prepared context has running status."""
        prepared = resume_manager.prepare_for_resume(sample_context)
        assert prepared.status == "running"

    def test_clears_interrupted_fields(
        self, resume_manager: ResumeManager, interrupted_context: RunContext
    ) -> None:
        """Prepared context clears interrupted fields."""
        prepared = resume_manager.prepare_for_resume(interrupted_context)
        assert prepared.interrupted_phase is None
        assert prepared.interrupted_at is None

    def test_preserves_phase_history(
        self, resume_manager: ResumeManager, sample_context: RunContext
    ) -> None:
        """Prepared context preserves phase_history."""
        prepared = resume_manager.prepare_for_resume(sample_context)
        assert prepared.phase_history == sample_context.phase_history

    def test_completed_raises(
        self, resume_manager: ResumeManager, completed_context: RunContext
    ) -> None:
        """Completed context raises ConfigError."""
        with pytest.raises(ConfigError) as exc_info:
            resume_manager.prepare_for_resume(completed_context)
        assert exc_info.value.code == "RUN_COMPLETED"

    def test_invalid_phase_raises(
        self, resume_manager: ResumeManager, sample_context: RunContext
    ) -> None:
        """Invalid from_phase raises ConfigError."""
        with pytest.raises(ConfigError) as exc_info:
            resume_manager.prepare_for_resume(sample_context, from_phase="bogus")
        assert exc_info.value.code == "INVALID_PHASE"

    def test_from_phase_with_later_phases_completed(
        self, resume_manager: ResumeManager, sample_context: RunContext
    ) -> None:
        """From_phase override works when later phases are already completed.

        When resuming from an earlier phase, the run should still be able
        to re-execute from that phase even if it was previously completed.
        """
        # Context with plan and build completed
        context_with_history = sample_context.model_copy(
            update={
                "phase_history": ["plan", "build"],
                "current_phase": "validate",
                "status": "failed",
            }
        )

        # Resume from "plan" even though it's already in phase_history
        prepared = resume_manager.prepare_for_resume(
            context_with_history, from_phase="plan"
        )

        # Should succeed - status set to running
        assert prepared.status == "running"
        # Phase history is preserved (orchestrator loop uses index, not history)
        assert "plan" in prepared.phase_history


class TestGetResumeStatus:
    """Tests for get_resume_status method."""

    def test_returns_status_dataclass(
        self, resume_manager: ResumeManager, sample_context: RunContext
    ) -> None:
        """Returns ResumeStatus with correct fields."""
        status = resume_manager.get_resume_status(sample_context)

        assert status.run_id == sample_context.run_id
        assert status.status == "running"
        assert status.current_phase == "build"
        assert status.can_resume is True
        assert status.resume_phase == "build"
        assert status.completed_phases == ["plan"]

    def test_interrupted_status(
        self, resume_manager: ResumeManager, interrupted_context: RunContext
    ) -> None:
        """Interrupted context returns correct status."""
        status = resume_manager.get_resume_status(interrupted_context)

        assert status.status == "interrupted"
        assert status.interrupted_phase == "build"
        assert status.can_resume is True
        assert status.resume_phase == "build"

    def test_completed_status(
        self, resume_manager: ResumeManager, completed_context: RunContext
    ) -> None:
        """Completed context returns correct status."""
        status = resume_manager.get_resume_status(completed_context)

        assert status.status == "completed"
        assert status.can_resume is False
        assert status.resume_phase is None

    def test_to_dict_conversion(
        self, resume_manager: ResumeManager, sample_context: RunContext
    ) -> None:
        """Status converts to dictionary correctly."""
        status = resume_manager.get_resume_status(sample_context)
        as_dict = status.to_dict()

        assert as_dict["run_id"] == sample_context.run_id
        assert as_dict["status"] == "running"
        assert as_dict["can_resume"] is True
