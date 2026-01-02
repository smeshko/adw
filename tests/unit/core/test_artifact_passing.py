"""Tests for artifact passing between phases.

This module tests the functionality that makes artifacts from earlier phases
available to later phases in templates, implementing Story 5.3.
"""

from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from ulid import ULID

from adw.commands.resolver import CommandResolver
from adw.commands.template import TemplateEngine
from adw.core.artifact_manager import ArtifactManager
from adw.core.phase_runner import PhaseRunner


def make_run_id() -> str:
    """Generate a valid ULID run ID."""
    return str(ULID())


@pytest.fixture
def tmp_runs_dir(tmp_path: Path) -> Path:
    """Create a temporary runs directory."""
    runs_dir = tmp_path / "runs"
    runs_dir.mkdir()
    return runs_dir


@pytest.fixture
def artifact_manager(tmp_runs_dir: Path) -> ArtifactManager:
    """Create an ArtifactManager with temporary storage."""
    return ArtifactManager(tmp_runs_dir)


@pytest.fixture
def template_engine(tmp_path: Path) -> TemplateEngine:
    """Create a TemplateEngine."""
    return TemplateEngine(project_root=tmp_path)


@pytest.fixture
def phase_runner(
    artifact_manager: ArtifactManager,
    template_engine: TemplateEngine,
) -> PhaseRunner:
    """Create a PhaseRunner with mocked dependencies."""
    mock_resolver = MagicMock(spec=CommandResolver)
    mock_hook_runner = MagicMock()
    mock_executor = MagicMock()

    return PhaseRunner(
        command_resolver=mock_resolver,
        template_engine=template_engine,
        hook_runner=mock_hook_runner,
        executor=mock_executor,
        artifact_manager=artifact_manager,
    )


class TestBuildArtifactsMap:
    """Tests for PhaseRunner._build_artifacts_map method."""

    def test_returns_empty_dict_when_no_artifacts_exist(
        self,
        phase_runner: PhaseRunner,
    ) -> None:
        """Test that empty dict is returned when no artifacts exist."""
        run_id = make_run_id()

        result = phase_runner._build_artifacts_map(run_id, "build")

        assert result == {}

    def test_loads_plan_artifact_for_build_phase(
        self,
        phase_runner: PhaseRunner,
        artifact_manager: ArtifactManager,
    ) -> None:
        """Test that plan artifacts are available when executing build phase."""
        run_id = make_run_id()

        # Store plan artifact
        artifact_manager.store(run_id, "plan", "plan.md", "# Implementation Plan\n\nStep 1: Do X")

        result = phase_runner._build_artifacts_map(run_id, "build")

        assert "plan" in result
        assert "plan" in result["plan"]
        assert "# Implementation Plan" in result["plan"]["plan"]

    def test_does_not_include_current_phase_artifacts(
        self,
        phase_runner: PhaseRunner,
        artifact_manager: ArtifactManager,
    ) -> None:
        """Test that current phase artifacts are not included in the map."""
        run_id = make_run_id()

        # Store plan and build artifacts
        artifact_manager.store(run_id, "plan", "plan.md", "Plan content")
        artifact_manager.store(run_id, "build", "build.md", "Build content")

        result = phase_runner._build_artifacts_map(run_id, "build")

        # Should only include plan, not build
        assert "plan" in result
        assert "build" not in result

    def test_includes_multiple_artifacts_from_single_phase(
        self,
        phase_runner: PhaseRunner,
        artifact_manager: ArtifactManager,
    ) -> None:
        """Test that multiple artifacts from a single phase are all included."""
        run_id = make_run_id()

        artifact_manager.store(run_id, "build", "diff.txt", "git diff output")
        artifact_manager.store(run_id, "build", "build_output.md", "Build summary")

        result = phase_runner._build_artifacts_map(run_id, "verify")

        assert "build" in result
        assert "diff" in result["build"]  # Extension stripped
        assert "build_output" in result["build"]

    def test_strips_file_extension_from_artifact_names(
        self,
        phase_runner: PhaseRunner,
        artifact_manager: ArtifactManager,
    ) -> None:
        """Test that file extensions are stripped for template access."""
        run_id = make_run_id()

        artifact_manager.store(run_id, "plan", "plan.md", "Plan content")
        artifact_manager.store(run_id, "plan", "notes.txt", "Notes content")

        result = phase_runner._build_artifacts_map(run_id, "build")

        # Keys should not have extensions
        assert "plan" in result["plan"]  # plan.md -> plan
        assert "notes" in result["plan"]  # notes.txt -> notes
        assert "plan.md" not in result["plan"]
        assert "notes.txt" not in result["plan"]

    def test_includes_all_previous_phases(
        self,
        phase_runner: PhaseRunner,
        artifact_manager: ArtifactManager,
    ) -> None:
        """Test that all previous phases' artifacts are included."""
        run_id = make_run_id()

        # Store artifacts for multiple phases
        artifact_manager.store(run_id, "plan", "plan.md", "Plan content")
        artifact_manager.store(run_id, "build", "diff.txt", "Diff content")
        artifact_manager.store(run_id, "verify", "evidence.json", '{"passed": true}')

        # When running validate phase, should have plan, build, verify
        result = phase_runner._build_artifacts_map(run_id, "validate")

        assert "plan" in result
        assert "build" in result
        assert "verify" in result
        assert "validate" not in result  # Current phase not included

    def test_skips_empty_phases(
        self,
        phase_runner: PhaseRunner,
        artifact_manager: ArtifactManager,
    ) -> None:
        """Test that phases with no artifacts are not included in the map."""
        run_id = make_run_id()

        # Only store plan artifact (no build)
        artifact_manager.store(run_id, "plan", "plan.md", "Plan content")

        result = phase_runner._build_artifacts_map(run_id, "verify")

        assert "plan" in result
        assert "build" not in result  # Empty phase not included


class TestArtifactsInTemplateVariables:
    """Tests for artifact content being passed to template rendering."""

    def test_artifacts_included_in_template_variables(
        self,
        phase_runner: PhaseRunner,
        artifact_manager: ArtifactManager,
        tmp_path: Path,
    ) -> None:
        """Test that artifacts map is included in template variables."""
        run_id = make_run_id()

        # Store plan artifact
        artifact_manager.store(run_id, "plan", "plan.md", "# My Plan")

        # Create mock context
        from adw.models import RunContext

        context = RunContext(
            run_id=run_id,
            feature_description="Test feature",
            current_phase="build",
            started_at=datetime.now(timezone.utc),
        )

        # Create a prompt file
        cmd_path = tmp_path / "commands" / "build"
        cmd_path.mkdir(parents=True)
        (cmd_path / "prompt.md").write_text("Plan: {{artifacts.plan.plan}}")

        # Mock the command resolver to return our command path
        from adw.models import ResolvedCommand

        mock_command = ResolvedCommand(
            name="build",
            path=cmd_path,
            tier="project",
            has_pre_hook=False,
            has_post_hook=False,
        )

        with patch.object(
            phase_runner.command_resolver, "resolve", return_value=mock_command
        ):
            # Call the private method directly to test
            result = phase_runner._load_and_render_prompt(
                phase="build",
                context=context,
                pre_hook_output="",
                command=mock_command,
            )

        assert "# My Plan" in result
