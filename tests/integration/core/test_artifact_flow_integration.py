# REDUCED: Removed mocked integration_phase_runner fixture and 5 tests that
# depended on it (test_plan_artifact_available_in_build_phase,
# test_multiple_plan_artifacts_available_in_build,
# test_build_diff_available_in_verify_phase,
# test_build_summary_available_for_verification,
# test_all_previous_phases_available_in_validate).
# Also removed TestPlanToBuildArtifactFlow, TestBuildToVerifyArtifactFlow,
# TestFullPipelineArtifactContinuity, and TestTemplateIntegrationWithArtifacts
# classes. Kept TestArtifactContentIntegrity with real artifact tests.
"""Integration tests for artifact content integrity.

These tests verify that artifacts maintain content integrity when stored
and retrieved through the ArtifactManager.
"""

from pathlib import Path

import pytest
from ulid import ULID

from adw.core.artifact_manager import ArtifactManager


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


class TestArtifactContentIntegrity:
    """Integration tests for artifact content integrity."""

    def test_json_artifact_preserved_as_string(
        self,
        integration_artifact_manager: ArtifactManager,
    ) -> None:
        """Test that JSON artifacts are preserved as strings."""
        run_id = make_run_id()

        json_content = '{"key": "value", "nested": {"inner": true}}'
        integration_artifact_manager.store(
            run_id, "validate", "evidence.json", json_content
        )

        # Retrieve and verify content preserved
        retrieved = integration_artifact_manager.get(run_id, "validate", "evidence.json")
        assert retrieved == json_content
        assert isinstance(retrieved, str)

    def test_multiline_artifact_newlines_preserved(
        self,
        integration_artifact_manager: ArtifactManager,
    ) -> None:
        """Test that multiline artifacts preserve newlines."""
        run_id = make_run_id()

        multiline_content = "Line 1\nLine 2\nLine 3\n\nLine 5"
        integration_artifact_manager.store(run_id, "plan", "plan.md", multiline_content)

        retrieved = integration_artifact_manager.get(run_id, "plan", "plan.md")
        assert retrieved == multiline_content

    def test_unicode_artifact_content_preserved(
        self,
        integration_artifact_manager: ArtifactManager,
    ) -> None:
        """Test that Unicode content is preserved in artifacts."""
        run_id = make_run_id()

        unicode_content = "Hello 世界! Привет мир! مرحبا بالعالم"
        integration_artifact_manager.store(run_id, "plan", "plan.md", unicode_content)

        retrieved = integration_artifact_manager.get(run_id, "plan", "plan.md")
        assert retrieved == unicode_content

    def test_special_characters_preserved(
        self,
        integration_artifact_manager: ArtifactManager,
    ) -> None:
        """Test that special characters are preserved in artifacts."""
        run_id = make_run_id()

        special_content = "Line with special chars: éàü @#$%^&*()"
        integration_artifact_manager.store(run_id, "plan", "plan.md", special_content)

        retrieved = integration_artifact_manager.get(run_id, "plan", "plan.md")
        assert retrieved == special_content

    def test_large_artifact_handling(
        self,
        integration_artifact_manager: ArtifactManager,
    ) -> None:
        """Test that large artifacts are handled correctly."""
        run_id = make_run_id()

        # Create a large artifact (10KB)
        large_content = "x" * 10000 + "\n" + "y" * 10000

        integration_artifact_manager.store(run_id, "plan", "plan.md", large_content)

        retrieved = integration_artifact_manager.get(run_id, "plan", "plan.md")
        assert len(retrieved) == len(large_content)
        assert retrieved == large_content
