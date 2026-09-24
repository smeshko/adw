# REDUCTION: Removed 3 tests that mocked core components (test_phase_runner_calls_llm_progress_methods,
# test_phase_runner_completes_llm_progress_on_error) or were trivial display tests (test_full_pipeline_progress_output).
# Kept 5 tests verifying Orchestrator-ProgressDisplay integration without mocking the integration points.
"""Integration tests for ProgressDisplay with Orchestrator.

Tests that ProgressDisplay correctly integrates with the Orchestrator
to display real-time progress during pipeline execution.
"""

import subprocess
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


@pytest.fixture
def runs_dir(git_repo: Path) -> Path:
    """Return the runs dir of a committed git project.

    The orchestrator derives its project root as ``runs_dir.parent.parent``
    and switches that checkout to the run's branch, so the root must be an
    isolated repo with HOME (``home/``) and the run directories gitignored.
    """
    (git_repo / ".gitignore").write_text("home/\n.adw/runs/\n")
    subprocess.run(["git", "add", "."], cwd=git_repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Ignore ADW runtime state"],
        cwd=git_repo,
        check=True,
        capture_output=True,
    )
    return git_repo / ".adw" / "runs"


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
        prompt_prefix: str | None = None,
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

    def is_phase_enabled(self, phase: str) -> bool:
        """Return True for all phases."""
        return True


class TestOrchestratorProgressIntegration:
    """Integration tests for Orchestrator with ProgressDisplay."""

    def test_orchestrator_calls_progress_display_on_phase_start(
        self, runs_dir: Path
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

        # Disable worktree for tests (the repo has no remote to fetch)
        orchestrator = Orchestrator(
            runs_dir=runs_dir,
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

        # Verify all phases were displayed
        output_text = output.getvalue()
        assert "PLAN" in output_text
        assert "BUILD" in output_text
        assert "VALIDATE" in output_text
        assert "DOCUMENT" in output_text

    def test_orchestrator_calls_progress_display_on_phase_complete(
        self, runs_dir: Path
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
            runs_dir=runs_dir,
            context_manager=context_manager,
            snapshot_manager=snapshot_manager,
            artifact_manager=artifact_manager,
            run_directory_manager=run_directory_manager,
            phase_runner=mock_runner,
            progress_display=progress,
            worktree_config=WorktreeConfig(enabled=False),  # no remote to fetch
        )

        orchestrator.run("Test feature")

        # Verify completion checkmarks are shown
        output_text = output.getvalue()
        # Should have 5 checkmarks for 5 completed phases
        assert output_text.count("✓") >= 5

    def test_orchestrator_calls_progress_display_on_error(self, runs_dir: Path) -> None:
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
                prompt_prefix: str | None = None,
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

            def is_phase_enabled(self, phase: str) -> bool:
                """Return True for all phases."""
                return True

        orchestrator = Orchestrator(
            runs_dir=runs_dir,
            context_manager=context_manager,
            snapshot_manager=snapshot_manager,
            artifact_manager=artifact_manager,
            run_directory_manager=run_directory_manager,
            phase_runner=FailingPhaseRunner(),
            progress_display=progress,
            worktree_config=WorktreeConfig(enabled=False),  # no remote to fetch
        )

        with pytest.raises(LLMError):
            orchestrator.run("Test feature")

        # Verify error is displayed
        output_text = output.getvalue()
        assert "BUILD" in output_text
        assert "Test error" in output_text

    def test_orchestrator_calls_pipeline_summary_on_completion(
        self, runs_dir: Path
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
            runs_dir=runs_dir,
            context_manager=context_manager,
            snapshot_manager=snapshot_manager,
            artifact_manager=artifact_manager,
            run_directory_manager=run_directory_manager,
            phase_runner=mock_runner,
            progress_display=progress,
            worktree_config=WorktreeConfig(enabled=False),  # no remote to fetch
        )

        orchestrator.run("Test feature")

        # Verify pipeline summary is shown
        output_text = output.getvalue()
        assert "Pipeline Summary" in output_text
        assert "completed" in output_text

    def test_orchestrator_calls_pipeline_summary_on_failure(
        self, runs_dir: Path
    ) -> None:
        """Test that Orchestrator calls show_pipeline_summary after failed run."""
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=80)
        progress = ProgressDisplay(console)

        context_manager = Mock(spec=ContextManager)
        snapshot_manager = Mock(spec=SnapshotManager)
        artifact_manager = Mock(spec=ArtifactManager)
        run_directory_manager = Mock(spec=RunDirectoryManager)

        # Create runner that fails on validate phase
        class FailingPhaseRunner:
            def run(
                self,
                phase: str,
                context: RunContext,
                *,
                artifacts_override: dict[str, dict[str, str]] | None = None,
                prompt_prefix: str | None = None,
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

            def is_phase_enabled(self, phase: str) -> bool:
                """Return True for all phases."""
                return True

        orchestrator = Orchestrator(
            runs_dir=runs_dir,
            context_manager=context_manager,
            snapshot_manager=snapshot_manager,
            artifact_manager=artifact_manager,
            run_directory_manager=run_directory_manager,
            phase_runner=FailingPhaseRunner(),
            progress_display=progress,
            worktree_config=WorktreeConfig(enabled=False),  # no remote to fetch
        )

        with pytest.raises(LLMError):
            orchestrator.run("Test feature")

        # Verify pipeline summary is shown with failed status
        output_text = output.getvalue()
        assert "Pipeline Summary" in output_text
        assert "failed" in output_text
