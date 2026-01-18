# REDUCTION: Removed 3 tests that mocked core components (test_phase_runner_calls_llm_progress_methods,
# test_phase_runner_completes_llm_progress_on_error) or were trivial display tests (test_full_pipeline_progress_output).
# Kept 5 tests verifying Orchestrator-ProgressDisplay integration without mocking the integration points.
"""Integration tests for ProgressDisplay with Orchestrator.

Tests that ProgressDisplay correctly integrates with the Orchestrator
to display real-time progress during pipeline execution.
"""

from datetime import UTC, datetime
from io import StringIO
from pathlib import Path
from unittest.mock import Mock

import pytest
from rich.console import Console

from adw.cli.progress import ProgressDisplay
from adw.core.artifact_manager import ArtifactManager
from adw.core.context_manager import ContextManager
from adw.core.orchestrator import Orchestrator
from adw.core.run_directory import RunDirectoryManager
from adw.core.snapshot_manager import SnapshotManager
from adw.exceptions import LLMError
from adw.models import PhaseResult, PhaseStatus, RunContext, WorktreeConfig


class MockPhaseRunner:
    """Mock PhaseRunner that returns configured results."""

    def __init__(self, results: dict[str, PhaseResult]) -> None:
        """Initialize with phase -> result mapping."""
        self.results = results
        self.phases_run: list[str] = []

    def run(
        self,
        phase: str,
        context: RunContext,
        *,
        artifacts_override: dict[str, dict[str, str]] | None = None,
    ) -> PhaseResult:
        """Return configured result for phase."""
        self.phases_run.append(phase)
        if phase in self.results:
            return self.results[phase]
        # Return default result
        return PhaseResult(
            phase=phase,
            status=PhaseStatus.COMPLETED,
            started_at=datetime.now(UTC),
            completed_at=datetime.now(UTC),
            artifacts=[f"{phase}_output.md"],
            tokens_used=100,
        )


class TestOrchestratorProgressIntegration:
    """Integration tests for Orchestrator with ProgressDisplay."""

    def test_orchestrator_calls_progress_display_on_phase_start(
        self, tmp_path: Path
    ) -> None:
        """Test that Orchestrator calls on_phase_start for each phase."""
        # Setup
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=80)
        progress = ProgressDisplay(console)

        # Create mock managers
        context_manager = Mock(spec=ContextManager)
        snapshot_manager = Mock(spec=SnapshotManager)
        artifact_manager = Mock(spec=ArtifactManager)
        run_directory_manager = Mock(spec=RunDirectoryManager)

        # Create mock phase runner that completes all phases
        mock_runner = MockPhaseRunner({})

        # ISS-025: Disable worktree for tests (tmp_path is not a git repo)
        orchestrator = Orchestrator(
            runs_dir=tmp_path,
            context_manager=context_manager,
            snapshot_manager=snapshot_manager,
            artifact_manager=artifact_manager,
            run_directory_manager=run_directory_manager,
            phase_runner=mock_runner,
            progress_display=progress,
            worktree_config=WorktreeConfig(enabled=False),
        )

        # Run
        orchestrator.run("Test feature")

        # Verify all phases were displayed (ISS-019: verify phase removed)
        output_text = output.getvalue()
        assert "PLAN" in output_text
        assert "BUILD" in output_text
        assert "VALIDATE" in output_text
        assert "DOCUMENT" in output_text

    def test_orchestrator_calls_progress_display_on_phase_complete(
        self, tmp_path: Path
    ) -> None:
        """Test that Orchestrator calls on_phase_complete for each phase."""
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=80)
        progress = ProgressDisplay(console)

        context_manager = Mock(spec=ContextManager)
        snapshot_manager = Mock(spec=SnapshotManager)
        artifact_manager = Mock(spec=ArtifactManager)
        run_directory_manager = Mock(spec=RunDirectoryManager)

        mock_runner = MockPhaseRunner({})

        orchestrator = Orchestrator(
            runs_dir=tmp_path,
            context_manager=context_manager,
            snapshot_manager=snapshot_manager,
            artifact_manager=artifact_manager,
            run_directory_manager=run_directory_manager,
            phase_runner=mock_runner,
            progress_display=progress,
            worktree_config=WorktreeConfig(enabled=False),  # ISS-025
        )

        orchestrator.run("Test feature")

        # Verify completion checkmarks are shown
        output_text = output.getvalue()
        # Should have 5 checkmarks for 5 completed phases
        assert output_text.count("✓") >= 5

    def test_orchestrator_calls_progress_display_on_error(self, tmp_path: Path) -> None:
        """Test that Orchestrator calls on_phase_error when phase fails."""
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=80)
        progress = ProgressDisplay(console)

        context_manager = Mock(spec=ContextManager)
        snapshot_manager = Mock(spec=SnapshotManager)
        artifact_manager = Mock(spec=ArtifactManager)
        run_directory_manager = Mock(spec=RunDirectoryManager)

        # Create runner that fails on build phase
        class FailingPhaseRunner:
            def run(
                self,
                phase: str,
                context: RunContext,
                *,
                artifacts_override: dict[str, dict[str, str]] | None = None,
            ) -> PhaseResult:
                if phase == "build":
                    raise LLMError(
                        code="LLM_ERROR",
                        message="Test error",
                        suggestion="Try again",
                        recoverable=False,
                    )
                return PhaseResult(
                    phase=phase,
                    status=PhaseStatus.COMPLETED,
                    started_at=datetime.now(UTC),
                    completed_at=datetime.now(UTC),
                    artifacts=[],
                    tokens_used=0,
                )

        orchestrator = Orchestrator(
            runs_dir=tmp_path,
            context_manager=context_manager,
            snapshot_manager=snapshot_manager,
            artifact_manager=artifact_manager,
            run_directory_manager=run_directory_manager,
            phase_runner=FailingPhaseRunner(),
            progress_display=progress,
            worktree_config=WorktreeConfig(enabled=False),  # ISS-025
        )

        with pytest.raises(LLMError):
            orchestrator.run("Test feature")

        # Verify error is displayed
        output_text = output.getvalue()
        assert "BUILD" in output_text
        assert "Test error" in output_text

    def test_orchestrator_calls_pipeline_summary_on_completion(
        self, tmp_path: Path
    ) -> None:
        """Test that Orchestrator calls show_pipeline_summary after successful run."""
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=80)
        progress = ProgressDisplay(console)

        context_manager = Mock(spec=ContextManager)
        snapshot_manager = Mock(spec=SnapshotManager)
        artifact_manager = Mock(spec=ArtifactManager)
        run_directory_manager = Mock(spec=RunDirectoryManager)

        mock_runner = MockPhaseRunner({})

        orchestrator = Orchestrator(
            runs_dir=tmp_path,
            context_manager=context_manager,
            snapshot_manager=snapshot_manager,
            artifact_manager=artifact_manager,
            run_directory_manager=run_directory_manager,
            phase_runner=mock_runner,
            progress_display=progress,
            worktree_config=WorktreeConfig(enabled=False),  # ISS-025
        )

        orchestrator.run("Test feature")

        # Verify pipeline summary is shown
        output_text = output.getvalue()
        assert "Pipeline Summary" in output_text
        assert "completed" in output_text

    def test_orchestrator_calls_pipeline_summary_on_failure(
        self, tmp_path: Path
    ) -> None:
        """Test that Orchestrator calls show_pipeline_summary after failed run."""
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=80)
        progress = ProgressDisplay(console)

        context_manager = Mock(spec=ContextManager)
        snapshot_manager = Mock(spec=SnapshotManager)
        artifact_manager = Mock(spec=ArtifactManager)
        run_directory_manager = Mock(spec=RunDirectoryManager)

        # Create runner that fails on validate phase (ISS-019: was verify)
        class FailingPhaseRunner:
            def run(
                self,
                phase: str,
                context: RunContext,
                *,
                artifacts_override: dict[str, dict[str, str]] | None = None,
            ) -> PhaseResult:
                if phase == "validate":
                    raise LLMError(
                        code="LLM_ERROR",
                        message="Validation failed",
                        suggestion="Check tests",
                        recoverable=False,
                    )
                return PhaseResult(
                    phase=phase,
                    status=PhaseStatus.COMPLETED,
                    started_at=datetime.now(UTC),
                    completed_at=datetime.now(UTC),
                    artifacts=[],
                    tokens_used=100,
                )

        orchestrator = Orchestrator(
            runs_dir=tmp_path,
            context_manager=context_manager,
            snapshot_manager=snapshot_manager,
            artifact_manager=artifact_manager,
            run_directory_manager=run_directory_manager,
            phase_runner=FailingPhaseRunner(),
            progress_display=progress,
            worktree_config=WorktreeConfig(enabled=False),  # ISS-025
        )

        with pytest.raises(LLMError):
            orchestrator.run("Test feature")

        # Verify pipeline summary is shown with failed status
        output_text = output.getvalue()
        assert "Pipeline Summary" in output_text
        assert "failed" in output_text
