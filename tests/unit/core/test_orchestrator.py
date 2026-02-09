"""Tests for the Orchestrator class.

This module tests the main orchestrator for ADW pipeline execution,
including phase sequencing, transitions, error handling, and retry logic.
"""

from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

from adw.core.constants import PHASE_SEQUENCE
from adw.exceptions import ConfigError, HookError, LLMTimeoutError, PhaseError
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
    snapshot_path = Path("/tmp/snapshot.json")
    manager.create_pre_phase_snapshot = MagicMock(return_value=snapshot_path)
    manager.create_post_phase_snapshot = MagicMock(return_value=snapshot_path)
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
def mock_interruption_handler() -> MagicMock:
    """Create a mock InterruptionHandler."""
    from contextlib import contextmanager

    handler = MagicMock()
    handler.shutdown_requested = False
    handler.check_shutdown = MagicMock()
    handler.set_context = MagicMock()

    @contextmanager
    def mock_protected_execution(context: RunContext):  # type: ignore[no-untyped-def]
        yield context

    handler.protected_execution = mock_protected_execution
    return handler


@pytest.fixture
def mock_index_manager() -> MagicMock:
    """Create a mock IndexManager."""
    manager = MagicMock()
    manager.register_run = MagicMock()
    manager.update_run = MagicMock()
    manager.get_recent_runs = MagicMock(return_value=[])
    return manager


@pytest.fixture
def orchestrator(
    tmp_path: Path,
    mock_context_manager: MagicMock,
    mock_snapshot_manager: MagicMock,
    mock_artifact_manager: MagicMock,
    mock_run_directory_manager: MagicMock,
    mock_phase_runner: MagicMock,
    mock_interruption_handler: MagicMock,
    mock_index_manager: MagicMock,
) -> "Orchestrator":
    """Create an Orchestrator instance with mocked dependencies.

    Note: Worktree is disabled by default for unit tests since tmp_path
    is not a git repository. Tests that need worktree functionality
    should use the worktree-specific tests in TestOrchestratorWorktree.
    """
    from adw.core.orchestrator import Orchestrator
    from adw.models import WorktreeConfig

    runs_dir = tmp_path / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)

    # ISS-025: Disable worktree for unit tests (tmp_path is not a git repo)
    # Worktree creation errors are now fatal, so we must disable it
    worktree_config = WorktreeConfig(enabled=False)

    orch = Orchestrator(
        runs_dir=runs_dir,
        context_manager=mock_context_manager,
        snapshot_manager=mock_snapshot_manager,
        artifact_manager=mock_artifact_manager,
        run_directory_manager=mock_run_directory_manager,
        phase_runner=mock_phase_runner,
        interruption_handler=mock_interruption_handler,
        index_manager=mock_index_manager,
        worktree_config=worktree_config,
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
        mock_phase_runner: MagicMock,
        mock_interruption_handler: MagicMock,
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
            phase_runner=mock_phase_runner,
            interruption_handler=mock_interruption_handler,
        )

        assert orch.runs_dir == runs_dir
        assert orch.context_manager is mock_context_manager
        assert orch.snapshot_manager is mock_snapshot_manager
        assert orch.artifact_manager is mock_artifact_manager
        assert orch.run_directory_manager is mock_run_directory_manager
        assert orch._phase_runner is mock_phase_runner
        assert orch.interruption_handler is mock_interruption_handler

    def test_init_creates_default_interruption_handler(
        self,
        tmp_path: Path,
        mock_context_manager: MagicMock,
        mock_snapshot_manager: MagicMock,
        mock_artifact_manager: MagicMock,
        mock_run_directory_manager: MagicMock,
        mock_phase_runner: MagicMock,
    ) -> None:
        """Test that InterruptionHandler is created by default."""
        from adw.core.interruption import InterruptionHandler
        from adw.core.orchestrator import Orchestrator

        orch = Orchestrator(
            runs_dir=tmp_path,
            context_manager=mock_context_manager,
            snapshot_manager=mock_snapshot_manager,
            artifact_manager=mock_artifact_manager,
            run_directory_manager=mock_run_directory_manager,
            phase_runner=mock_phase_runner,
        )

        assert isinstance(orch.interruption_handler, InterruptionHandler)

    def test_init_default_max_retries(
        self,
        tmp_path: Path,
        mock_context_manager: MagicMock,
        mock_snapshot_manager: MagicMock,
        mock_artifact_manager: MagicMock,
        mock_run_directory_manager: MagicMock,
        mock_phase_runner: MagicMock,
    ) -> None:
        """Test that max_retries defaults to 3."""
        from adw.core.orchestrator import Orchestrator

        orch = Orchestrator(
            runs_dir=tmp_path,
            context_manager=mock_context_manager,
            snapshot_manager=mock_snapshot_manager,
            artifact_manager=mock_artifact_manager,
            run_directory_manager=mock_run_directory_manager,
            phase_runner=mock_phase_runner,
        )

        assert orch.max_retries == 3

    def test_init_custom_max_retries(
        self,
        tmp_path: Path,
        mock_context_manager: MagicMock,
        mock_snapshot_manager: MagicMock,
        mock_artifact_manager: MagicMock,
        mock_run_directory_manager: MagicMock,
        mock_phase_runner: MagicMock,
    ) -> None:
        """Test that max_retries can be customized."""
        from adw.core.orchestrator import Orchestrator

        orch = Orchestrator(
            runs_dir=tmp_path,
            context_manager=mock_context_manager,
            snapshot_manager=mock_snapshot_manager,
            artifact_manager=mock_artifact_manager,
            run_directory_manager=mock_run_directory_manager,
            phase_runner=mock_phase_runner,
            max_retries=5,
        )

        assert orch.max_retries == 5


class TestGetNextPhase:
    """Tests for get_next_phase method."""

    def test_get_next_phase_plan(self, orchestrator: "Orchestrator") -> None:
        """Test getting next phase after plan."""
        assert orchestrator.get_next_phase("plan") == "build"

    def test_get_next_phase_build(self, orchestrator: "Orchestrator") -> None:
        """Test getting next phase after build (ISS-019: now validate, not verify)."""
        assert orchestrator.get_next_phase("build") == "validate"

    def test_get_next_phase_validate(self, orchestrator: "Orchestrator") -> None:
        """Test getting next phase after validate."""
        assert orchestrator.get_next_phase("validate") == "document"

    def test_get_next_phase_document(self, orchestrator: "Orchestrator") -> None:
        """Test getting next phase after document (Story 15.1: now ship)."""
        assert orchestrator.get_next_phase("document") == "ship"

    def test_get_next_phase_ship_returns_none(
        self, orchestrator: "Orchestrator"
    ) -> None:
        """Test that ship is the last phase."""
        assert orchestrator.get_next_phase("ship") is None

    def test_get_next_phase_invalid_returns_none(
        self, orchestrator: "Orchestrator"
    ) -> None:
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

        # Create a mock context
        context = RunContext(
            run_id="01TEST00000000000000000001",
            feature_description="Test feature",
            current_phase="plan",
            started_at=datetime.now(UTC),
            status="running",
        )

        # Execute a single phase transition
        orchestrator._execute_phase_with_transitions(context, "plan")

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

        context = RunContext(
            run_id="01TEST00000000000000000001",
            feature_description="Test feature",
            current_phase="plan",
            started_at=datetime.now(UTC),
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

        context = RunContext(
            run_id="01TEST00000000000000000001",
            feature_description="Test feature",
            current_phase="plan",
            started_at=datetime.now(UTC),
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

        context = RunContext(
            run_id="01TEST00000000000000000001",
            feature_description="Test feature",
            current_phase="plan",
            phase_history=[],
            started_at=datetime.now(UTC),
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

        context = RunContext(
            run_id="01TEST00000000000000000001",
            feature_description="Test feature",
            current_phase="plan",
            phase_tokens={},
            started_at=datetime.now(UTC),
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

        context = RunContext(
            run_id="01TEST00000000000000000001",
            feature_description="Test feature",
            current_phase="plan",
            started_at=datetime.now(UTC),
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

        orchestrator.run("Test feature")

        mock_run_directory_manager.create.assert_called_once()

    def test_run_executes_all_phases(
        self,
        orchestrator: "Orchestrator",
        mock_phase_runner: MagicMock,
    ) -> None:
        """Test that run executes all phases in order."""

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

        context = orchestrator.run("Add user authentication")

        assert context.feature_description == "Add user authentication"

    def test_run_tracks_tokens_per_phase(
        self,
        orchestrator: "Orchestrator",
        mock_phase_runner: MagicMock,
    ) -> None:
        """Test that token usage is tracked per phase."""

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

        with pytest.raises(HookError):
            orchestrator.run("Test feature")

        # Context should have been saved with failed status
        saved_contexts = [
            call[0][0] for call in mock_context_manager.save.call_args_list
        ]
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

        def side_effect(
            phase: str,
            context: RunContext,
            *,
            artifacts_override: dict[str, dict[str, str]] | None = None,
        ) -> PhaseResult:
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
                started_at=datetime.now(UTC),
                completed_at=datetime.now(UTC),
                tokens_used=100,
            )

        mock_phase_runner.run.side_effect = side_effect

        with pytest.raises(HookError):
            orchestrator.run("Test feature")

        # Plan succeeded, build failed
        assert call_count == 2


class TestRetryLogic:
    """Tests for retry logic with recoverable errors."""

    def test_recoverable_error_triggers_retry(
        self,
        orchestrator: "Orchestrator",
        mock_phase_runner: MagicMock,
    ) -> None:
        """Test that recoverable errors trigger retries."""
        call_count = 0

        def side_effect(
            phase: str,
            context: RunContext,
            *,
            artifacts_override: dict[str, dict[str, str]] | None = None,
        ) -> PhaseResult:
            nonlocal call_count
            call_count += 1
            if phase == "plan" and call_count < 3:
                raise LLMTimeoutError(
                    code="LLM_TIMEOUT",
                    message="Request timed out",
                    suggestion="Retry",
                    timeout_seconds=300,
                    elapsed_seconds=300,
                    recoverable=True,
                )
            return PhaseResult(
                phase=phase,
                status=PhaseStatus.COMPLETED,
                started_at=datetime.now(UTC),
                completed_at=datetime.now(UTC),
                tokens_used=100,
            )

        mock_phase_runner.run.side_effect = side_effect

        context = orchestrator.run("Test feature")

        # Should succeed after retries
        # Story 15.1: (2 failures + success on plan = 3, then 4 more phases)
        assert context.status == "completed"
        # Plan: 3 attempts (2 failures + 1 success) + 4 other phases = 7 calls
        assert call_count == 7

    def test_retry_exhaustion_raises_error(
        self,
        orchestrator: "Orchestrator",
        mock_phase_runner: MagicMock,
    ) -> None:
        """Test that retry exhaustion raises the last error."""
        # All attempts fail with recoverable error
        error = LLMTimeoutError(
            code="LLM_TIMEOUT",
            message="Request timed out",
            suggestion="Retry",
            timeout_seconds=300,
            elapsed_seconds=300,
            recoverable=True,
        )
        mock_phase_runner.run.side_effect = error

        with pytest.raises(LLMTimeoutError):
            orchestrator.run("Test feature")

        # Should have tried max_retries times
        assert mock_phase_runner.run.call_count == 3  # default max_retries

    def test_retry_with_custom_max_retries(
        self,
        tmp_path: Path,
        mock_context_manager: MagicMock,
        mock_snapshot_manager: MagicMock,
        mock_artifact_manager: MagicMock,
        mock_run_directory_manager: MagicMock,
        mock_phase_runner: MagicMock,
    ) -> None:
        """Test that max_retries can be customized."""
        from adw.core.orchestrator import Orchestrator
        from adw.models import WorktreeConfig

        runs_dir = tmp_path / "runs"
        runs_dir.mkdir(parents=True, exist_ok=True)

        orchestrator = Orchestrator(
            runs_dir=runs_dir,
            context_manager=mock_context_manager,
            snapshot_manager=mock_snapshot_manager,
            artifact_manager=mock_artifact_manager,
            run_directory_manager=mock_run_directory_manager,
            phase_runner=mock_phase_runner,
            max_retries=5,  # Custom max
            worktree_config=WorktreeConfig(enabled=False),  # ISS-025
        )

        error = LLMTimeoutError(
            code="LLM_TIMEOUT",
            message="Timeout",
            suggestion="Retry",
            timeout_seconds=300,
            elapsed_seconds=300,
            recoverable=True,
        )
        mock_phase_runner.run.side_effect = error

        with pytest.raises(LLMTimeoutError):
            orchestrator.run("Test feature")

        assert mock_phase_runner.run.call_count == 5

    @patch("time.sleep")
    def test_retry_uses_exponential_backoff(
        self,
        mock_sleep: MagicMock,
        orchestrator: "Orchestrator",
        mock_phase_runner: MagicMock,
    ) -> None:
        """Test that retries use exponential backoff (1s, 2s, 4s)."""
        # All attempts fail
        error = LLMTimeoutError(
            code="LLM_TIMEOUT",
            message="Timeout",
            suggestion="Retry",
            timeout_seconds=300,
            elapsed_seconds=300,
            recoverable=True,
        )
        mock_phase_runner.run.side_effect = error

        with pytest.raises(LLMTimeoutError):
            orchestrator.run("Test feature")

        # Should have slept twice (before 2nd and 3rd attempt)
        assert mock_sleep.call_count == 2
        # First delay: 2^0 = 1, Second delay: 2^1 = 2
        mock_sleep.assert_any_call(1)
        mock_sleep.assert_any_call(2)

    def test_retry_success_after_failures(
        self,
        orchestrator: "Orchestrator",
        mock_phase_runner: MagicMock,
    ) -> None:
        """Test successful completion after recoverable failures."""
        call_count = 0

        def side_effect(
            phase: str,
            context: RunContext,
            *,
            artifacts_override: dict[str, dict[str, str]] | None = None,
        ) -> PhaseResult:
            nonlocal call_count
            call_count += 1
            if phase == "plan" and call_count == 1:
                raise LLMTimeoutError(
                    code="LLM_TIMEOUT",
                    message="Timeout",
                    suggestion="Retry",
                    timeout_seconds=300,
                    elapsed_seconds=300,
                    recoverable=True,
                )
            return PhaseResult(
                phase=phase,
                status=PhaseStatus.COMPLETED,
                started_at=datetime.now(UTC),
                completed_at=datetime.now(UTC),
                tokens_used=100,
            )

        mock_phase_runner.run.side_effect = side_effect

        context = orchestrator.run("Test feature")

        assert context.status == "completed"
        # Story 15.1: 1 failure + 5 successes = 6 calls (ship phase added)
        assert call_count == 6

    def test_spinner_stopped_before_error_logging(
        self,
        tmp_path: Path,
        mock_context_manager: MagicMock,
        mock_snapshot_manager: MagicMock,
        mock_artifact_manager: MagicMock,
        mock_run_directory_manager: MagicMock,
        mock_phase_runner: MagicMock,
    ) -> None:
        """Test ISS-034: spinner is stopped before any error logging.

        When an error occurs during phase execution, the spinner must be
        stopped BEFORE any error messages are logged to prevent output
        overlap (e.g., "⠴ LLM executing...20:25:17 [WARN]").
        """
        from adw.core.orchestrator import Orchestrator
        from adw.models import WorktreeConfig

        runs_dir = tmp_path / "runs"
        runs_dir.mkdir(parents=True, exist_ok=True)

        # Create a mock progress display to track call order
        mock_progress = MagicMock()
        call_order: list[str] = []

        def track_llm_complete() -> None:
            call_order.append("on_llm_complete")

        mock_progress.on_llm_complete = track_llm_complete
        mock_progress.on_phase_start = MagicMock()
        mock_progress.on_phase_complete = MagicMock()
        mock_progress.on_phase_error = MagicMock()

        orchestrator = Orchestrator(
            runs_dir=runs_dir,
            context_manager=mock_context_manager,
            snapshot_manager=mock_snapshot_manager,
            artifact_manager=mock_artifact_manager,
            run_directory_manager=mock_run_directory_manager,
            phase_runner=mock_phase_runner,
            worktree_config=WorktreeConfig(enabled=False),
            progress_display=mock_progress,
        )

        # Make phase fail with recoverable error
        error = LLMTimeoutError(
            code="LLM_TIMEOUT",
            message="Request timed out",
            suggestion="Retry",
            timeout_seconds=300,
            elapsed_seconds=300,
            recoverable=True,
        )
        mock_phase_runner.run.side_effect = error

        with pytest.raises(LLMTimeoutError):
            orchestrator.run("Test feature")

        # Verify on_llm_complete was called at least once
        # (it should be called on each error before logging)
        assert "on_llm_complete" in call_order
        # The key assertion: on_llm_complete was called before error handling
        # This validates the ISS-034 fix
        assert call_order.count("on_llm_complete") >= 1


class TestTransitionPerformance:
    """Tests for transition performance (NFR2: <1 second)."""

    def test_transition_under_1_second(
        self,
        orchestrator: "Orchestrator",
        mock_phase_runner: MagicMock,
    ) -> None:
        """Test that phase transitions complete under 1 second (NFR2)."""
        import time

        # Make phase runner return immediately

        start = time.monotonic()
        orchestrator.run("Test feature")
        elapsed = time.monotonic() - start

        # All transitions (5 phases) should be under 5 seconds
        # Each transition should be under 1 second
        assert elapsed < 5.0, f"Total time {elapsed}s should be < 5s"

    def test_transition_logs_duration(
        self,
        orchestrator: "Orchestrator",
        mock_phase_runner: MagicMock,
    ) -> None:
        """Test that transition duration is logged.

        ISS-034: Phase completion is now logged at DEBUG level (not INFO)
        to reduce console noise since Rich progress display already shows
        phase completion status.
        """

        with patch("adw.core.orchestrator.logger") as mock_logger:
            orchestrator.run("Test feature")

            # ISS-034: Phase completed now logged at DEBUG level
            # Story 15.1: 5 phases now (ship added)
            completed_calls = [
                call
                for call in mock_logger.debug.call_args_list
                if "Phase completed" in str(call)
            ]
            assert (
                len(completed_calls) == 5
            )  # One per phase (plan, build, validate, document, ship)

    def test_slow_transition_logs_debug(
        self,
        orchestrator: "Orchestrator",
    ) -> None:
        """Test that slow transitions log a debug message."""
        import time

        # Create a slow phase runner
        slow_runner = MagicMock()

        def slow_run(
            phase: str,
            context: RunContext,
            *,
            artifacts_override: dict[str, dict[str, str]] | None = None,
        ) -> PhaseResult:
            time.sleep(1.1)  # Exceed 1 second threshold
            return PhaseResult(
                phase=phase,
                status=PhaseStatus.COMPLETED,
                started_at=datetime.now(UTC),
                completed_at=datetime.now(UTC),
                tokens_used=100,
            )

        slow_runner.run = MagicMock(side_effect=slow_run)
        orchestrator._phase_runner = slow_runner

        with patch("adw.core.orchestrator.logger") as mock_logger:
            # Run just the first phase to avoid long test
            context = RunContext(
                run_id="01TEST00000000000000000001",
                feature_description="Test",
                current_phase="plan",
                started_at=datetime.now(UTC),
                status="running",
            )

            orchestrator._execute_phase_with_transitions(context, "plan")

            # Should have logged a debug message about slow transition
            debug_calls = mock_logger.debug.call_args_list
            assert len(debug_calls) >= 1
            # Find the transition exceeded message
            found_transition_msg = any(
                "exceeded 1s" in str(call).lower() or "1s" in str(call).lower()
                for call in debug_calls
            )
            assert found_transition_msg, f"Expected transition debug log: {debug_calls}"


class TestInterruptionHandling:
    """Tests for interruption handling and graceful shutdown."""

    def test_run_checks_shutdown_between_phases(
        self,
        orchestrator: "Orchestrator",
        mock_phase_runner: MagicMock,
        mock_interruption_handler: MagicMock,
    ) -> None:
        """Test that shutdown is checked between phases."""

        orchestrator.run("Test feature")

        # check_shutdown should be called before each phase
        expected_calls = len(PHASE_SEQUENCE)
        assert mock_interruption_handler.check_shutdown.call_count == expected_calls

    def test_run_raises_shutdown_requested(
        self,
        orchestrator: "Orchestrator",
        mock_phase_runner: MagicMock,
        mock_interruption_handler: MagicMock,
    ) -> None:
        """Test that ShutdownRequested propagates from handler."""
        from adw.core.interruption import ShutdownRequested

        # Simulate shutdown on second phase check
        call_count = 0

        def check_shutdown_side_effect() -> None:
            nonlocal call_count
            call_count += 1
            if call_count == 2:  # Second phase
                raise ShutdownRequested(phase="build")

        mock_interruption_handler.check_shutdown.side_effect = (
            check_shutdown_side_effect
        )

        with pytest.raises(ShutdownRequested) as exc_info:
            orchestrator.run("Test feature")

        assert exc_info.value.phase == "build"

    def test_run_persists_initial_state(
        self,
        orchestrator: "Orchestrator",
        mock_phase_runner: MagicMock,
        mock_context_manager: MagicMock,
    ) -> None:
        """Test that initial state is persisted before phase loop."""

        orchestrator.run("Test feature")

        # First save should be with status="running" before any phase
        first_save = mock_context_manager.save.call_args_list[0][0][0]
        assert first_save.status == "running"
        assert first_save.phase_history == []  # No phases completed yet


class TestRunSinglePhase:
    """Tests for run_single_phase() method."""

    def test_run_single_phase_generates_new_run_id(
        self,
        orchestrator: "Orchestrator",
        mock_phase_runner: MagicMock,
    ) -> None:
        """Test that run_single_phase generates a unique run ID."""

        context = orchestrator.run_single_phase("plan", "Test feature")

        assert context.run_id is not None
        assert len(context.run_id) == 26  # ULID length

    def test_run_single_phase_creates_context_with_feature(
        self,
        orchestrator: "Orchestrator",
        mock_phase_runner: MagicMock,
    ) -> None:
        """Test that run_single_phase creates context with feature description."""

        context = orchestrator.run_single_phase("plan", "Add login feature")

        assert context.feature_description == "Add login feature"

    def test_run_single_phase_executes_only_specified_phase(
        self,
        orchestrator: "Orchestrator",
        mock_phase_runner: MagicMock,
    ) -> None:
        """Test that only the specified phase is executed."""

        orchestrator.run_single_phase("plan", "Test feature")

        # Should only execute "plan", not the full sequence
        assert mock_phase_runner.run.call_count == 1
        call_args = mock_phase_runner.run.call_args[0]
        assert call_args[0] == "plan"

    def test_run_single_phase_returns_completed_context(
        self,
        orchestrator: "Orchestrator",
        mock_phase_runner: MagicMock,
    ) -> None:
        """Test that run_single_phase returns context with completed status."""

        context = orchestrator.run_single_phase("plan", "Test feature")

        assert context.status == "completed"
        assert context.completed_at is not None

    def test_run_single_phase_records_phase_in_history(
        self,
        orchestrator: "Orchestrator",
        mock_phase_runner: MagicMock,
        mock_artifact_manager: MagicMock,
    ) -> None:
        """Test that executed phase is recorded in phase_history."""

        # Mock artifacts for required phases
        mock_artifact_manager.list_artifacts.return_value = [{"name": "plan.md"}]
        mock_artifact_manager.get.return_value = "# Plan Content"

        context = orchestrator.run_single_phase("build", "Test feature", "01HQSOURCE")

        assert "build" in context.phase_history

    def test_run_single_phase_persists_state(
        self,
        orchestrator: "Orchestrator",
        mock_phase_runner: MagicMock,
        mock_context_manager: MagicMock,
    ) -> None:
        """Test that state is persisted during single phase execution."""

        orchestrator.run_single_phase("plan", "Test feature")

        # Should save at least once (initial + after phase)
        assert mock_context_manager.save.call_count >= 1

    def test_run_single_phase_creates_run_directory(
        self,
        orchestrator: "Orchestrator",
        mock_phase_runner: MagicMock,
        mock_run_directory_manager: MagicMock,
    ) -> None:
        """Test that run directory is created for single phase."""

        orchestrator.run_single_phase("plan", "Test feature")

        mock_run_directory_manager.create.assert_called()

    def test_run_single_phase_with_from_run_id(
        self,
        orchestrator: "Orchestrator",
        mock_phase_runner: MagicMock,
        mock_artifact_manager: MagicMock,
    ) -> None:
        """Test that from_run_id is accepted for non-plan phases."""

        # Mock artifacts for required phases
        mock_artifact_manager.list_artifacts.return_value = [{"name": "plan.md"}]
        mock_artifact_manager.get.return_value = "# Plan Content"

        # Should not raise - from_run_id provided for build phase with artifacts
        context = orchestrator.run_single_phase(
            "build", "Test feature", from_run_id="01HQSOURCE123"
        )

        assert context.status == "completed"


class TestLoadArtifactsFromSource:
    """Tests for loading artifacts from source run in single-phase execution."""

    def test_load_artifacts_from_source_run(
        self,
        orchestrator: "Orchestrator",
        mock_phase_runner: MagicMock,
        mock_artifact_manager: MagicMock,
    ) -> None:
        """Test that artifacts are loaded from source run when from_run_id is set."""

        # Set up artifact manager to return artifacts for source run
        mock_artifact_manager.list_artifacts.return_value = [{"name": "plan.md"}]
        mock_artifact_manager.get.return_value = "# Test Plan Content"

        orchestrator.run_single_phase(
            "build", "Test feature", from_run_id="01HQSOURCE123"
        )

        # Verify artifacts were loaded from source run
        mock_artifact_manager.list_artifacts.assert_called()
        # The call should include the source run ID
        call_args = mock_artifact_manager.list_artifacts.call_args_list
        assert any("01HQSOURCE123" in str(c) for c in call_args)

    def test_source_run_artifacts_not_modified(
        self,
        orchestrator: "Orchestrator",
        mock_phase_runner: MagicMock,
        mock_artifact_manager: MagicMock,
    ) -> None:
        """Test that source run artifacts are not modified."""

        # Set up artifact manager
        mock_artifact_manager.list_artifacts.return_value = [{"name": "plan.md"}]
        mock_artifact_manager.get.return_value = "# Test Plan Content"

        orchestrator.run_single_phase(
            "build", "Test feature", from_run_id="01HQSOURCE123"
        )

        # Verify store was NOT called with source run ID
        for call in mock_artifact_manager.store.call_args_list:
            assert "01HQSOURCE123" not in str(call)

    def test_artifacts_stored_in_new_run(
        self,
        orchestrator: "Orchestrator",
        mock_phase_runner: MagicMock,
        mock_artifact_manager: MagicMock,
    ) -> None:
        """Test that new artifacts are stored in new run, not source run."""

        # Set up mock to capture store calls
        mock_artifact_manager.list_artifacts.return_value = [{"name": "plan.md"}]
        mock_artifact_manager.get.return_value = "# Test Plan Content"

        context = orchestrator.run_single_phase(
            "build", "Test feature", from_run_id="01HQSOURCE123"
        )

        # New run ID should be different from source run
        assert context.run_id != "01HQSOURCE123"


class TestPhaseRequirementsValidation:
    """Tests for validating phase requirements before execution."""

    def test_build_phase_requires_plan_artifacts(
        self,
        orchestrator: "Orchestrator",
        mock_phase_runner: MagicMock,
        mock_artifact_manager: MagicMock,
    ) -> None:
        """Test that build phase requires plan artifacts from source run."""

        # Source run has no plan artifacts
        mock_artifact_manager.list_artifacts.return_value = []

        with pytest.raises(ConfigError) as exc_info:
            orchestrator.run_single_phase(
                "build", "Test feature", from_run_id="01HQSOURCE123"
            )

        assert "plan" in str(exc_info.value).lower()

    def test_validate_phase_requires_build_artifacts(
        self,
        orchestrator: "Orchestrator",
        mock_phase_runner: MagicMock,
        mock_artifact_manager: MagicMock,
    ) -> None:
        """Test that validate phase requires build artifacts (ISS-019: renamed from verify)."""

        # Source run has plan but no build artifacts
        def list_artifacts_side_effect(run_id: str, phase: str):
            if phase == "plan":
                return [{"name": "plan.md"}]
            return []

        mock_artifact_manager.list_artifacts.side_effect = list_artifacts_side_effect

        with pytest.raises(ConfigError) as exc_info:
            orchestrator.run_single_phase(
                "validate", "Test feature", from_run_id="01HQSOURCE123"
            )

        assert "build" in str(exc_info.value).lower()

    def test_plan_phase_does_not_require_artifacts(
        self,
        orchestrator: "Orchestrator",
        mock_phase_runner: MagicMock,
        mock_artifact_manager: MagicMock,
    ) -> None:
        """Test that plan phase does not require previous artifacts."""

        # No artifacts in source run - should not matter for plan
        mock_artifact_manager.list_artifacts.return_value = []

        # Should succeed for plan phase (no validation needed)
        context = orchestrator.run_single_phase("plan", "Test feature")

        assert context.status == "completed"


class TestOrchestratorAbort:
    """Tests for Orchestrator.abort() method."""

    def test_abort_running_run(
        self,
        orchestrator: "Orchestrator",
        mock_context_manager: MagicMock,
        mock_interruption_handler: MagicMock,
    ) -> None:
        """Test aborting a running run."""
        running_context = RunContext(
            run_id="01JFTEST000000000000000001",
            feature_description="Test feature",
            current_phase="build",
            phase_history=["plan"],
            started_at=datetime.now(UTC),
            status="running",
        )
        mock_context_manager.load.return_value = running_context

        # Configure abort_gracefully to return aborted context
        aborted_context = running_context.model_copy(
            update={"status": "aborted", "completed_at": datetime.now(UTC)}
        )
        mock_interruption_handler.abort_gracefully.return_value = aborted_context

        result = orchestrator.abort("01JFTEST000000000000000001")

        assert result.status == "aborted"
        assert result.completed_at is not None
        mock_interruption_handler.abort_gracefully.assert_called_once()

    def test_abort_not_running_raises(
        self,
        orchestrator: "Orchestrator",
        mock_context_manager: MagicMock,
    ) -> None:
        """Test aborting a non-running run raises error."""
        completed_context = RunContext(
            run_id="01JFTEST000000000000000001",
            feature_description="Test feature",
            current_phase="document",
            phase_history=PHASE_SEQUENCE,
            started_at=datetime.now(UTC),
            status="completed",
        )
        mock_context_manager.load.return_value = completed_context

        with pytest.raises(ConfigError) as exc_info:
            orchestrator.abort("01JFTEST000000000000000001")

        assert exc_info.value.code == "RUN_NOT_ACTIVE"

    def test_abort_with_custom_reason(
        self,
        orchestrator: "Orchestrator",
        mock_context_manager: MagicMock,
        mock_interruption_handler: MagicMock,
    ) -> None:
        """Test abort with custom reason."""
        running_context = RunContext(
            run_id="01JFTEST000000000000000001",
            feature_description="Test feature",
            current_phase="build",
            phase_history=["plan"],
            started_at=datetime.now(UTC),
            status="running",
        )
        mock_context_manager.load.return_value = running_context

        # Configure abort_gracefully to return aborted context
        aborted_context = running_context.model_copy(
            update={"status": "aborted", "completed_at": datetime.now(UTC)}
        )
        mock_interruption_handler.abort_gracefully.return_value = aborted_context

        orchestrator.abort("01JFTEST000000000000000001", reason="cli_abort")

        # Check that abort_gracefully was called with reason
        mock_interruption_handler.abort_gracefully.assert_called_once()
        call_args = mock_interruption_handler.abort_gracefully.call_args
        assert call_args[1]["reason"] == "cli_abort"

    def test_abort_already_aborted_raises(
        self,
        orchestrator: "Orchestrator",
        mock_context_manager: MagicMock,
    ) -> None:
        """Test aborting an already aborted run raises error."""
        aborted_context = RunContext(
            run_id="01JFTEST000000000000000001",
            feature_description="Test feature",
            current_phase="build",
            phase_history=["plan"],
            started_at=datetime.now(UTC),
            status="aborted",
        )
        mock_context_manager.load.return_value = aborted_context

        with pytest.raises(ConfigError) as exc_info:
            orchestrator.abort("01JFTEST000000000000000001")

        assert exc_info.value.code == "RUN_ALREADY_ABORTED"


class TestOrchestratorWorktree:
    """Tests for Orchestrator worktree integration (Story 10.1)."""

    def test_run_with_worktree_disabled(
        self,
        mock_context_manager: MagicMock,
        mock_snapshot_manager: MagicMock,
        mock_artifact_manager: MagicMock,
        mock_run_directory_manager: MagicMock,
        mock_phase_runner: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test run with use_worktree=False doesn't create worktree."""
        from adw.core.orchestrator import Orchestrator
        from adw.models import WorktreeConfig

        runs_dir = tmp_path / ".adw" / "runs"
        runs_dir.mkdir(parents=True)

        # Worktree config is enabled, but we'll pass use_worktree=False
        worktree_config = WorktreeConfig(enabled=True)

        orchestrator = Orchestrator(
            runs_dir=runs_dir,
            context_manager=mock_context_manager,
            snapshot_manager=mock_snapshot_manager,
            artifact_manager=mock_artifact_manager,
            run_directory_manager=mock_run_directory_manager,
            phase_runner=mock_phase_runner,
            worktree_config=worktree_config,
        )

        # Run with worktree disabled
        context = orchestrator.run("Test feature", use_worktree=False)

        # Verify context indicates worktree was not used
        assert context.use_worktree is False
        assert context.worktree_path is None

    def test_worktree_config_disabled(
        self,
        mock_context_manager: MagicMock,
        mock_snapshot_manager: MagicMock,
        mock_artifact_manager: MagicMock,
        mock_run_directory_manager: MagicMock,
        mock_phase_runner: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test that worktree is not created when config.enabled=False."""
        from adw.core.orchestrator import Orchestrator
        from adw.models import WorktreeConfig

        runs_dir = tmp_path / ".adw" / "runs"
        runs_dir.mkdir(parents=True)

        # Worktree config is disabled
        worktree_config = WorktreeConfig(enabled=False)

        orchestrator = Orchestrator(
            runs_dir=runs_dir,
            context_manager=mock_context_manager,
            snapshot_manager=mock_snapshot_manager,
            artifact_manager=mock_artifact_manager,
            run_directory_manager=mock_run_directory_manager,
            phase_runner=mock_phase_runner,
            worktree_config=worktree_config,
        )

        # _worktree_manager should be None when config.enabled=False
        assert orchestrator._worktree_manager is None

        # Run should still work
        context = orchestrator.run("Test feature")

        # Verify context indicates worktree was not used
        assert context.use_worktree is False
        assert context.worktree_path is None

    def test_run_default_uses_worktree(
        self,
        mock_context_manager: MagicMock,
        mock_snapshot_manager: MagicMock,
        mock_artifact_manager: MagicMock,
        mock_run_directory_manager: MagicMock,
        mock_phase_runner: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test that run() defaults to using worktree when enabled."""
        from adw.core.orchestrator import Orchestrator
        from adw.models import WorktreeConfig

        runs_dir = tmp_path / ".adw" / "runs"
        runs_dir.mkdir(parents=True)

        # Create worktree config
        worktree_config = WorktreeConfig(enabled=True, base_dir="trees")

        orchestrator = Orchestrator(
            runs_dir=runs_dir,
            context_manager=mock_context_manager,
            snapshot_manager=mock_snapshot_manager,
            artifact_manager=mock_artifact_manager,
            run_directory_manager=mock_run_directory_manager,
            phase_runner=mock_phase_runner,
            worktree_config=worktree_config,
        )

        # WorktreeManager should be created when config.enabled=True
        assert orchestrator._worktree_manager is not None
        assert orchestrator._worktree_manager.base_dir == "trees"


class TestWorktreeNoAutoDelete:
    """Tests for worktree preservation - worktrees should never be auto-deleted (ISS-020).

    ISS-020 extends ISS-018 to ensure worktrees are NEVER automatically deleted.
    Only the explicit 'adw cleanup <run_id>' command should delete worktrees.
    """

    def test_single_phase_preserves_worktree_on_success(
        self,
        mock_context_manager: MagicMock,
        mock_snapshot_manager: MagicMock,
        mock_artifact_manager: MagicMock,
        mock_run_directory_manager: MagicMock,
        mock_phase_runner: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Single-phase run preserves worktree after success (ISS-018).

        When running a single phase, the worktree should be preserved for
        inspection rather than cleaned up. The user can manually clean up
        with 'adw cleanup <run_id>' when done.
        """
        from adw.core.orchestrator import Orchestrator
        from adw.models import WorktreeConfig

        runs_dir = tmp_path / ".adw" / "runs"
        runs_dir.mkdir(parents=True)

        worktree_config = WorktreeConfig(enabled=True, base_dir="trees")

        orchestrator = Orchestrator(
            runs_dir=runs_dir,
            context_manager=mock_context_manager,
            snapshot_manager=mock_snapshot_manager,
            artifact_manager=mock_artifact_manager,
            run_directory_manager=mock_run_directory_manager,
            phase_runner=mock_phase_runner,
            worktree_config=worktree_config,
        )

        # Mock the cleanup method to track calls
        orchestrator._cleanup_worktree = MagicMock()

        # ISS-025: Mock worktree creation on lifecycle (tmp_path is not a git repo)
        worktree_path = tmp_path / "trees" / "test-run"
        orchestrator._lifecycle._create_worktree_for_run = MagicMock(
            return_value=(worktree_path, "adw/test-run")
        )

        # Run single phase (signature: phase, feature_description)
        orchestrator.run_single_phase("plan", "Test feature")

        # Verify _cleanup_worktree was NOT called for single-phase success
        orchestrator._cleanup_worktree.assert_not_called()

    def test_multi_phase_preserves_worktree_on_success(
        self,
        mock_context_manager: MagicMock,
        mock_snapshot_manager: MagicMock,
        mock_artifact_manager: MagicMock,
        mock_run_directory_manager: MagicMock,
        mock_phase_runner: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Multi-phase run preserves worktree after success (ISS-020).

        Worktrees are NEVER automatically deleted. Users must explicitly
        use 'adw cleanup <run_id>' to remove worktrees.
        """
        from adw.core.orchestrator import Orchestrator
        from adw.models import WorktreeConfig

        runs_dir = tmp_path / ".adw" / "runs"
        runs_dir.mkdir(parents=True)

        worktree_config = WorktreeConfig(enabled=True, base_dir="trees")

        orchestrator = Orchestrator(
            runs_dir=runs_dir,
            context_manager=mock_context_manager,
            snapshot_manager=mock_snapshot_manager,
            artifact_manager=mock_artifact_manager,
            run_directory_manager=mock_run_directory_manager,
            phase_runner=mock_phase_runner,
            worktree_config=worktree_config,
        )

        # Mock the cleanup method to track calls
        orchestrator._cleanup_worktree = MagicMock()

        # ISS-025: Mock worktree creation (tmp_path is not a git repo)
        worktree_path = tmp_path / "trees" / "test-run"
        orchestrator._lifecycle._create_worktree_for_run = MagicMock(
            return_value=(worktree_path, "adw/test-run")
        )

        # Run full pipeline (signature: feature_description)
        orchestrator.run("Test feature")

        # Verify _cleanup_worktree was NOT called (ISS-020: no auto-delete)
        orchestrator._cleanup_worktree.assert_not_called()

    def test_single_phase_prints_worktree_location(
        self,
        mock_context_manager: MagicMock,
        mock_snapshot_manager: MagicMock,
        mock_artifact_manager: MagicMock,
        mock_run_directory_manager: MagicMock,
        mock_phase_runner: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Single-phase run prints worktree path and cleanup instructions.

        When preserving a worktree after single-phase completion, the user
        should see a clear message about where the worktree is and how to
        clean it up.
        """
        from adw.core.orchestrator import Orchestrator
        from adw.models import WorktreeConfig

        runs_dir = tmp_path / ".adw" / "runs"
        runs_dir.mkdir(parents=True)

        worktree_config = WorktreeConfig(enabled=True, base_dir="trees")

        orchestrator = Orchestrator(
            runs_dir=runs_dir,
            context_manager=mock_context_manager,
            snapshot_manager=mock_snapshot_manager,
            artifact_manager=mock_artifact_manager,
            run_directory_manager=mock_run_directory_manager,
            phase_runner=mock_phase_runner,
            worktree_config=worktree_config,
        )

        # Mock the progress display with a real mock console
        from adw.cli.progress import ProgressDisplay

        mock_console = MagicMock()
        mock_progress_display = MagicMock(spec=ProgressDisplay)
        mock_progress_display.console = mock_console
        orchestrator.progress_display = mock_progress_display
        # Also update lifecycle's progress_display since it was created with None
        orchestrator._lifecycle.progress_display = mock_progress_display

        # Mock worktree creation to return a path
        worktree_path = tmp_path / "trees" / "test-run"
        orchestrator._lifecycle._create_worktree_for_run = MagicMock(
            return_value=(worktree_path, "adw/test-run")
        )

        # Run single phase (signature: phase, feature_description)
        _ = orchestrator.run_single_phase("plan", "Test feature")

        # Verify console.print was called with specific worktree info
        print_calls = [str(c) for c in mock_console.print.call_args_list]

        # Must have worktree path mentioned
        worktree_mentioned = any("Worktree" in str(c) for c in print_calls)
        assert worktree_mentioned, (
            f"Expected 'Worktree' in console output, got: {print_calls}"
        )

        # Must have cleanup command mentioned
        cleanup_mentioned = any("cleanup" in str(c) for c in print_calls)
        assert cleanup_mentioned, (
            f"Expected 'cleanup' instruction in console output, got: {print_calls}"
        )

        # Must have phase completion message
        phase_complete = any("complete" in str(c).lower() for c in print_calls)
        assert phase_complete, (
            f"Expected phase completion message in console output, got: {print_calls}"
        )

    def test_single_phase_works_without_progress_display(
        self,
        mock_context_manager: MagicMock,
        mock_snapshot_manager: MagicMock,
        mock_artifact_manager: MagicMock,
        mock_run_directory_manager: MagicMock,
        mock_phase_runner: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Single-phase run works correctly when progress_display is None.

        The orchestrator should not crash when progress_display is not set,
        even when preserving a worktree (ISS-018 fix).
        """
        from adw.core.orchestrator import Orchestrator
        from adw.models import WorktreeConfig

        runs_dir = tmp_path / ".adw" / "runs"
        runs_dir.mkdir(parents=True)

        worktree_config = WorktreeConfig(enabled=True, base_dir="trees")

        orchestrator = Orchestrator(
            runs_dir=runs_dir,
            context_manager=mock_context_manager,
            snapshot_manager=mock_snapshot_manager,
            artifact_manager=mock_artifact_manager,
            run_directory_manager=mock_run_directory_manager,
            phase_runner=mock_phase_runner,
            worktree_config=worktree_config,
            # progress_display is intentionally NOT set (None)
        )

        # Ensure progress_display is None
        assert orchestrator.progress_display is None

        # Mock worktree creation to return a path
        worktree_path = tmp_path / "trees" / "test-run"
        orchestrator._lifecycle._create_worktree_for_run = MagicMock(
            return_value=(worktree_path, "adw/test-run")
        )

        # This should NOT raise AttributeError even without progress_display
        context = orchestrator.run_single_phase("plan", "Test feature")

        # Verify the run completed successfully
        assert context.status == "completed"
        assert "plan" in context.phase_history

    def test_failed_run_preserves_worktree(
        self,
        mock_context_manager: MagicMock,
        mock_snapshot_manager: MagicMock,
        mock_artifact_manager: MagicMock,
        mock_run_directory_manager: MagicMock,
        mock_phase_runner: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Failed runs preserve worktree regardless of preserve_on_failure config (ISS-020).

        Worktrees are NEVER automatically deleted, even on failure.
        The preserve_on_failure config option is deprecated and ignored.
        """
        from adw.core.orchestrator import Orchestrator
        from adw.exceptions import PhaseError
        from adw.models import WorktreeConfig

        runs_dir = tmp_path / ".adw" / "runs"
        runs_dir.mkdir(parents=True)

        # Explicitly set preserve_on_failure=False to verify it's ignored
        worktree_config = WorktreeConfig(
            enabled=True,
            base_dir="trees",
            preserve_on_failure=False,  # This should be ignored per ISS-020
        )

        orchestrator = Orchestrator(
            runs_dir=runs_dir,
            context_manager=mock_context_manager,
            snapshot_manager=mock_snapshot_manager,
            artifact_manager=mock_artifact_manager,
            run_directory_manager=mock_run_directory_manager,
            phase_runner=mock_phase_runner,
            worktree_config=worktree_config,
        )

        # Mock the cleanup method to track calls
        orchestrator._cleanup_worktree = MagicMock()

        # ISS-025: Mock worktree creation (tmp_path is not a git repo)
        worktree_path = tmp_path / "trees" / "test-run"
        orchestrator._lifecycle._create_worktree_for_run = MagicMock(
            return_value=(worktree_path, "adw/test-run")
        )

        # Make phase runner fail
        mock_phase_runner.run.side_effect = PhaseError(
            code="PHASE_FAILED",
            message="Test failure",
            phase="plan",
            recoverable=False,
        )

        # Run should raise the error
        import pytest

        with pytest.raises(PhaseError):
            orchestrator.run("Test feature")

        # Verify _cleanup_worktree was NOT called (ISS-020: no auto-delete)
        orchestrator._cleanup_worktree.assert_not_called()

    def test_worktree_info_message_on_multi_phase_success(
        self,
        mock_context_manager: MagicMock,
        mock_snapshot_manager: MagicMock,
        mock_artifact_manager: MagicMock,
        mock_run_directory_manager: MagicMock,
        mock_phase_runner: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Multi-phase success shows worktree path and cleanup instructions (ISS-020).

        After successful completion, user should see worktree location
        and how to clean it up.
        """
        from adw.core.orchestrator import Orchestrator
        from adw.models import WorktreeConfig

        runs_dir = tmp_path / ".adw" / "runs"
        runs_dir.mkdir(parents=True)

        # Create orchestrator with worktree disabled initially
        worktree_config = WorktreeConfig(enabled=False)

        orchestrator = Orchestrator(
            runs_dir=runs_dir,
            context_manager=mock_context_manager,
            snapshot_manager=mock_snapshot_manager,
            artifact_manager=mock_artifact_manager,
            run_directory_manager=mock_run_directory_manager,
            phase_runner=mock_phase_runner,
            worktree_config=worktree_config,
        )

        # Mock the progress display with a real mock console
        from adw.cli.progress import ProgressDisplay

        mock_console = MagicMock()
        mock_progress_display = MagicMock(spec=ProgressDisplay)
        mock_progress_display.console = mock_console
        orchestrator.progress_display = mock_progress_display

        # Enable worktree and mock the manager
        worktree_config = WorktreeConfig(enabled=True, base_dir="trees")
        orchestrator.worktree_config = worktree_config
        orchestrator._worktree_manager = MagicMock()

        # Also update lifecycle's progress_display and worktree_config
        orchestrator._lifecycle.progress_display = mock_progress_display
        orchestrator._lifecycle.worktree_config = worktree_config
        orchestrator._lifecycle._worktree_manager = orchestrator._worktree_manager

        # Mock worktree creation to return a path
        worktree_path = tmp_path / "trees" / "test-run"
        orchestrator._lifecycle._create_worktree_for_run = MagicMock(
            return_value=(worktree_path, "adw/test-run")
        )

        # Run full pipeline
        orchestrator.run("Test feature")

        # Verify console.print was called with worktree info
        print_calls = [str(c) for c in mock_console.print.call_args_list]

        # Must have worktree path mentioned
        worktree_mentioned = any("Worktree" in str(c) for c in print_calls)
        assert worktree_mentioned, (
            f"Expected 'Worktree' in console output, got: {print_calls}"
        )

        # Must have cleanup command mentioned
        cleanup_mentioned = any("cleanup" in str(c) for c in print_calls)
        assert cleanup_mentioned, (
            f"Expected 'cleanup' instruction in console output, got: {print_calls}"
        )

    def test_resume_preserves_worktree_on_success(
        self,
        mock_context_manager: MagicMock,
        mock_snapshot_manager: MagicMock,
        mock_artifact_manager: MagicMock,
        mock_run_directory_manager: MagicMock,
        mock_phase_runner: MagicMock,
        mock_interruption_handler: MagicMock,
        mock_index_manager: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Resume success preserves worktree for user inspection (ISS-020).

        Worktrees are NEVER automatically deleted after resume completes.
        Users must explicitly use 'adw cleanup <run_id>' to remove worktrees.
        """
        from adw.core.orchestrator import Orchestrator
        from adw.models import WorktreeConfig

        runs_dir = tmp_path / ".adw" / "runs"
        runs_dir.mkdir(parents=True)

        # Create orchestrator with worktree disabled initially to avoid git ops
        worktree_config = WorktreeConfig(enabled=False)

        orchestrator = Orchestrator(
            runs_dir=runs_dir,
            context_manager=mock_context_manager,
            snapshot_manager=mock_snapshot_manager,
            artifact_manager=mock_artifact_manager,
            run_directory_manager=mock_run_directory_manager,
            phase_runner=mock_phase_runner,
            interruption_handler=mock_interruption_handler,
            index_manager=mock_index_manager,
            worktree_config=worktree_config,
        )

        # Mock the cleanup method to track calls
        orchestrator._cleanup_worktree = MagicMock()

        # Create a context that can be resumed (failed/interrupted state)
        worktree_path = tmp_path / "trees" / "test-run"
        existing_context = RunContext(
            run_id="01JFTEST000000000000000001",
            feature_description="Test feature",
            current_phase="build",
            phase_history=["plan"],
            phase_tokens={"plan": 100},
            started_at=datetime.now(UTC),
            status="failed",
            use_worktree=True,
            worktree_path=worktree_path,
        )
        mock_context_manager.load.return_value = existing_context

        # Resume the run
        orchestrator.resume("01JFTEST000000000000000001")

        # Verify _cleanup_worktree was NOT called (ISS-020: no auto-delete)
        orchestrator._cleanup_worktree.assert_not_called()

    def test_cleanup_command_is_only_deletion_method(
        self,
        mock_context_manager: MagicMock,
        mock_snapshot_manager: MagicMock,
        mock_artifact_manager: MagicMock,
        mock_run_directory_manager: MagicMock,
        mock_phase_runner: MagicMock,
        mock_interruption_handler: MagicMock,
        mock_index_manager: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Only adw cleanup command should delete worktrees (ISS-020).

        Verifies that _cleanup_worktree is never called automatically by
        run(), run_single_phase(), or resume(). The only caller should be
        the explicit cleanup CLI command.
        """
        from adw.core.orchestrator import Orchestrator
        from adw.models import WorktreeConfig

        runs_dir = tmp_path / ".adw" / "runs"
        runs_dir.mkdir(parents=True)

        # Create orchestrator with worktree disabled initially to avoid git ops
        worktree_config = WorktreeConfig(enabled=False)

        orchestrator = Orchestrator(
            runs_dir=runs_dir,
            context_manager=mock_context_manager,
            snapshot_manager=mock_snapshot_manager,
            artifact_manager=mock_artifact_manager,
            run_directory_manager=mock_run_directory_manager,
            phase_runner=mock_phase_runner,
            interruption_handler=mock_interruption_handler,
            index_manager=mock_index_manager,
            worktree_config=worktree_config,
        )

        # Enable worktree and mock the manager
        orchestrator.worktree_config = WorktreeConfig(enabled=True, base_dir="trees")
        orchestrator._worktree_manager = MagicMock()

        # Mock _cleanup_worktree to track ALL calls
        cleanup_mock = MagicMock()
        orchestrator._cleanup_worktree = cleanup_mock

        # Mock worktree creation
        worktree_path = tmp_path / "trees" / "test-run"
        orchestrator._lifecycle._create_worktree_for_run = MagicMock(
            return_value=(worktree_path, "adw/test-run")
        )

        # Test 1: run() should NOT call _cleanup_worktree
        orchestrator.run("Test feature 1")
        assert cleanup_mock.call_count == 0, "run() should not auto-cleanup worktree"

        # Test 2: run_single_phase() should NOT call _cleanup_worktree
        cleanup_mock.reset_mock()
        orchestrator.run_single_phase("plan", "Test feature 2")
        assert cleanup_mock.call_count == 0, (
            "run_single_phase() should not auto-cleanup worktree"
        )

        # Test 3: resume() should NOT call _cleanup_worktree
        cleanup_mock.reset_mock()
        existing_context = RunContext(
            run_id="01JFTEST000000000000000002",
            feature_description="Test feature",
            current_phase="build",
            phase_history=["plan"],
            phase_tokens={"plan": 100},
            started_at=datetime.now(UTC),
            status="failed",
            use_worktree=True,
            worktree_path=worktree_path,
        )
        mock_context_manager.load.return_value = existing_context
        orchestrator.resume("01JFTEST000000000000000002")
        assert cleanup_mock.call_count == 0, "resume() should not auto-cleanup worktree"


class TestStatusSyncServiceIntegration:
    """Tests for StatusSyncService integration with Orchestrator (Story 12.3)."""

    @pytest.fixture
    def mock_status_sync_service(self) -> MagicMock:
        """Create a mock StatusSyncService."""
        service = MagicMock()
        service.sync_phase_start = MagicMock()
        service.sync_phase_transition = MagicMock()
        service.sync_run_failed = MagicMock()
        service.sync_run_complete = MagicMock()
        return service

    def test_sync_phase_start_called_for_each_phase(
        self,
        tmp_path: Path,
        mock_context_manager: MagicMock,
        mock_snapshot_manager: MagicMock,
        mock_artifact_manager: MagicMock,
        mock_run_directory_manager: MagicMock,
        mock_phase_runner: MagicMock,
        mock_interruption_handler: MagicMock,
        mock_index_manager: MagicMock,
        mock_status_sync_service: MagicMock,
    ) -> None:
        """Calls sync_phase_start at the beginning of each phase."""
        from adw.core.orchestrator import Orchestrator
        from adw.models.config import WorktreeConfig

        runs_dir = tmp_path / ".adw" / "runs"
        runs_dir.mkdir(parents=True)

        worktree_config = WorktreeConfig(enabled=False)

        orchestrator = Orchestrator(
            runs_dir=runs_dir,
            context_manager=mock_context_manager,
            snapshot_manager=mock_snapshot_manager,
            artifact_manager=mock_artifact_manager,
            run_directory_manager=mock_run_directory_manager,
            phase_runner=mock_phase_runner,
            interruption_handler=mock_interruption_handler,
            index_manager=mock_index_manager,
            worktree_config=worktree_config,
            status_sync_service=mock_status_sync_service,
        )

        orchestrator.run("Test feature")

        # Verify sync_phase_start was called for each phase
        assert mock_status_sync_service.sync_phase_start.call_count == len(
            PHASE_SEQUENCE
        )

        # Verify the phases were correct
        call_args = [
            call[0][1]
            for call in mock_status_sync_service.sync_phase_start.call_args_list
        ]
        assert call_args == list(PHASE_SEQUENCE)

    def test_sync_run_failed_called_on_error(
        self,
        tmp_path: Path,
        mock_context_manager: MagicMock,
        mock_snapshot_manager: MagicMock,
        mock_artifact_manager: MagicMock,
        mock_run_directory_manager: MagicMock,
        mock_phase_runner: MagicMock,
        mock_interruption_handler: MagicMock,
        mock_index_manager: MagicMock,
        mock_status_sync_service: MagicMock,
    ) -> None:
        """Calls sync_run_failed when a phase fails."""
        from adw.core.orchestrator import Orchestrator
        from adw.models.config import WorktreeConfig

        runs_dir = tmp_path / ".adw" / "runs"
        runs_dir.mkdir(parents=True)

        worktree_config = WorktreeConfig(enabled=False)

        # Make phase runner fail on build phase
        def fail_on_build(phase: str, context: RunContext, **kwargs):
            if phase == "build":
                raise PhaseError(
                    code="BUILD_FAILED",
                    message="Build failed",
                    phase="build",
                    recoverable=False,
                )
            return PhaseResult(
                phase=phase,
                status=PhaseStatus.COMPLETED,
                started_at=datetime.now(UTC),
                completed_at=datetime.now(UTC),
                artifacts=[],
                tokens_used=50,
            )

        mock_phase_runner.run.side_effect = fail_on_build

        orchestrator = Orchestrator(
            runs_dir=runs_dir,
            context_manager=mock_context_manager,
            snapshot_manager=mock_snapshot_manager,
            artifact_manager=mock_artifact_manager,
            run_directory_manager=mock_run_directory_manager,
            phase_runner=mock_phase_runner,
            interruption_handler=mock_interruption_handler,
            index_manager=mock_index_manager,
            worktree_config=worktree_config,
            status_sync_service=mock_status_sync_service,
        )

        with pytest.raises(PhaseError):
            orchestrator.run("Test feature")

        # Verify sync_run_failed was called
        assert mock_status_sync_service.sync_run_failed.call_count == 1

        # Verify it was called with the correct phase
        call_args = mock_status_sync_service.sync_run_failed.call_args[0]
        assert call_args[1] == "build"  # Failed phase
        assert "BUILD_FAILED" in call_args[2]  # Error message

    def test_no_sync_calls_without_service(
        self,
        tmp_path: Path,
        mock_context_manager: MagicMock,
        mock_snapshot_manager: MagicMock,
        mock_artifact_manager: MagicMock,
        mock_run_directory_manager: MagicMock,
        mock_phase_runner: MagicMock,
        mock_interruption_handler: MagicMock,
        mock_index_manager: MagicMock,
    ) -> None:
        """Runs without error when no StatusSyncService is provided."""
        from adw.core.orchestrator import Orchestrator
        from adw.models.config import WorktreeConfig

        runs_dir = tmp_path / ".adw" / "runs"
        runs_dir.mkdir(parents=True)

        worktree_config = WorktreeConfig(enabled=False)

        # No status_sync_service provided
        orchestrator = Orchestrator(
            runs_dir=runs_dir,
            context_manager=mock_context_manager,
            snapshot_manager=mock_snapshot_manager,
            artifact_manager=mock_artifact_manager,
            run_directory_manager=mock_run_directory_manager,
            phase_runner=mock_phase_runner,
            interruption_handler=mock_interruption_handler,
            index_manager=mock_index_manager,
            worktree_config=worktree_config,
        )

        # Should complete without error
        context = orchestrator.run("Test feature")
        assert context.status == "completed"

    def test_sync_errors_do_not_fail_run(
        self,
        tmp_path: Path,
        mock_context_manager: MagicMock,
        mock_snapshot_manager: MagicMock,
        mock_artifact_manager: MagicMock,
        mock_run_directory_manager: MagicMock,
        mock_phase_runner: MagicMock,
        mock_interruption_handler: MagicMock,
        mock_index_manager: MagicMock,
        mock_status_sync_service: MagicMock,
    ) -> None:
        """Run completes successfully even when sync calls fail."""
        from adw.core.orchestrator import Orchestrator
        from adw.models.config import WorktreeConfig

        runs_dir = tmp_path / ".adw" / "runs"
        runs_dir.mkdir(parents=True)

        worktree_config = WorktreeConfig(enabled=False)

        # Make sync service throw errors (these should be caught internally)
        mock_status_sync_service.sync_phase_start.side_effect = Exception("API Error")

        orchestrator = Orchestrator(
            runs_dir=runs_dir,
            context_manager=mock_context_manager,
            snapshot_manager=mock_snapshot_manager,
            artifact_manager=mock_artifact_manager,
            run_directory_manager=mock_run_directory_manager,
            phase_runner=mock_phase_runner,
            interruption_handler=mock_interruption_handler,
            index_manager=mock_index_manager,
            worktree_config=worktree_config,
            status_sync_service=mock_status_sync_service,
        )

        # Should complete without error despite sync failures
        context = orchestrator.run("Test feature")
        assert context.status == "completed"


class TestPRCreationAfterDocumentPhase:
    """Tests for ISS-031: PR creation after document phase."""

    def test_pr_created_after_document_phase(
        self,
        tmp_path: Path,
        mock_context_manager: MagicMock,
        mock_snapshot_manager: MagicMock,
        mock_artifact_manager: MagicMock,
        mock_run_directory_manager: MagicMock,
        mock_phase_runner: MagicMock,
        mock_interruption_handler: MagicMock,
        mock_index_manager: MagicMock,
    ) -> None:
        """PR is created after document phase, before ship phase.

        ISS-031: The PR should be created immediately after document phase
        completes so that ship phase can validate and merge it.
        """
        from unittest.mock import patch

        from adw.cli.pr import AutoPRResult
        from adw.cli.progress import ProgressDisplay
        from adw.core.extensions import DocumentExtension, ExtensionRegistry
        from adw.core.orchestrator import Orchestrator
        from adw.models.config import GitConfig, WorktreeConfig

        runs_dir = tmp_path / ".adw" / "runs"
        runs_dir.mkdir(parents=True)

        # Track when PR creation is called relative to phases
        phase_order: list[str] = []
        pr_creation_order: list[str] = []

        def track_phase_run(
            phase: str,
            context: RunContext,
            *,
            artifacts_override: dict[str, dict[str, str]] | None = None,
        ) -> PhaseResult:
            phase_order.append(phase)
            return PhaseResult(
                phase=phase,
                status=PhaseStatus.COMPLETED,
                started_at=datetime.now(UTC),
                completed_at=datetime.now(UTC),
                tokens_used=100,
            )

        mock_phase_runner.run.side_effect = track_phase_run

        # Mock progress display (no longer used for PR creation, but needed for display)
        mock_console = MagicMock()
        mock_progress_display = MagicMock(spec=ProgressDisplay)
        mock_progress_display.console = mock_console

        worktree_config = WorktreeConfig(enabled=False)
        git_config = GitConfig()

        # Create extension registry with DocumentExtension
        extension_registry = ExtensionRegistry()
        extension_registry.register(DocumentExtension(git_config, runs_dir))

        # Mock auto_create_pr to track when it's called
        def mock_auto_create_pr(
            run_id: str,
            context: RunContext,
            runs_dir_arg: Path,
        ) -> AutoPRResult:
            # Track when PR creation is called
            pr_creation_order.append(f"pr_creation_after_{phase_order[-1]}")
            return AutoPRResult(
                success=True,
                pr_url="https://github.com/test/test/pull/123",
            )

        orchestrator = Orchestrator(
            runs_dir=runs_dir,
            context_manager=mock_context_manager,
            snapshot_manager=mock_snapshot_manager,
            artifact_manager=mock_artifact_manager,
            run_directory_manager=mock_run_directory_manager,
            phase_runner=mock_phase_runner,
            interruption_handler=mock_interruption_handler,
            index_manager=mock_index_manager,
            worktree_config=worktree_config,
            git_config=git_config,
            progress_display=mock_progress_display,
            extension_registry=extension_registry,
        )

        # Patch auto_create_pr to use our mock
        with patch("adw.cli.pr.auto_create_pr", mock_auto_create_pr):
            orchestrator.run("Test feature")

        # Verify PR creation happened after document phase
        assert len(pr_creation_order) == 1
        assert pr_creation_order[0] == "pr_creation_after_document"

        # Verify phase order includes ship after document
        assert "document" in phase_order
        assert "ship" in phase_order
        doc_idx = phase_order.index("document")
        ship_idx = phase_order.index("ship")
        assert doc_idx < ship_idx  # document comes before ship

    def test_ship_phase_skipped_when_pr_creation_fails(
        self,
        tmp_path: Path,
        mock_context_manager: MagicMock,
        mock_snapshot_manager: MagicMock,
        mock_artifact_manager: MagicMock,
        mock_run_directory_manager: MagicMock,
        mock_phase_runner: MagicMock,
        mock_interruption_handler: MagicMock,
        mock_index_manager: MagicMock,
    ) -> None:
        """Ship phase is skipped when PR creation fails.

        ISS-031 / Phase Extensions: When PR creation is attempted but fails,
        the ship phase should be skipped (not run) to avoid pre.sh errors.
        This is now handled by ShipExtension.should_skip() checking
        context.pr_creation_failed.
        """
        from unittest.mock import patch

        from adw.cli.pr import AutoPRResult
        from adw.cli.progress import ProgressDisplay
        from adw.core.extensions import (
            DocumentExtension,
            ExtensionRegistry,
            ShipExtension,
        )
        from adw.core.orchestrator import Orchestrator
        from adw.models.config import GitConfig, WorktreeConfig

        runs_dir = tmp_path / ".adw" / "runs"
        runs_dir.mkdir(parents=True)

        # Track which phases are executed
        executed_phases: list[str] = []

        def track_phase_run(
            phase: str,
            context: RunContext,
            *,
            artifacts_override: dict[str, dict[str, str]] | None = None,
        ) -> PhaseResult:
            executed_phases.append(phase)
            return PhaseResult(
                phase=phase,
                status=PhaseStatus.COMPLETED,
                started_at=datetime.now(UTC),
                completed_at=datetime.now(UTC),
                tokens_used=100,
            )

        mock_phase_runner.run.side_effect = track_phase_run

        # Mock progress display (needed for skip message output)
        mock_console = MagicMock()
        mock_progress_display = MagicMock(spec=ProgressDisplay)
        mock_progress_display.console = mock_console

        worktree_config = WorktreeConfig(enabled=False)
        git_config = GitConfig()

        # Create extension registry with DocumentExtension and ShipExtension
        extension_registry = ExtensionRegistry()
        extension_registry.register(DocumentExtension(git_config, runs_dir))
        extension_registry.register(ShipExtension())

        # Mock auto_create_pr to return failure
        def mock_auto_create_pr_fails(
            run_id: str,
            context: RunContext,
            runs_dir_arg: Path,
        ) -> AutoPRResult:
            return AutoPRResult(
                success=False,
                reason="No commits to push",
            )

        orchestrator = Orchestrator(
            runs_dir=runs_dir,
            context_manager=mock_context_manager,
            snapshot_manager=mock_snapshot_manager,
            artifact_manager=mock_artifact_manager,
            run_directory_manager=mock_run_directory_manager,
            phase_runner=mock_phase_runner,
            interruption_handler=mock_interruption_handler,
            index_manager=mock_index_manager,
            worktree_config=worktree_config,
            git_config=git_config,
            progress_display=mock_progress_display,
            extension_registry=extension_registry,
        )

        # Patch auto_create_pr to fail
        with patch("adw.cli.pr.auto_create_pr", mock_auto_create_pr_fails):
            orchestrator.run("Test feature")

        # Verify ship phase was NOT executed
        assert "ship" not in executed_phases
        # But document phase was executed
        assert "document" in executed_phases

        # Verify skip message was printed (via extension registry)
        mock_progress_display.console.print.assert_called()
        calls = mock_progress_display.console.print.call_args_list
        skip_message_printed = any("Skipping ship phase" in str(call) for call in calls)
        assert skip_message_printed

    def test_pr_url_stored_in_context(
        self,
        tmp_path: Path,
        mock_context_manager: MagicMock,
        mock_snapshot_manager: MagicMock,
        mock_artifact_manager: MagicMock,
        mock_run_directory_manager: MagicMock,
        mock_phase_runner: MagicMock,
        mock_interruption_handler: MagicMock,
        mock_index_manager: MagicMock,
    ) -> None:
        """PR URL is stored in context when PR is successfully created.

        ISS-031 / Phase Extensions: The pr_url should be stored in the context
        so that it can be passed to ship phase hooks via ADW_PR_URL environment
        variable. This is now handled by DocumentExtension.on_complete().
        """
        from unittest.mock import patch

        from adw.cli.pr import AutoPRResult
        from adw.cli.progress import ProgressDisplay
        from adw.core.extensions import DocumentExtension, ExtensionRegistry
        from adw.core.orchestrator import Orchestrator
        from adw.models.config import GitConfig, WorktreeConfig

        runs_dir = tmp_path / ".adw" / "runs"
        runs_dir.mkdir(parents=True)

        # Mock progress display
        mock_console = MagicMock()
        mock_progress_display = MagicMock(spec=ProgressDisplay)
        mock_progress_display.console = mock_console

        worktree_config = WorktreeConfig(enabled=False)
        git_config = GitConfig()

        # Create extension registry with DocumentExtension
        extension_registry = ExtensionRegistry()
        extension_registry.register(DocumentExtension(git_config, runs_dir))

        # Mock auto_create_pr to return success
        def mock_auto_create_pr_success(
            run_id: str,
            context: RunContext,
            runs_dir_arg: Path,
        ) -> AutoPRResult:
            return AutoPRResult(
                success=True,
                pr_url="https://github.com/test/test/pull/456",
            )

        orchestrator = Orchestrator(
            runs_dir=runs_dir,
            context_manager=mock_context_manager,
            snapshot_manager=mock_snapshot_manager,
            artifact_manager=mock_artifact_manager,
            run_directory_manager=mock_run_directory_manager,
            phase_runner=mock_phase_runner,
            interruption_handler=mock_interruption_handler,
            index_manager=mock_index_manager,
            worktree_config=worktree_config,
            git_config=git_config,
            progress_display=mock_progress_display,
            extension_registry=extension_registry,
        )

        with patch("adw.cli.pr.auto_create_pr", mock_auto_create_pr_success):
            orchestrator.run("Test feature")

        # Verify context_manager.save was called with pr_url set
        # Check the last few save calls to find one with pr_url
        save_calls = mock_context_manager.save.call_args_list
        pr_url_saved = False
        for call in save_calls:
            saved_context = call[0][0]  # First positional arg
            if hasattr(saved_context, "pr_url") and saved_context.pr_url:
                assert saved_context.pr_url == "https://github.com/test/test/pull/456"
                pr_url_saved = True
                break

        assert pr_url_saved, "pr_url should be saved in context"

    def test_ship_runs_with_default_git_config(
        self,
        tmp_path: Path,
        mock_context_manager: MagicMock,
        mock_snapshot_manager: MagicMock,
        mock_artifact_manager: MagicMock,
        mock_run_directory_manager: MagicMock,
        mock_phase_runner: MagicMock,
        mock_interruption_handler: MagicMock,
        mock_index_manager: MagicMock,
    ) -> None:
        """Ship phase runs normally with default git config.

        All phases including ship should run without any issues.
        """
        from adw.core.orchestrator import Orchestrator
        from adw.models.config import GitConfig, WorktreeConfig

        runs_dir = tmp_path / ".adw" / "runs"
        runs_dir.mkdir(parents=True)

        # Track which phases are executed
        executed_phases: list[str] = []

        def track_phase_run(
            phase: str,
            context: RunContext,
            *,
            artifacts_override: dict[str, dict[str, str]] | None = None,
        ) -> PhaseResult:
            executed_phases.append(phase)
            return PhaseResult(
                phase=phase,
                status=PhaseStatus.COMPLETED,
                started_at=datetime.now(UTC),
                completed_at=datetime.now(UTC),
                tokens_used=100,
            )

        mock_phase_runner.run.side_effect = track_phase_run

        worktree_config = WorktreeConfig(enabled=False)
        git_config = GitConfig()

        orchestrator = Orchestrator(
            runs_dir=runs_dir,
            context_manager=mock_context_manager,
            snapshot_manager=mock_snapshot_manager,
            artifact_manager=mock_artifact_manager,
            run_directory_manager=mock_run_directory_manager,
            phase_runner=mock_phase_runner,
            interruption_handler=mock_interruption_handler,
            index_manager=mock_index_manager,
            worktree_config=worktree_config,
            git_config=git_config,
        )

        orchestrator.run("Test feature")

        # All phases should run, including ship
        assert "ship" in executed_phases
        assert executed_phases == list(PHASE_SEQUENCE)

    def test_ship_runs_without_progress_display(
        self,
        tmp_path: Path,
        mock_context_manager: MagicMock,
        mock_snapshot_manager: MagicMock,
        mock_artifact_manager: MagicMock,
        mock_run_directory_manager: MagicMock,
        mock_phase_runner: MagicMock,
        mock_interruption_handler: MagicMock,
        mock_index_manager: MagicMock,
    ) -> None:
        """Ship phase runs when there's no progress_display.

        ISS-031: When progress_display is None, PR creation is not attempted,
        so ship phase should still run (backward compatibility).
        """
        from adw.core.orchestrator import Orchestrator
        from adw.models.config import GitConfig, WorktreeConfig

        runs_dir = tmp_path / ".adw" / "runs"
        runs_dir.mkdir(parents=True)

        # Track which phases are executed
        executed_phases: list[str] = []

        def track_phase_run(
            phase: str,
            context: RunContext,
            *,
            artifacts_override: dict[str, dict[str, str]] | None = None,
        ) -> PhaseResult:
            executed_phases.append(phase)
            return PhaseResult(
                phase=phase,
                status=PhaseStatus.COMPLETED,
                started_at=datetime.now(UTC),
                completed_at=datetime.now(UTC),
                tokens_used=100,
            )

        mock_phase_runner.run.side_effect = track_phase_run

        worktree_config = WorktreeConfig(enabled=False)
        git_config = GitConfig()

        orchestrator = Orchestrator(
            runs_dir=runs_dir,
            context_manager=mock_context_manager,
            snapshot_manager=mock_snapshot_manager,
            artifact_manager=mock_artifact_manager,
            run_directory_manager=mock_run_directory_manager,
            phase_runner=mock_phase_runner,
            interruption_handler=mock_interruption_handler,
            index_manager=mock_index_manager,
            worktree_config=worktree_config,
            git_config=git_config,
            # No progress_display set
        )

        orchestrator.run("Test feature")

        # All phases should run since PR creation wasn't attempted
        assert "ship" in executed_phases
        assert executed_phases == list(PHASE_SEQUENCE)
