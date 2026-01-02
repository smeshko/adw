"""Integration tests for ProgressDisplay with Orchestrator and PhaseRunner.

Tests that ProgressDisplay correctly integrates with the pipeline
components to display real-time progress during execution.
"""

from datetime import UTC, datetime
from io import StringIO
from pathlib import Path
from unittest.mock import Mock

import pytest
from rich.console import Console
from ulid import ULID

from adw.cli.progress import ProgressDisplay
from adw.core.artifact_manager import ArtifactManager
from adw.core.context_manager import ContextManager
from adw.core.orchestrator import Orchestrator
from adw.core.phase_runner import PhaseRunner
from adw.core.run_directory import RunDirectoryManager
from adw.core.snapshot_manager import SnapshotManager
from adw.exceptions import LLMError
from adw.models import LLMResult, PhaseResult, PhaseStatus, ResolvedCommand, RunContext


class MockPhaseRunner:
    """Mock PhaseRunner that returns configured results."""

    def __init__(self, results: dict[str, PhaseResult]) -> None:
        """Initialize with phase -> result mapping."""
        self.results = results
        self.phases_run: list[str] = []

    def run(self, phase: str, context: RunContext) -> PhaseResult:
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

        orchestrator = Orchestrator(
            runs_dir=tmp_path,
            context_manager=context_manager,
            snapshot_manager=snapshot_manager,
            artifact_manager=artifact_manager,
            run_directory_manager=run_directory_manager,
            progress_display=progress,
        )

        # Create mock phase runner that completes all phases
        mock_runner = MockPhaseRunner({})
        orchestrator.set_phase_runner(mock_runner)

        # Run
        orchestrator.run("Test feature")

        # Verify all phases were displayed
        output_text = output.getvalue()
        assert "PLAN" in output_text
        assert "BUILD" in output_text
        assert "VERIFY" in output_text
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

        orchestrator = Orchestrator(
            runs_dir=tmp_path,
            context_manager=context_manager,
            snapshot_manager=snapshot_manager,
            artifact_manager=artifact_manager,
            run_directory_manager=run_directory_manager,
            progress_display=progress,
        )

        mock_runner = MockPhaseRunner({})
        orchestrator.set_phase_runner(mock_runner)

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

        orchestrator = Orchestrator(
            runs_dir=tmp_path,
            context_manager=context_manager,
            snapshot_manager=snapshot_manager,
            artifact_manager=artifact_manager,
            run_directory_manager=run_directory_manager,
            progress_display=progress,
        )

        # Create runner that fails on build phase
        class FailingPhaseRunner:
            def run(self, phase: str, context: RunContext) -> PhaseResult:
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

        orchestrator.set_phase_runner(FailingPhaseRunner())

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

        orchestrator = Orchestrator(
            runs_dir=tmp_path,
            context_manager=context_manager,
            snapshot_manager=snapshot_manager,
            artifact_manager=artifact_manager,
            run_directory_manager=run_directory_manager,
            progress_display=progress,
        )

        mock_runner = MockPhaseRunner({})
        orchestrator.set_phase_runner(mock_runner)

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

        orchestrator = Orchestrator(
            runs_dir=tmp_path,
            context_manager=context_manager,
            snapshot_manager=snapshot_manager,
            artifact_manager=artifact_manager,
            run_directory_manager=run_directory_manager,
            progress_display=progress,
        )

        # Create runner that fails on verify phase
        class FailingPhaseRunner:
            def run(self, phase: str, context: RunContext) -> PhaseResult:
                if phase == "verify":
                    raise LLMError(
                        code="LLM_ERROR",
                        message="Verification failed",
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

        orchestrator.set_phase_runner(FailingPhaseRunner())

        with pytest.raises(LLMError):
            orchestrator.run("Test feature")

        # Verify pipeline summary is shown with failed status
        output_text = output.getvalue()
        assert "Pipeline Summary" in output_text
        assert "failed" in output_text


class TestPhaseRunnerProgressIntegration:
    """Integration tests for PhaseRunner with ProgressDisplay."""

    @pytest.fixture
    def mock_executor(self) -> Mock:
        """Create mock executor that returns LLM result."""
        executor = Mock()
        executor.execute.return_value = LLMResult(
            success=True,
            content="Test output",
            tokens_used=500,
            tool_calls=[],
        )
        return executor

    @pytest.fixture
    def mock_command_resolver(self, tmp_path: Path) -> Mock:
        """Create mock command resolver."""
        # Create a prompt file
        command_path = tmp_path / "commands" / "plan"
        command_path.mkdir(parents=True)
        (command_path / "prompt.md").write_text("Test prompt {{ feature }}")

        resolver = Mock()
        resolver.resolve.return_value = ResolvedCommand(
            name="plan",
            path=command_path,
            tier="project",
            has_pre_hook=False,
            has_post_hook=False,
        )
        return resolver

    def test_phase_runner_calls_llm_progress_methods(
        self,
        tmp_path: Path,
        mock_executor: Mock,
        mock_command_resolver: Mock,
    ) -> None:
        """Test that PhaseRunner calls LLM progress methods."""
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=80)
        progress = ProgressDisplay(console)

        # Track method calls
        llm_start_called = False
        llm_progress_called = False
        llm_complete_called = False

        original_start = progress.on_llm_start
        original_progress = progress.on_llm_progress
        original_complete = progress.on_llm_complete

        def track_start() -> None:
            nonlocal llm_start_called
            llm_start_called = True
            original_start()

        def track_progress(tokens: int) -> None:
            nonlocal llm_progress_called
            llm_progress_called = True
            original_progress(tokens)

        def track_complete() -> None:
            nonlocal llm_complete_called
            llm_complete_called = True
            original_complete()

        progress.on_llm_start = track_start
        progress.on_llm_progress = track_progress
        progress.on_llm_complete = track_complete

        template_engine = Mock()
        template_engine.render.return_value = "Rendered prompt"

        hook_runner = Mock()

        artifact_manager = Mock()
        artifact_manager.get_artifact_paths.return_value = {}

        runner = PhaseRunner(
            command_resolver=mock_command_resolver,
            template_engine=template_engine,
            hook_runner=hook_runner,
            executor=mock_executor,
            artifact_manager=artifact_manager,
            progress_display=progress,
        )

        context = RunContext(
            run_id=str(ULID()),
            feature_description="Test",
            current_phase="plan",
            started_at=datetime.now(UTC),
            status="running",
        )

        runner.run("plan", context)

        assert llm_start_called, "on_llm_start was not called"
        assert llm_progress_called, "on_llm_progress was not called"
        assert llm_complete_called, "on_llm_complete was not called"

    def test_phase_runner_completes_llm_progress_on_error(
        self,
        tmp_path: Path,
        mock_command_resolver: Mock,
    ) -> None:
        """Test that PhaseRunner completes LLM progress display on error."""
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=80)
        progress = ProgressDisplay(console)

        # Create executor that fails
        failing_executor = Mock()
        failing_executor.execute.side_effect = LLMError(
            code="LLM_ERROR",
            message="Execution failed",
            suggestion="Try again",
            recoverable=True,
        )

        template_engine = Mock()
        template_engine.render.return_value = "Rendered prompt"

        hook_runner = Mock()

        artifact_manager = Mock()
        artifact_manager.get_artifact_paths.return_value = {}

        runner = PhaseRunner(
            command_resolver=mock_command_resolver,
            template_engine=template_engine,
            hook_runner=hook_runner,
            executor=failing_executor,
            artifact_manager=artifact_manager,
            progress_display=progress,
        )

        context = RunContext(
            run_id=str(ULID()),
            feature_description="Test",
            current_phase="plan",
            started_at=datetime.now(UTC),
            status="running",
        )

        with pytest.raises(LLMError):
            runner.run("plan", context)

        # Progress display should be cleaned up
        assert progress._live is None
        assert progress._progress is None


class TestProgressDisplayWithRealConsole:
    """Tests that verify ProgressDisplay output format."""

    def test_full_pipeline_progress_output(self) -> None:
        """Test that full pipeline produces expected output."""
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=80)
        progress = ProgressDisplay(console)

        # Simulate full pipeline execution
        for phase in ["plan", "build", "verify", "validate", "document"]:
            progress.on_phase_start(phase)

            progress.on_llm_start()
            progress.on_llm_progress(100)
            progress.on_llm_progress(250)
            progress.on_llm_progress(500)
            progress.on_llm_complete()

            result = PhaseResult(
                phase=phase,
                status=PhaseStatus.COMPLETED,
                started_at=datetime.now(UTC),
                completed_at=datetime.now(UTC),
                artifacts=[f"{phase}_output.md"],
                tokens_used=500,
            )
            progress.on_phase_complete(phase, result)

        progress.show_pipeline_summary(
            completed_phases=["plan", "build", "verify", "validate", "document"],
            status="completed",
            total_duration_ms=30000,
            total_tokens=2500,
        )

        output_text = output.getvalue()

        # Verify all phases are mentioned
        assert "PLAN" in output_text
        assert "BUILD" in output_text
        assert "VERIFY" in output_text
        assert "VALIDATE" in output_text
        assert "DOCUMENT" in output_text

        # Verify completion indicators
        assert "completed" in output_text

        # Verify summary
        assert "2,500" in output_text  # Total tokens formatted
