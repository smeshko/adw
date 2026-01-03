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
def orchestrator(
    tmp_path: Path,
    mock_context_manager: MagicMock,
    mock_snapshot_manager: MagicMock,
    mock_artifact_manager: MagicMock,
    mock_run_directory_manager: MagicMock,
    mock_interruption_handler: MagicMock,
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
        interruption_handler=mock_interruption_handler,
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
            interruption_handler=mock_interruption_handler,
        )

        assert orch.runs_dir == runs_dir
        assert orch.context_manager is mock_context_manager
        assert orch.snapshot_manager is mock_snapshot_manager
        assert orch.artifact_manager is mock_artifact_manager
        assert orch.run_directory_manager is mock_run_directory_manager
        assert orch.interruption_handler is mock_interruption_handler

    def test_init_creates_default_interruption_handler(
        self,
        tmp_path: Path,
        mock_context_manager: MagicMock,
        mock_snapshot_manager: MagicMock,
        mock_artifact_manager: MagicMock,
        mock_run_directory_manager: MagicMock,
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
        )

        assert isinstance(orch.interruption_handler, InterruptionHandler)

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

    def test_get_next_phase_document_returns_none(
        self, orchestrator: "Orchestrator"
    ) -> None:
        """Test that document is the last phase."""
        assert orchestrator.get_next_phase("document") is None

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
        orchestrator.set_phase_runner(mock_phase_runner)

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
        orchestrator.set_phase_runner(mock_phase_runner)

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
        orchestrator.set_phase_runner(mock_phase_runner)

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
        orchestrator.set_phase_runner(mock_phase_runner)

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
        orchestrator.set_phase_runner(mock_phase_runner)

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
        orchestrator.set_phase_runner(mock_phase_runner)

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
        orchestrator.set_phase_runner(mock_phase_runner)

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
        orchestrator.set_phase_runner(mock_phase_runner)

        context = orchestrator.run("Test feature")

        # Should succeed after retries
        # (2 failures + success on plan = 3, then 4 more phases)
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
        orchestrator.set_phase_runner(mock_phase_runner)

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

        runs_dir = tmp_path / "runs"
        runs_dir.mkdir(parents=True, exist_ok=True)

        orchestrator = Orchestrator(
            runs_dir=runs_dir,
            context_manager=mock_context_manager,
            snapshot_manager=mock_snapshot_manager,
            artifact_manager=mock_artifact_manager,
            run_directory_manager=mock_run_directory_manager,
            max_retries=5,  # Custom max
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
        orchestrator.set_phase_runner(mock_phase_runner)

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
        orchestrator.set_phase_runner(mock_phase_runner)

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
        orchestrator.set_phase_runner(mock_phase_runner)

        context = orchestrator.run("Test feature")

        assert context.status == "completed"
        # 1 failure + 5 successes = 6 calls
        assert call_count == 6


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
        orchestrator.set_phase_runner(mock_phase_runner)

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
        """Test that transition duration is logged."""
        orchestrator.set_phase_runner(mock_phase_runner)

        with patch("adw.core.orchestrator.logger") as mock_logger:
            orchestrator.run("Test feature")

            # Should have logged phase completed with duration
            completed_calls = [
                call
                for call in mock_logger.info.call_args_list
                if "Phase completed" in str(call)
            ]
            assert len(completed_calls) == 5  # One per phase

    def test_slow_transition_logs_warning(
        self,
        orchestrator: "Orchestrator",
    ) -> None:
        """Test that slow transitions log a warning."""
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
        orchestrator.set_phase_runner(slow_runner)

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

            # Should have logged a warning about slow transition
            warning_calls = mock_logger.warning.call_args_list
            assert len(warning_calls) >= 1
            warning_str = str(warning_calls[0]).lower()
            assert "exceeded 1s" in warning_str or "1s" in warning_str


class TestInterruptionHandling:
    """Tests for interruption handling and graceful shutdown."""

    def test_run_checks_shutdown_between_phases(
        self,
        orchestrator: "Orchestrator",
        mock_phase_runner: MagicMock,
        mock_interruption_handler: MagicMock,
    ) -> None:
        """Test that shutdown is checked between phases."""
        orchestrator.set_phase_runner(mock_phase_runner)

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
        orchestrator.set_phase_runner(mock_phase_runner)

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
        orchestrator.set_phase_runner(mock_phase_runner)

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
        orchestrator.set_phase_runner(mock_phase_runner)

        context = orchestrator.run_single_phase("plan", "Test feature")

        assert context.run_id is not None
        assert len(context.run_id) == 26  # ULID length

    def test_run_single_phase_creates_context_with_feature(
        self,
        orchestrator: "Orchestrator",
        mock_phase_runner: MagicMock,
    ) -> None:
        """Test that run_single_phase creates context with feature description."""
        orchestrator.set_phase_runner(mock_phase_runner)

        context = orchestrator.run_single_phase("plan", "Add login feature")

        assert context.feature_description == "Add login feature"

    def test_run_single_phase_executes_only_specified_phase(
        self,
        orchestrator: "Orchestrator",
        mock_phase_runner: MagicMock,
    ) -> None:
        """Test that only the specified phase is executed."""
        orchestrator.set_phase_runner(mock_phase_runner)

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
        orchestrator.set_phase_runner(mock_phase_runner)

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
        orchestrator.set_phase_runner(mock_phase_runner)

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
        orchestrator.set_phase_runner(mock_phase_runner)

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
        orchestrator.set_phase_runner(mock_phase_runner)

        orchestrator.run_single_phase("plan", "Test feature")

        mock_run_directory_manager.create.assert_called()

    def test_run_single_phase_with_from_run_id(
        self,
        orchestrator: "Orchestrator",
        mock_phase_runner: MagicMock,
        mock_artifact_manager: MagicMock,
    ) -> None:
        """Test that from_run_id is accepted for non-plan phases."""
        orchestrator.set_phase_runner(mock_phase_runner)

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
        orchestrator.set_phase_runner(mock_phase_runner)

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
        orchestrator.set_phase_runner(mock_phase_runner)

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
        orchestrator.set_phase_runner(mock_phase_runner)

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
        orchestrator.set_phase_runner(mock_phase_runner)

        # Source run has no plan artifacts
        mock_artifact_manager.list_artifacts.return_value = []

        with pytest.raises(ConfigError) as exc_info:
            orchestrator.run_single_phase(
                "build", "Test feature", from_run_id="01HQSOURCE123"
            )

        assert "plan" in str(exc_info.value).lower()

    def test_verify_phase_requires_build_artifacts(
        self,
        orchestrator: "Orchestrator",
        mock_phase_runner: MagicMock,
        mock_artifact_manager: MagicMock,
    ) -> None:
        """Test that verify phase requires build artifacts."""
        orchestrator.set_phase_runner(mock_phase_runner)

        # Source run has plan but no build artifacts
        def list_artifacts_side_effect(run_id: str, phase: str):
            if phase == "plan":
                return [{"name": "plan.md"}]
            return []

        mock_artifact_manager.list_artifacts.side_effect = list_artifacts_side_effect

        with pytest.raises(ConfigError) as exc_info:
            orchestrator.run_single_phase(
                "verify", "Test feature", from_run_id="01HQSOURCE123"
            )

        assert "build" in str(exc_info.value).lower()

    def test_plan_phase_does_not_require_artifacts(
        self,
        orchestrator: "Orchestrator",
        mock_phase_runner: MagicMock,
        mock_artifact_manager: MagicMock,
    ) -> None:
        """Test that plan phase does not require previous artifacts."""
        orchestrator.set_phase_runner(mock_phase_runner)

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
