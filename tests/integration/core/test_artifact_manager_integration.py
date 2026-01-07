"""Integration tests for ArtifactManager.

Tests artifact lifecycle across phases and runs, including persistence
and content integrity verification.
"""

from datetime import datetime
from pathlib import Path

import pytest

from adw.core.artifact_manager import ArtifactManager
from adw.models import RunContext


@pytest.fixture
def project_root(tmp_path: Path) -> Path:
    """Create a temporary project root with .adw structure."""
    adw_dir = tmp_path / ".adw"
    adw_dir.mkdir()
    runs_dir = adw_dir / "runs"
    runs_dir.mkdir()
    return tmp_path


@pytest.fixture
def artifact_manager(project_root: Path) -> ArtifactManager:
    """Create an ArtifactManager for the project."""
    runs_dir = project_root / ".adw" / "runs"
    return ArtifactManager(runs_dir)


@pytest.fixture
def sample_run_context() -> RunContext:
    """Create a sample RunContext for testing."""
    return RunContext(
        run_id="01HQKWZ0VDHNK0W4HSCZWJZXW2",
        feature_description="Test feature implementation",
        current_phase="plan",
        started_at=datetime.now(),
    )


class TestArtifactLifecycle:
    """Tests for full artifact lifecycle across phases."""

    def test_full_phase_lifecycle_with_artifacts(
        self,
        artifact_manager: ArtifactManager,
        project_root: Path,
        sample_run_context: RunContext,
    ) -> None:
        """Test artifact creation and retrieval through phase progression."""
        run_id = sample_run_context.run_id

        # Create run directory
        run_dir = project_root / ".adw" / "runs" / run_id
        run_dir.mkdir(parents=True)

        # Phase 1: Plan - store plan output
        plan_content = {"objective": "Add feature X", "tasks": ["task1", "task2"]}
        artifact_manager.store_json(run_id, "plan", "plan_output.json", plan_content)

        # Verify plan artifact
        retrieved_plan = artifact_manager.get_json(run_id, "plan", "plan_output.json")
        assert retrieved_plan == plan_content

        # Phase 2: Build - store diff
        diff_content = """\
diff --git a/src/main.py b/src/main.py
+++ b/src/main.py
@@ -1,3 +1,5 @@
+def new_feature():
+    pass
"""
        artifact_manager.store_text(run_id, "build", "changes.diff", diff_content)

        # Verify build artifact
        retrieved_diff = artifact_manager.get(run_id, "build", "changes.diff")
        assert retrieved_diff == diff_content

        # Phase 3: Verify - store evidence
        evidence = {"test_results": {"passed": 5, "failed": 0}, "coverage": 85.5}
        artifact_manager.store_json(run_id, "validate", "evidence.json", evidence)

        # Verify all artifacts exist
        all_artifacts = artifact_manager.list_artifacts(run_id)
        phases = {a["phase"] for a in all_artifacts}
        assert phases == {"plan", "build", "validate"}

    def test_artifact_access_from_subsequent_phase(
        self,
        artifact_manager: ArtifactManager,
        project_root: Path,
    ) -> None:
        """Test that subsequent phases can access previous phase artifacts."""
        run_id = "01HQKWZ0VDHNK0W4HSCZWJZXW3"
        run_dir = project_root / ".adw" / "runs" / run_id
        run_dir.mkdir(parents=True)

        # Plan phase creates artifact
        plan_data = {"target_files": ["src/feature.py", "tests/test_feature.py"]}
        artifact_manager.store_json(run_id, "plan", "plan.json", plan_data)

        # Build phase reads plan artifact (simulating cross-phase access)
        plan_from_build = artifact_manager.get_json(run_id, "plan", "plan.json")
        assert plan_from_build is not None
        expected_files = ["src/feature.py", "tests/test_feature.py"]
        assert plan_from_build["target_files"] == expected_files

        # Build phase creates its own artifact based on plan
        build_result = {
            "files_modified": plan_from_build["target_files"],
            "lines_added": 100,
        }
        artifact_manager.store_json(run_id, "build", "result.json", build_result)

        # Verify phase reads both plan and build artifacts
        plan_for_verify = artifact_manager.get_json(run_id, "plan", "plan.json")
        build_for_verify = artifact_manager.get_json(run_id, "build", "result.json")

        assert plan_for_verify is not None
        assert build_for_verify is not None
        assert build_for_verify["files_modified"] == plan_for_verify["target_files"]


class TestArtifactPersistence:
    """Tests for artifact persistence across operations."""

    def test_artifact_persistence_across_runs(
        self,
        artifact_manager: ArtifactManager,
        project_root: Path,
    ) -> None:
        """Test that artifacts persist and are accessible in new sessions."""
        run_id_1 = "01HQKWZ0VDHNK0W4HSCZWJZXW4"
        run_id_2 = "01HQKWZ0VDHNK0W4HSCZWJZXW5"

        # Create directories for both runs
        for run_id in [run_id_1, run_id_2]:
            run_dir = project_root / ".adw" / "runs" / run_id
            run_dir.mkdir(parents=True)

        # First run stores artifact
        artifact_manager.store_json(run_id_1, "build", "output.json", {"run": 1})

        # Second run stores different artifact
        artifact_manager.store_json(run_id_2, "build", "output.json", {"run": 2})

        # Create a new ArtifactManager (simulating new session)
        new_manager = ArtifactManager(project_root / ".adw" / "runs")

        # Both runs' artifacts should be accessible
        run1_artifact = new_manager.get_json(run_id_1, "build", "output.json")
        run2_artifact = new_manager.get_json(run_id_2, "build", "output.json")

        assert run1_artifact == {"run": 1}
        assert run2_artifact == {"run": 2}

    def test_artifact_overwrites_cleanly(
        self,
        artifact_manager: ArtifactManager,
        project_root: Path,
    ) -> None:
        """Test that storing to same path overwrites previous content."""
        run_id = "01HQKWZ0VDHNK0W4HSCZWJZXW6"
        run_dir = project_root / ".adw" / "runs" / run_id
        run_dir.mkdir(parents=True)

        # Store initial content
        artifact_manager.store_text(run_id, "build", "log.txt", "Initial content")

        # Verify initial content
        content_v1 = artifact_manager.get(run_id, "build", "log.txt")
        assert content_v1 == "Initial content"

        # Overwrite with new content
        artifact_manager.store_text(run_id, "build", "log.txt", "Updated content")

        # Verify new content replaced old
        content_v2 = artifact_manager.get(run_id, "build", "log.txt")
        assert content_v2 == "Updated content"
        assert content_v2 != content_v1


class TestContentIntegrity:
    """Tests for artifact content integrity."""

    def test_binary_content_integrity(
        self,
        artifact_manager: ArtifactManager,
        project_root: Path,
    ) -> None:
        """Test that binary content is preserved exactly."""
        run_id = "01HQKWZ0VDHNK0W4HSCZWJZXW7"
        run_dir = project_root / ".adw" / "runs" / run_id
        run_dir.mkdir(parents=True)

        # Create binary content with all byte values
        binary_content = bytes(range(256))

        artifact_manager.store(run_id, "build", "binary.bin", binary_content)

        # Retrieve and verify exact match
        retrieved = artifact_manager.get(run_id, "build", "binary.bin", binary=True)
        assert retrieved == binary_content
        assert len(retrieved) == 256

    def test_unicode_content_integrity(
        self,
        artifact_manager: ArtifactManager,
        project_root: Path,
    ) -> None:
        """Test that unicode text content is preserved."""
        run_id = "01HQKWZ0VDHNK0W4HSCZWJZXW8"
        run_dir = project_root / ".adw" / "runs" / run_id
        run_dir.mkdir(parents=True)

        # Unicode content with various scripts
        unicode_content = "Hello 世界 🌍 مرحبا Привет"

        artifact_manager.store_text(run_id, "build", "unicode.txt", unicode_content)

        # Retrieve and verify
        retrieved = artifact_manager.get(run_id, "build", "unicode.txt")
        assert retrieved == unicode_content

    def test_large_content_integrity(
        self,
        artifact_manager: ArtifactManager,
        project_root: Path,
    ) -> None:
        """Test that large content is handled correctly."""
        run_id = "01HQKWZ0VDHNK0W4HSCZWJZXW9"
        run_dir = project_root / ".adw" / "runs" / run_id
        run_dir.mkdir(parents=True)

        # Create 1MB of content
        large_content = "x" * (1024 * 1024)

        artifact_manager.store_text(run_id, "build", "large.txt", large_content)

        # Retrieve and verify
        retrieved = artifact_manager.get(run_id, "build", "large.txt")
        assert retrieved == large_content
        assert len(retrieved) == 1024 * 1024

    def test_json_roundtrip_integrity(
        self,
        artifact_manager: ArtifactManager,
        project_root: Path,
    ) -> None:
        """Test that complex JSON structures survive roundtrip."""
        run_id = "01HQKWZ0VDHNK0W4HSCZWJZXWA"
        run_dir = project_root / ".adw" / "runs" / run_id
        run_dir.mkdir(parents=True)

        complex_data = {
            "string": "hello",
            "number": 42,
            "float": 3.14159,
            "boolean": True,
            "null": None,
            "array": [1, 2, 3, {"nested": "value"}],
            "object": {
                "deeply": {
                    "nested": {
                        "value": [1, 2, 3],
                    }
                }
            },
        }

        artifact_manager.store_json(run_id, "validate", "complex.json", complex_data)

        retrieved = artifact_manager.get_json(run_id, "validate", "complex.json")
        assert retrieved == complex_data


class TestRunContextIntegration:
    """Tests for integration with RunContext artifacts field."""

    def test_update_run_context_with_artifact_paths(
        self,
        artifact_manager: ArtifactManager,
        project_root: Path,
    ) -> None:
        """Test updating RunContext with artifact paths after each store."""
        run_id = "01HQKWZ0VDHNK0W4HSCZWJZXWB"
        run_dir = project_root / ".adw" / "runs" / run_id
        run_dir.mkdir(parents=True)

        # Create initial context
        context = RunContext(
            run_id=run_id,
            feature_description="Test feature",
            current_phase="plan",
            started_at=datetime.now(),
        )
        assert context.artifacts == {}

        # Store artifact and update context
        artifact_manager.store_json(run_id, "plan", "output.json", {"task": "plan"})
        context = context.model_copy(
            update={"artifacts": artifact_manager.get_artifact_paths(run_id)}
        )
        assert context.artifacts == {"plan": ["output.json"]}

        # Add more artifacts
        artifact_manager.store_text(run_id, "build", "diff.txt", "diff content")
        artifact_manager.store_json(run_id, "build", "result.json", {"success": True})
        context = context.model_copy(
            update={"artifacts": artifact_manager.get_artifact_paths(run_id)}
        )

        assert "plan" in context.artifacts
        assert "build" in context.artifacts
        assert set(context.artifacts["build"]) == {"diff.txt", "result.json"}

    def test_serialize_context_with_artifacts_to_file(
        self,
        artifact_manager: ArtifactManager,
        project_root: Path,
    ) -> None:
        """Test that context with artifacts can be serialized and restored."""
        import json

        run_id = "01HQKWZ0VDHNK0W4HSCZWJZXWC"
        run_dir = project_root / ".adw" / "runs" / run_id
        run_dir.mkdir(parents=True)

        # Create artifacts
        artifact_manager.store_json(run_id, "plan", "plan.json", {"step": 1})
        artifact_manager.store_text(run_id, "build", "log.txt", "build log")

        # Create context with artifact paths
        context = RunContext(
            run_id=run_id,
            feature_description="Serialization test",
            current_phase="validate",
            started_at=datetime.now(),
            artifacts=artifact_manager.get_artifact_paths(run_id),
        )

        # Serialize to file
        context_path = run_dir / "context.json"
        context_path.write_text(context.model_dump_json(indent=2))

        # Restore from file
        restored_data = json.loads(context_path.read_text())
        restored_context = RunContext(**restored_data)

        # Verify artifacts field preserved
        assert restored_context.artifacts == context.artifacts
        assert "plan" in restored_context.artifacts
        assert "build" in restored_context.artifacts

        # Verify we can still access actual artifacts using paths from context
        plan_artifact_name = restored_context.artifacts["plan"][0]
        plan_content = artifact_manager.get_json(run_id, "plan", plan_artifact_name)
        assert plan_content == {"step": 1}
