"""Tests for the Orchestrator class.

This module tests the main orchestrator for ADW pipeline execution,
including phase sequencing, transitions, error handling, and retry logic.
"""

from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

from adw.core.constants import PHASE_SEQUENCE
from adw.exceptions import ADWError, HookError, LLMTimeoutError, PhaseError
from adw.models import RunContext
from adw.models.phase import PhaseResult, PhaseStatus

if TYPE_CHECKING:
    from adw.core.orchestrator import Orchestrator


@pytest.fixture
def mock_context_manager() -> MagicMock:
    """Create a mock ContextManager."""
    manager = MagicMock()
    manager.save = MagicMock()
    return manager


@pytest.fixture
def mock_snapshot_manager() -> MagicMock:
    """Create a mock SnapshotManager."""
    manager = MagicMock()
    manager.create_pre_phase_snapshot = MagicMock(return_value=Path("/tmp/snapshot.json"))
    manager.create_post_phase_snapshot = MagicMock(return_value=Path("/tmp/snapshot.json"))
    return manager


@pytest.fixture
def mock_artifact_manager() -> MagicMock:
    """Create a mock ArtifactManager."""
    manager = MagicMock()
    return manager


@pytest.fixture
def mock_run_directory_manager(tmp_path: Path) -> MagicMock:
    """Create a mock RunDirectoryManager."""
    manager = MagicMock()
    run_dir = tmp_path / "runs" / "01TEST00000000000000000001"
    run_dir.mkdir(parents=True)
    (run_dir / "snapshots").mkdir()
    manager.create_run_directory = MagicMock(return_value=run_dir)
    return manager


@pytest.fixture
def mock_phase_runner() -> MagicMock:
    """Create a mock PhaseRunner."""
    runner = MagicMock()

    def run_side_effect(phase: str, context: RunContext) -> PhaseResult:
        return PhaseResult(
            phase=phase,
            status=PhaseStatus.COMPLETED,
            started_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc),
            tokens_used=100,
        )

    runner.run = MagicMock(side_effect=run_side_effect)
    return runner


@pytest.fixture
def orchestrator(
    tmp_path: Path,
    mock_context_manager: MagicMock,
    mock_snapshot_manager: MagicMock,
    mock_artifact_manager: MagicMock,
    mock_run_directory_manager: MagicMock,
) -> "Orchestrator":
    """Create an Orchestrator instance with mocked dependencies."""
    from adw.core.orchestrator import Orchestrator

    runs_dir = tmp_path / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)

    orch = Orchestrator(
        runs_dir=runs_dir,
        context_manager=mock_context_manager,
        snapshot_manager=mock_snapshot_manager,
        artifact_manager=mock_artifact_manager,
        run_directory_manager=mock_run_directory_manager,
    )
    return orch


class TestOrchestratorInit:
    """Tests for Orchestrator initialization."""

    def test_init_stores_dependencies(
        self,
        tmp_path: Path,
        mock_context_manager: MagicMock,
        mock_snapshot_manager: MagicMock,
        mock_artifact_manager: MagicMock,
        mock_run_directory_manager: MagicMock,
    ) -> None:
        """Test that __init__ stores all dependencies."""
        from adw.core.orchestrator import Orchestrator

        runs_dir = tmp_path / "runs"
        orch = Orchestrator(
            runs_dir=runs_dir,
            context_manager=mock_context_manager,
            snapshot_manager=mock_snapshot_manager,
            artifact_manager=mock_artifact_manager,
            run_directory_manager=mock_run_directory_manager,
        )

        assert orch.runs_dir == runs_dir
        assert orch.context_manager is mock_context_manager
        assert orch.snapshot_manager is mock_snapshot_manager
        assert orch.artifact_manager is mock_artifact_manager
        assert orch.run_directory_manager is mock_run_directory_manager

    def test_init_default_max_retries(
        self,
        tmp_path: Path,
        mock_context_manager: MagicMock,
        mock_snapshot_manager: MagicMock,
        mock_artifact_manager: MagicMock,
        mock_run_directory_manager: MagicMock,
    ) -> None:
        """Test that max_retries defaults to 3."""
        from adw.core.orchestrator import Orchestrator

        orch = Orchestrator(
            runs_dir=tmp_path,
            context_manager=mock_context_manager,
            snapshot_manager=mock_snapshot_manager,
            artifact_manager=mock_artifact_manager,
            run_directory_manager=mock_run_directory_manager,
        )

        assert orch.max_retries == 3

    def test_init_custom_max_retries(
        self,
        tmp_path: Path,
        mock_context_manager: MagicMock,
        mock_snapshot_manager: MagicMock,
        mock_artifact_manager: MagicMock,
        mock_run_directory_manager: MagicMock,
    ) -> None:
        """Test that max_retries can be customized."""
        from adw.core.orchestrator import Orchestrator

        orch = Orchestrator(
            runs_dir=tmp_path,
            context_manager=mock_context_manager,
            snapshot_manager=mock_snapshot_manager,
            artifact_manager=mock_artifact_manager,
            run_directory_manager=mock_run_directory_manager,
            max_retries=5,
        )

        assert orch.max_retries == 5

    def test_init_phase_runner_is_none(
        self,
        orchestrator: "Orchestrator",
    ) -> None:
        """Test that phase runner is initially None."""
        assert orchestrator._phase_runner is None


class TestSetPhaseRunner:
    """Tests for set_phase_runner method."""

    def test_set_phase_runner(
        self,
        orchestrator: "Orchestrator",
        mock_phase_runner: MagicMock,
    ) -> None:
        """Test that set_phase_runner stores the runner."""
        orchestrator.set_phase_runner(mock_phase_runner)
        assert orchestrator._phase_runner is mock_phase_runner


class TestGetNextPhase:
    """Tests for get_next_phase method."""

    def test_get_next_phase_plan(self, orchestrator: "Orchestrator") -> None:
        """Test getting next phase after plan."""
        assert orchestrator.get_next_phase("plan") == "build"

    def test_get_next_phase_build(self, orchestrator: "Orchestrator") -> None:
        """Test getting next phase after build."""
        assert orchestrator.get_next_phase("build") == "verify"

    def test_get_next_phase_verify(self, orchestrator: "Orchestrator") -> None:
        """Test getting next phase after verify."""
        assert orchestrator.get_next_phase("verify") == "validate"

    def test_get_next_phase_validate(self, orchestrator: "Orchestrator") -> None:
        """Test getting next phase after validate."""
        assert orchestrator.get_next_phase("validate") == "document"

    def test_get_next_phase_document_returns_none(self, orchestrator: "Orchestrator") -> None:
        """Test that document is the last phase."""
        assert orchestrator.get_next_phase("document") is None

    def test_get_next_phase_invalid_returns_none(self, orchestrator: "Orchestrator") -> None:
        """Test that invalid phase returns None."""
        assert orchestrator.get_next_phase("invalid") is None


class TestPhaseTransitions:
    """Tests for phase transition logic."""

    def test_transition_persists_state_before_phase(
        self,
        orchestrator: "Orchestrator",
        mock_phase_runner: MagicMock,
        mock_context_manager: MagicMock,
    ) -> None:
        """Test that state is persisted before each phase execution."""
        orchestrator.set_phase_runner(mock_phase_runner)

        # Create a mock context
        context = RunContext(
            run_id="01TEST00000000000000000001",
            feature_description="Test feature",
            current_phase="plan",
            started_at=datetime.now(timezone.utc),
            status="running",
        )

        # Execute a single phase transition
        result_context = orchestrator._execute_phase_with_transitions(context, "plan")

        # Context should have been saved multiple times
        # At minimum: once for updating current_phase, once after completion
        assert mock_context_manager.save.call_count >= 2

    def test_transition_creates_pre_phase_snapshot(
        self,
        orchestrator: "Orchestrator",
        mock_phase_runner: MagicMock,
        mock_snapshot_manager: MagicMock,
    ) -> None:
        """Test that pre-phase snapshot is created."""
        orchestrator.set_phase_runner(mock_phase_runner)

        context = RunContext(
            run_id="01TEST00000000000000000001",
            feature_description="Test feature",
            current_phase="plan",
            started_at=datetime.now(timezone.utc),
            status="running",
        )

        orchestrator._execute_phase_with_transitions(context, "plan")

        mock_snapshot_manager.create_pre_phase_snapshot.assert_called_once()
        call_args = mock_snapshot_manager.create_pre_phase_snapshot.call_args
        assert call_args[0][1] == "plan"  # phase argument

    def test_transition_creates_post_phase_snapshot(
        self,
        orchestrator: "Orchestrator",
        mock_phase_runner: MagicMock,
        mock_snapshot_manager: MagicMock,
    ) -> None:
        """Test that post-phase snapshot is created."""
        orchestrator.set_phase_runner(mock_phase_runner)

        context = RunContext(
            run_id="01TEST00000000000000000001",
            feature_description="Test feature",
            current_phase="plan",
            started_at=datetime.now(timezone.utc),
            status="running",
        )

        orchestrator._execute_phase_with_transitions(context, "plan")

        mock_snapshot_manager.create_post_phase_snapshot.assert_called_once()
        call_args = mock_snapshot_manager.create_post_phase_snapshot.call_args
        assert call_args[0][1] == "plan"  # phase argument

    def test_transition_updates_phase_history(
        self,
        orchestrator: "Orchestrator",
        mock_phase_runner: MagicMock,
    ) -> None:
        """Test that phase_history is updated after transition."""
        orchestrator.set_phase_runner(mock_phase_runner)

        context = RunContext(
            run_id="01TEST00000000000000000001",
            feature_description="Test feature",
            current_phase="plan",
            phase_history=[],
            started_at=datetime.now(timezone.utc),
            status="running",
        )

        result_context = orchestrator._execute_phase_with_transitions(context, "plan")

        assert "plan" in result_context.phase_history

    def test_transition_updates_phase_tokens(
        self,
        orchestrator: "Orchestrator",
        mock_phase_runner: MagicMock,
    ) -> None:
        """Test that phase_tokens is updated after transition."""
        orchestrator.set_phase_runner(mock_phase_runner)

        context = RunContext(
            run_id="01TEST00000000000000000001",
            feature_description="Test feature",
            current_phase="plan",
            phase_tokens={},
            started_at=datetime.now(timezone.utc),
            status="running",
        )

        result_context = orchestrator._execute_phase_with_transitions(context, "plan")

        assert "plan" in result_context.phase_tokens
        assert result_context.phase_tokens["plan"] == 100  # from mock

    def test_transition_returns_updated_context(
        self,
        orchestrator: "Orchestrator",
        mock_phase_runner: MagicMock,
    ) -> None:
        """Test that transition returns an updated context."""
        orchestrator.set_phase_runner(mock_phase_runner)

        context = RunContext(
            run_id="01TEST00000000000000000001",
            feature_description="Test feature",
            current_phase="plan",
            started_at=datetime.now(timezone.utc),
            status="running",
        )

        result_context = orchestrator._execute_phase_with_transitions(context, "plan")

        # Context should be immutably updated (different object)
        assert result_context is not context
        assert "plan" in result_context.phase_history


class TestRun:
    """Tests for the run() method."""

    def test_run_generates_ulid(
        self,
        orchestrator: "Orchestrator",
        mock_phase_runner: MagicMock,
    ) -> None:
        """Test that run generates a valid ULID."""
        orchestrator.set_phase_runner(mock_phase_runner)

        context = orchestrator.run("Test feature")

        # ULID should be 26 characters
        assert len(context.run_id) == 26

    def test_run_creates_run_directory(
        self,
        orchestrator: "Orchestrator",
        mock_phase_runner: MagicMock,
        mock_run_directory_manager: MagicMock,
    ) -> None:
        """Test that run creates the run directory."""
        orchestrator.set_phase_runner(mock_phase_runner)

        orchestrator.run("Test feature")

        mock_run_directory_manager.create.assert_called_once()

    def test_run_executes_all_phases(
        self,
        orchestrator: "Orchestrator",
        mock_phase_runner: MagicMock,
    ) -> None:
        """Test that run executes all phases in order."""
        orchestrator.set_phase_runner(mock_phase_runner)

        context = orchestrator.run("Test feature")

        assert context.status == "completed"
        assert context.phase_history == list(PHASE_SEQUENCE)
        assert mock_phase_runner.run.call_count == len(PHASE_SEQUENCE)

    def test_run_phases_in_order(
        self,
        orchestrator: "Orchestrator",
        mock_phase_runner: MagicMock,
    ) -> None:
        """Test that phases are executed in correct order."""
        orchestrator.set_phase_runner(mock_phase_runner)

        orchestrator.run("Test feature")

        # Verify phases were called in order
        calls = mock_phase_runner.run.call_args_list
        for i, phase in enumerate(PHASE_SEQUENCE):
            assert calls[i][0][0] == phase

    def test_run_sets_completed_status(
        self,
        orchestrator: "Orchestrator",
        mock_phase_runner: MagicMock,
    ) -> None:
        """Test that successful run sets status to completed."""
        orchestrator.set_phase_runner(mock_phase_runner)

        context = orchestrator.run("Test feature")

        assert context.status == "completed"
        assert context.completed_at is not None

    def test_run_persists_final_state(
        self,
        orchestrator: "Orchestrator",
        mock_phase_runner: MagicMock,
        mock_context_manager: MagicMock,
    ) -> None:
        """Test that final state is persisted."""
        orchestrator.set_phase_runner(mock_phase_runner)

        orchestrator.run("Test feature")

        # Final save should have status = "completed"
        last_call = mock_context_manager.save.call_args_list[-1]
        saved_context = last_call[0][0]
        assert saved_context.status == "completed"

    def test_run_stores_feature_description(
        self,
        orchestrator: "Orchestrator",
        mock_phase_runner: MagicMock,
    ) -> None:
        """Test that feature description is stored in context."""
        orchestrator.set_phase_runner(mock_phase_runner)

        context = orchestrator.run("Add user authentication")

        assert context.feature_description == "Add user authentication"

    def test_run_without_phase_runner_raises_error(
        self,
        orchestrator: "Orchestrator",
    ) -> None:
        """Test that run without phase runner raises RuntimeError."""
        # Don't set phase runner

        with pytest.raises(RuntimeError, match="PhaseRunner not set"):
            orchestrator.run("Test feature")

    def test_run_tracks_tokens_per_phase(
        self,
        orchestrator: "Orchestrator",
        mock_phase_runner: MagicMock,
    ) -> None:
        """Test that token usage is tracked per phase."""
        orchestrator.set_phase_runner(mock_phase_runner)

        context = orchestrator.run("Test feature")

        # Each phase should have tokens recorded
        for phase in PHASE_SEQUENCE:
            assert phase in context.phase_tokens
            assert context.phase_tokens[phase] == 100  # from mock


class TestErrorHandling:
    """Tests for error handling behavior."""

    def test_non_recoverable_error_stops_pipeline(
        self,
        orchestrator: "Orchestrator",
        mock_phase_runner: MagicMock,
    ) -> None:
        """Test that non-recoverable errors stop the pipeline."""
        error = HookError(
            code="HOOK_FAILED",
            message="Pre-hook exited with code 1",
            suggestion="Check hook script for errors",
            recoverable=False,
            phase="build",
        )
        mock_phase_runner.run.side_effect = error
        orchestrator.set_phase_runner(mock_phase_runner)

        with pytest.raises(HookError) as exc_info:
            orchestrator.run("Test feature")

        assert exc_info.value.code == "HOOK_FAILED"
        # Should only attempt once for non-recoverable
        assert mock_phase_runner.run.call_count == 1

    def test_non_recoverable_error_sets_failed_status(
        self,
        orchestrator: "Orchestrator",
        mock_phase_runner: MagicMock,
        mock_context_manager: MagicMock,
    ) -> None:
        """Test that non-recoverable error sets status to failed."""
        error = PhaseError(
            code="PHASE_FAILED",
            message="Phase failed",
            suggestion="Check logs",
            recoverable=False,
            phase="plan",
        )
        mock_phase_runner.run.side_effect = error
        orchestrator.set_phase_runner(mock_phase_runner)

        with pytest.raises(PhaseError):
            orchestrator.run("Test feature")

        # Last save should have status = "failed"
        last_call = mock_context_manager.save.call_args_list[-1]
        saved_context = last_call[0][0]
        assert saved_context.status == "failed"

    def test_non_recoverable_error_persists_state(
        self,
        orchestrator: "Orchestrator",
        mock_phase_runner: MagicMock,
        mock_context_manager: MagicMock,
    ) -> None:
        """Test that state is persisted before raising non-recoverable error."""
        error = HookError(
            code="HOOK_FAILED",
            message="Pre-hook failed",
            suggestion="Check hook",
            recoverable=False,
            phase="build",
        )
        mock_phase_runner.run.side_effect = error
        orchestrator.set_phase_runner(mock_phase_runner)

        with pytest.raises(HookError):
            orchestrator.run("Test feature")

        # Context should have been saved with failed status
        saved_contexts = [call[0][0] for call in mock_context_manager.save.call_args_list]
        failed_saves = [c for c in saved_contexts if c.status == "failed"]
        assert len(failed_saves) >= 1

    def test_error_on_first_phase(
        self,
        orchestrator: "Orchestrator",
        mock_phase_runner: MagicMock,
    ) -> None:
        """Test handling of error on first phase."""
        error = HookError(
            code="HOOK_FAILED",
            message="Plan phase failed",
            suggestion="Check hook",
            recoverable=False,
            phase="plan",
        )
        mock_phase_runner.run.side_effect = error
        orchestrator.set_phase_runner(mock_phase_runner)

        with pytest.raises(HookError):
            orchestrator.run("Test feature")

        # Only the first phase should have been attempted
        assert mock_phase_runner.run.call_count == 1

    def test_error_on_middle_phase(
        self,
        orchestrator: "Orchestrator",
        mock_phase_runner: MagicMock,
    ) -> None:
        """Test handling of error on middle phase (build)."""
        call_count = 0

        def side_effect(phase: str, context: RunContext) -> PhaseResult:
            nonlocal call_count
            call_count += 1
            if phase == "build":
                raise HookError(
                    code="HOOK_FAILED",
                    message="Build phase failed",
                    suggestion="Check hook",
                    recoverable=False,
                    phase="build",
                )
            return PhaseResult(
                phase=phase,
                status=PhaseStatus.COMPLETED,
                started_at=datetime.now(timezone.utc),
                completed_at=datetime.now(timezone.utc),
                tokens_used=100,
            )

        mock_phase_runner.run.side_effect = side_effect
        orchestrator.set_phase_runner(mock_phase_runner)

        with pytest.raises(HookError):
            orchestrator.run("Test feature")

        # Plan succeeded, build failed
        assert call_count == 2
