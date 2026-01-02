"""Integration tests for artifact flow between phases.

These tests verify that artifacts correctly flow from earlier phases to later
phases, ensuring content integrity throughout the pipeline.
"""

from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from ulid import ULID

from adw.commands.resolver import CommandResolver
from adw.commands.template import TemplateEngine
from adw.core.artifact_manager import ArtifactManager
from adw.core.phase_runner import PhaseRunner
from adw.models import RunContext


def make_run_id() -> str:
    """Generate a valid ULID run ID."""
    return str(ULID())


@pytest.fixture
def integration_runs_dir(tmp_path: Path) -> Path:
    """Create a temporary runs directory for integration tests."""
    runs_dir = tmp_path / "runs"
    runs_dir.mkdir()
    return runs_dir


@pytest.fixture
def integration_artifact_manager(integration_runs_dir: Path) -> ArtifactManager:
    """Create an ArtifactManager for integration tests."""
    return ArtifactManager(integration_runs_dir)


@pytest.fixture
def integration_template_engine(tmp_path: Path) -> TemplateEngine:
    """Create a TemplateEngine for integration tests."""
    return TemplateEngine(project_root=tmp_path)


@pytest.fixture
def integration_phase_runner(
    integration_artifact_manager: ArtifactManager,
    integration_template_engine: TemplateEngine,
) -> PhaseRunner:
    """Create a PhaseRunner for integration tests."""
    mock_resolver = MagicMock(spec=CommandResolver)
    mock_hook_runner = MagicMock()
    mock_executor = MagicMock()

    return PhaseRunner(
        command_resolver=mock_resolver,
        template_engine=integration_template_engine,
        hook_runner=mock_hook_runner,
        executor=mock_executor,
        artifact_manager=integration_artifact_manager,
    )


class TestPlanToBuildArtifactFlow:
    """Integration tests for plan -> build artifact flow."""

    def test_plan_artifact_available_in_build_phase(
        self,
        integration_phase_runner: PhaseRunner,
        integration_artifact_manager: ArtifactManager,
    ) -> None:
        """Test that plan.md artifact is accessible when building."""
        run_id = make_run_id()

        # Simulate plan phase producing an artifact
        plan_content = """# Implementation Plan

## Steps
1. Create new module
2. Add API endpoint
3. Write tests

## Technical Details
- Use Python 3.13
- Follow existing patterns
"""
        integration_artifact_manager.store(run_id, "plan", "plan.md", plan_content)

        # When build phase starts, it should have access to plan
        artifacts_map = integration_phase_runner._build_artifacts_map(run_id, "build")

        assert "plan" in artifacts_map
        assert "plan" in artifacts_map["plan"]
        assert "Implementation Plan" in artifacts_map["plan"]["plan"]
        assert "Create new module" in artifacts_map["plan"]["plan"]

    def test_multiple_plan_artifacts_available_in_build(
        self,
        integration_phase_runner: PhaseRunner,
        integration_artifact_manager: ArtifactManager,
    ) -> None:
        """Test that multiple plan artifacts are accessible in build phase."""
        run_id = make_run_id()

        # Plan phase produces multiple artifacts
        integration_artifact_manager.store(
            run_id, "plan", "plan.md", "# Main Plan\nSteps..."
        )
        integration_artifact_manager.store(
            run_id, "plan", "notes.md", "# Additional Notes\nConsiderations..."
        )

        artifacts_map = integration_phase_runner._build_artifacts_map(run_id, "build")

        assert len(artifacts_map["plan"]) == 2
        assert "plan" in artifacts_map["plan"]
        assert "notes" in artifacts_map["plan"]


class TestBuildToVerifyArtifactFlow:
    """Integration tests for build -> verify artifact flow."""

    def test_build_diff_available_in_verify_phase(
        self,
        integration_phase_runner: PhaseRunner,
        integration_artifact_manager: ArtifactManager,
    ) -> None:
        """Test that build diff is accessible for verification."""
        run_id = make_run_id()

        # Plan and build phases produce artifacts
        integration_artifact_manager.store(run_id, "plan", "plan.md", "# Plan")
        diff_content = """diff --git a/src/module.py b/src/module.py
new file mode 100644
--- /dev/null
+++ b/src/module.py
@@ -0,0 +1,20 @@
+def new_function():
+    return True
"""
        integration_artifact_manager.store(run_id, "build", "diff.txt", diff_content)

        # Verify phase should have access to both plan and build
        artifacts_map = integration_phase_runner._build_artifacts_map(run_id, "verify")

        assert "plan" in artifacts_map
        assert "build" in artifacts_map
        assert "diff" in artifacts_map["build"]
        assert "new_function" in artifacts_map["build"]["diff"]

    def test_build_summary_available_for_verification(
        self,
        integration_phase_runner: PhaseRunner,
        integration_artifact_manager: ArtifactManager,
    ) -> None:
        """Test that build summary is accessible for verification."""
        run_id = make_run_id()

        integration_artifact_manager.store(run_id, "plan", "plan.md", "# Plan")
        build_summary = """# Build Summary

## Files Changed
- src/module.py (NEW)
- tests/test_module.py (NEW)

## Tests Run
- 10 tests passed
- 0 tests failed
"""
        integration_artifact_manager.store(
            run_id, "build", "build_output.md", build_summary
        )

        artifacts_map = integration_phase_runner._build_artifacts_map(run_id, "verify")

        assert "build_output" in artifacts_map["build"]
        assert "10 tests passed" in artifacts_map["build"]["build_output"]


class TestFullPipelineArtifactContinuity:
    """Integration tests for full pipeline artifact flow."""

    def test_all_previous_phases_available_in_validate(
        self,
        integration_phase_runner: PhaseRunner,
        integration_artifact_manager: ArtifactManager,
    ) -> None:
        """Test that validate phase has access to plan, build, and verify artifacts."""
        run_id = make_run_id()

        # Simulate full pipeline artifact production
        integration_artifact_manager.store(
            run_id, "plan", "plan.md", "# Implementation Plan"
        )
        integration_artifact_manager.store(
            run_id, "build", "diff.txt", "git diff output..."
        )
        integration_artifact_manager.store(
            run_id, "verify", "evidence.json", '{"passed": true, "tests": 42}'
        )

        # Validate phase should see all previous phases
        artifacts_map = integration_phase_runner._build_artifacts_map(run_id, "validate")

        assert "plan" in artifacts_map
        assert "build" in artifacts_map
        assert "verify" in artifacts_map
        assert "validate" not in artifacts_map  # Current phase excluded

    def test_artifact_content_integrity_preserved(
        self,
        integration_phase_runner: PhaseRunner,
        integration_artifact_manager: ArtifactManager,
    ) -> None:
        """Test that artifact content is preserved exactly through the pipeline."""
        run_id = make_run_id()

        # Store artifacts with specific content
        original_plan = "Line 1\nLine 2\nLine 3 with special chars: éàü @#$%"
        original_diff = "Binary-like content: \x00\x01\x02"  # Note: stored as text

        integration_artifact_manager.store(run_id, "plan", "plan.md", original_plan)
        integration_artifact_manager.store(run_id, "build", "diff.txt", original_diff)

        # Content should be exactly preserved
        artifacts_map = integration_phase_runner._build_artifacts_map(run_id, "verify")

        assert artifacts_map["plan"]["plan"] == original_plan
        assert artifacts_map["build"]["diff"] == original_diff

    def test_large_artifact_handling(
        self,
        integration_phase_runner: PhaseRunner,
        integration_artifact_manager: ArtifactManager,
    ) -> None:
        """Test that large artifacts are handled correctly."""
        run_id = make_run_id()

        # Create a large artifact (10KB)
        large_content = "x" * 10000 + "\n" + "y" * 10000

        integration_artifact_manager.store(run_id, "plan", "plan.md", large_content)

        artifacts_map = integration_phase_runner._build_artifacts_map(run_id, "build")

        assert len(artifacts_map["plan"]["plan"]) == len(large_content)
        assert artifacts_map["plan"]["plan"] == large_content


class TestArtifactContentIntegrity:
    """Integration tests for artifact content integrity."""

    def test_json_artifact_preserved_as_string(
        self,
        integration_phase_runner: PhaseRunner,
        integration_artifact_manager: ArtifactManager,
    ) -> None:
        """Test that JSON artifacts are preserved as strings for templates."""
        run_id = make_run_id()

        json_content = '{"key": "value", "nested": {"inner": true}}'
        integration_artifact_manager.store(
            run_id, "verify", "evidence.json", json_content
        )

        artifacts_map = integration_phase_runner._build_artifacts_map(run_id, "validate")

        # Should be raw string, not parsed JSON
        assert artifacts_map["verify"]["evidence"] == json_content
        assert isinstance(artifacts_map["verify"]["evidence"], str)

    def test_multiline_artifact_newlines_preserved(
        self,
        integration_phase_runner: PhaseRunner,
        integration_artifact_manager: ArtifactManager,
    ) -> None:
        """Test that multiline artifacts preserve newlines."""
        run_id = make_run_id()

        # Note: \r\n is normalized to \n by Python's read_text()
        multiline_content = "Line 1\nLine 2\nLine 3\n\nLine 5"
        integration_artifact_manager.store(
            run_id, "plan", "plan.md", multiline_content
        )

        artifacts_map = integration_phase_runner._build_artifacts_map(run_id, "build")

        assert artifacts_map["plan"]["plan"] == multiline_content

    def test_unicode_artifact_content_preserved(
        self,
        integration_phase_runner: PhaseRunner,
        integration_artifact_manager: ArtifactManager,
    ) -> None:
        """Test that Unicode content is preserved in artifacts."""
        run_id = make_run_id()

        unicode_content = "Hello 世界! Привет мир! مرحبا بالعالم"
        integration_artifact_manager.store(
            run_id, "plan", "plan.md", unicode_content
        )

        artifacts_map = integration_phase_runner._build_artifacts_map(run_id, "build")

        assert artifacts_map["plan"]["plan"] == unicode_content


class TestTemplateIntegrationWithArtifacts:
    """Integration tests for template rendering with real artifacts."""

    def test_template_renders_artifact_content(
        self,
        integration_phase_runner: PhaseRunner,
        integration_artifact_manager: ArtifactManager,
        integration_template_engine: TemplateEngine,
        tmp_path: Path,
    ) -> None:
        """Test that templates can render artifact content."""
        run_id = make_run_id()

        # Store artifacts
        integration_artifact_manager.store(
            run_id, "plan", "plan.md", "# The Plan\n\n1. Do X\n2. Do Y"
        )

        # Build artifacts map
        artifacts_map = integration_phase_runner._build_artifacts_map(run_id, "build")

        # Render template with artifacts
        template = """# Build Phase

Using plan:
{{artifacts.plan.plan}}

Now implementing...
"""
        result = integration_template_engine.render(
            template, {"artifacts": artifacts_map}
        )

        assert "# The Plan" in result
        assert "1. Do X" in result
        assert "2. Do Y" in result
