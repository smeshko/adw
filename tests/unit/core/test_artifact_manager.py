"""Unit tests for ArtifactManager.

Tests artifact storage, retrieval, listing, and JSON convenience methods.
"""

from pathlib import Path

import pytest

from adw.core.artifact_manager import ArtifactManager


@pytest.fixture
def runs_dir(tmp_path: Path) -> Path:
    """Create a temporary runs directory."""
    runs_dir = tmp_path / ".adw" / "runs"
    runs_dir.mkdir(parents=True)
    return runs_dir


@pytest.fixture
def artifact_manager(runs_dir: Path) -> ArtifactManager:
    """Create an ArtifactManager with temporary runs directory."""
    return ArtifactManager(runs_dir)


@pytest.fixture
def run_id() -> str:
    """Sample run ID for testing."""
    return "01TESTRUNID123456789"


class TestArtifactManagerInit:
    """Tests for ArtifactManager initialization."""

    def test_init_sets_runs_dir(self, runs_dir: Path) -> None:
        """Test that init stores the runs directory path."""
        manager = ArtifactManager(runs_dir)
        assert manager.runs_dir == runs_dir


class TestArtifactManagerStore:
    """Tests for artifact storage."""

    def test_store_creates_artifact_file(
        self,
        artifact_manager: ArtifactManager,
        runs_dir: Path,
        run_id: str,
    ) -> None:
        """Test that store creates the artifact file."""
        # Arrange - create run artifacts dir
        artifacts_dir = runs_dir / run_id / "artifacts" / "build"
        artifacts_dir.mkdir(parents=True)

        # Act
        path = artifact_manager.store(run_id, "build", "diff.txt", "line1\nline2")

        # Assert
        assert path.exists()
        assert path.read_text() == "line1\nline2"
        assert path.parent.name == "build"
        assert path.name == "diff.txt"

    def test_store_creates_phase_directory(
        self,
        artifact_manager: ArtifactManager,
        runs_dir: Path,
        run_id: str,
    ) -> None:
        """Test that store creates phase directory if it doesn't exist."""
        # Arrange - create only the run directory
        run_dir = runs_dir / run_id
        run_dir.mkdir(parents=True)

        # Act
        path = artifact_manager.store(run_id, "validate", "evidence.json", "{}")

        # Assert
        assert path.exists()
        assert path.parent.name == "validate"

    def test_store_binary_content(
        self,
        artifact_manager: ArtifactManager,
        runs_dir: Path,
        run_id: str,
    ) -> None:
        """Test that store handles binary content."""
        # Arrange
        run_dir = runs_dir / run_id
        run_dir.mkdir(parents=True)
        binary_data = b"\x00\x01\x02\x03\xff"

        # Act
        path = artifact_manager.store(run_id, "build", "data.bin", binary_data)

        # Assert
        assert path.exists()
        assert path.read_bytes() == binary_data

    def test_store_returns_artifact_path(
        self,
        artifact_manager: ArtifactManager,
        runs_dir: Path,
        run_id: str,
    ) -> None:
        """Test that store returns the correct path."""
        run_dir = runs_dir / run_id
        run_dir.mkdir(parents=True)

        path = artifact_manager.store(run_id, "build", "result.txt", "content")

        expected = runs_dir / run_id / "artifacts" / "build" / "result.txt"
        assert path == expected


class TestArtifactManagerGet:
    """Tests for artifact retrieval."""

    def test_get_returns_text_content(
        self,
        artifact_manager: ArtifactManager,
        runs_dir: Path,
        run_id: str,
    ) -> None:
        """Test that get returns text content."""
        # Arrange
        artifacts_dir = runs_dir / run_id / "artifacts" / "build"
        artifacts_dir.mkdir(parents=True)
        (artifacts_dir / "diff.txt").write_text("line1\nline2")

        # Act
        content = artifact_manager.get(run_id, "build", "diff.txt")

        # Assert
        assert content == "line1\nline2"

    def test_get_returns_none_for_missing(
        self,
        artifact_manager: ArtifactManager,
        run_id: str,
    ) -> None:
        """Test that get returns None for non-existent artifact."""
        result = artifact_manager.get(run_id, "build", "missing.txt")
        assert result is None

    def test_get_binary_content(
        self,
        artifact_manager: ArtifactManager,
        runs_dir: Path,
        run_id: str,
    ) -> None:
        """Test that get returns binary content when requested."""
        # Arrange
        artifacts_dir = runs_dir / run_id / "artifacts" / "build"
        artifacts_dir.mkdir(parents=True)
        binary_data = b"\x00\x01\x02\x03\xff"
        (artifacts_dir / "data.bin").write_bytes(binary_data)

        # Act
        content = artifact_manager.get(run_id, "build", "data.bin", binary=True)

        # Assert
        assert content == binary_data

    def test_get_head_returns_first_n_lines(
        self,
        artifact_manager: ArtifactManager,
        runs_dir: Path,
        run_id: str,
    ) -> None:
        """Test that get with head returns first N lines."""
        # Arrange
        artifacts_dir = runs_dir / run_id / "artifacts" / "build"
        artifacts_dir.mkdir(parents=True)
        content = "line1\nline2\nline3\nline4\nline5"
        (artifacts_dir / "log.txt").write_text(content)

        # Act
        result = artifact_manager.get(run_id, "build", "log.txt", head=2)

        # Assert
        assert result == "line1\nline2\n"

    def test_get_tail_returns_last_n_lines(
        self,
        artifact_manager: ArtifactManager,
        runs_dir: Path,
        run_id: str,
    ) -> None:
        """Test that get with tail returns last N lines."""
        # Arrange
        artifacts_dir = runs_dir / run_id / "artifacts" / "build"
        artifacts_dir.mkdir(parents=True)
        content = "line1\nline2\nline3\nline4\nline5"
        (artifacts_dir / "log.txt").write_text(content)

        # Act
        result = artifact_manager.get(run_id, "build", "log.txt", tail=2)

        # Assert
        assert result == "line4\nline5"

    def test_get_head_takes_precedence_over_tail(
        self,
        artifact_manager: ArtifactManager,
        runs_dir: Path,
        run_id: str,
    ) -> None:
        """Test that head takes precedence when both head and tail are set."""
        # Arrange
        artifacts_dir = runs_dir / run_id / "artifacts" / "build"
        artifacts_dir.mkdir(parents=True)
        content = "line1\nline2\nline3\nline4\nline5"
        (artifacts_dir / "log.txt").write_text(content)

        # Act - both head and tail set, head should win
        result = artifact_manager.get(run_id, "build", "log.txt", head=1, tail=1)

        # Assert
        assert result == "line1\n"


class TestArtifactManagerList:
    """Tests for artifact listing."""

    def test_list_artifacts_empty(
        self,
        artifact_manager: ArtifactManager,
        run_id: str,
    ) -> None:
        """Test that list returns empty for non-existent directory."""
        result = artifact_manager.list_artifacts(run_id)
        assert result == []

    def test_list_artifacts_all(
        self,
        artifact_manager: ArtifactManager,
        runs_dir: Path,
        run_id: str,
    ) -> None:
        """Test listing all artifacts."""
        # Arrange
        run_dir = runs_dir / run_id
        run_dir.mkdir(parents=True)
        artifact_manager.store(run_id, "build", "diff.txt", "diff content")
        artifact_manager.store(run_id, "validate", "evidence.json", "{}")

        # Act
        all_artifacts = artifact_manager.list_artifacts(run_id)

        # Assert
        assert len(all_artifacts) == 2
        phases = {a["phase"] for a in all_artifacts}
        assert phases == {"build", "validate"}

    def test_list_artifacts_by_phase(
        self,
        artifact_manager: ArtifactManager,
        runs_dir: Path,
        run_id: str,
    ) -> None:
        """Test listing artifacts filtered by phase."""
        # Arrange
        run_dir = runs_dir / run_id
        run_dir.mkdir(parents=True)
        artifact_manager.store(run_id, "build", "diff.txt", "diff content")
        artifact_manager.store(run_id, "validate", "evidence.json", "{}")

        # Act
        build_only = artifact_manager.list_artifacts(run_id, phase="build")

        # Assert
        assert len(build_only) == 1
        assert build_only[0]["name"] == "diff.txt"
        assert build_only[0]["phase"] == "build"

    def test_list_artifacts_includes_metadata(
        self,
        artifact_manager: ArtifactManager,
        runs_dir: Path,
        run_id: str,
    ) -> None:
        """Test that list includes size and modified time metadata."""
        # Arrange
        run_dir = runs_dir / run_id
        run_dir.mkdir(parents=True)
        artifact_manager.store(run_id, "build", "diff.txt", "content")

        # Act
        artifacts = artifact_manager.list_artifacts(run_id)

        # Assert
        assert len(artifacts) == 1
        assert "size" in artifacts[0]
        assert "modified" in artifacts[0]
        assert artifacts[0]["size"] == len("content")

    def test_list_artifacts_nonexistent_phase_returns_empty(
        self,
        artifact_manager: ArtifactManager,
        runs_dir: Path,
        run_id: str,
    ) -> None:
        """Test listing a specific phase that doesn't exist returns empty list."""
        # Arrange - create artifacts dir but not the specific phase
        artifacts_dir = runs_dir / run_id / "artifacts"
        artifacts_dir.mkdir(parents=True)

        # Act - request a phase that doesn't exist
        result = artifact_manager.list_artifacts(run_id, phase="nonexistent")

        # Assert
        assert result == []

    def test_list_artifacts_ignores_subdirectories(
        self,
        artifact_manager: ArtifactManager,
        runs_dir: Path,
        run_id: str,
    ) -> None:
        """Test that list_artifacts only returns files, not subdirectories."""
        # Arrange
        run_dir = runs_dir / run_id
        run_dir.mkdir(parents=True)
        artifact_manager.store(run_id, "build", "diff.txt", "content")

        # Create a subdirectory inside the phase dir (edge case)
        subdir = runs_dir / run_id / "artifacts" / "build" / "nested_dir"
        subdir.mkdir()

        # Act
        artifacts = artifact_manager.list_artifacts(run_id, phase="build")

        # Assert - should only have the file, not the directory
        assert len(artifacts) == 1
        assert artifacts[0]["name"] == "diff.txt"


class TestArtifactManagerJSON:
    """Tests for JSON convenience methods."""

    def test_store_and_get_json(
        self,
        artifact_manager: ArtifactManager,
        runs_dir: Path,
        run_id: str,
    ) -> None:
        """Test JSON storage and retrieval."""
        # Arrange
        run_dir = runs_dir / run_id
        run_dir.mkdir(parents=True)
        data = {"key": "value", "count": 42, "nested": {"a": 1}}

        # Act
        artifact_manager.store_json(run_id, "validate", "result.json", data)
        loaded = artifact_manager.get_json(run_id, "validate", "result.json")

        # Assert
        assert loaded == data

    def test_get_json_returns_none_for_missing(
        self,
        artifact_manager: ArtifactManager,
        run_id: str,
    ) -> None:
        """Test that get_json returns None for missing artifact."""
        result = artifact_manager.get_json(run_id, "validate", "missing.json")
        assert result is None

    def test_get_json_returns_none_for_invalid_json(
        self,
        artifact_manager: ArtifactManager,
        runs_dir: Path,
        run_id: str,
    ) -> None:
        """Test that get_json returns None for invalid JSON content."""
        # Arrange
        artifacts_dir = runs_dir / run_id / "artifacts" / "validate"
        artifacts_dir.mkdir(parents=True)
        (artifacts_dir / "invalid.json").write_text("not valid json {")

        # Act
        result = artifact_manager.get_json(run_id, "validate", "invalid.json")

        # Assert
        assert result is None


class TestArtifactManagerText:
    """Tests for text convenience methods."""

    def test_store_text_creates_artifact(
        self,
        artifact_manager: ArtifactManager,
        runs_dir: Path,
        run_id: str,
    ) -> None:
        """Test that store_text creates text file."""
        # Arrange
        run_dir = runs_dir / run_id
        run_dir.mkdir(parents=True)

        # Act
        path = artifact_manager.store_text(
            run_id, "build", "output.txt", "Hello world!"
        )

        # Assert
        assert path.exists()
        assert path.read_text() == "Hello world!"


class TestArtifactManagerAutoDetect:
    """Tests for auto-detection content type."""

    def test_get_auto_parses_json_files(
        self,
        artifact_manager: ArtifactManager,
        runs_dir: Path,
        run_id: str,
    ) -> None:
        """Test that get_auto parses JSON files."""
        # Arrange
        run_dir = runs_dir / run_id
        run_dir.mkdir(parents=True)
        artifact_manager.store_json(run_id, "validate", "result.json", {"key": "value"})

        # Act
        result = artifact_manager.get_auto(run_id, "validate", "result.json")

        # Assert
        assert result == {"key": "value"}

    def test_get_auto_returns_raw_text_for_non_json(
        self,
        artifact_manager: ArtifactManager,
        runs_dir: Path,
        run_id: str,
    ) -> None:
        """Test that get_auto returns raw text for non-JSON files."""
        # Arrange
        run_dir = runs_dir / run_id
        run_dir.mkdir(parents=True)
        artifact_manager.store_text(run_id, "build", "log.txt", "Log content")

        # Act
        result = artifact_manager.get_auto(run_id, "build", "log.txt")

        # Assert
        assert result == "Log content"

    def test_get_auto_returns_none_for_missing(
        self,
        artifact_manager: ArtifactManager,
        run_id: str,
    ) -> None:
        """Test that get_auto returns None for missing artifacts."""
        result = artifact_manager.get_auto(run_id, "build", "missing.json")
        assert result is None


class TestArtifactManagerErrorHandling:
    """Tests for error handling paths."""

    def test_store_raises_state_error_on_write_failure(
        self,
        artifact_manager: ArtifactManager,
        runs_dir: Path,
        run_id: str,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test that store raises StateError when write fails."""
        from adw.exceptions import StateError

        # Arrange - create run directory
        run_dir = runs_dir / run_id
        run_dir.mkdir(parents=True)

        # Mock open to raise OSError
        def mock_open_error(*args: object, **kwargs: object) -> None:
            raise OSError("Disk full")

        monkeypatch.setattr("builtins.open", mock_open_error)

        # Act & Assert
        with pytest.raises(StateError) as exc_info:
            artifact_manager.store(run_id, "build", "test.txt", "content")

        assert exc_info.value.code == "ARTIFACT_WRITE_FAILED"
        assert "build/test.txt" in exc_info.value.message

    def test_get_returns_none_on_read_error(
        self,
        artifact_manager: ArtifactManager,
        runs_dir: Path,
        run_id: str,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test that get returns None when read fails due to OSError."""
        # Arrange - create artifact file
        artifacts_dir = runs_dir / run_id / "artifacts" / "build"
        artifacts_dir.mkdir(parents=True)
        artifact_path = artifacts_dir / "secret.txt"
        artifact_path.write_text("content")

        # Mock read_text to raise OSError after exists check passes
        original_read_text = Path.read_text

        def mock_read_text(self: Path, *args: object, **kwargs: object) -> str:
            if self.name == "secret.txt":
                raise OSError("Permission denied")
            return original_read_text(self, *args, **kwargs)  # type: ignore[arg-type]

        monkeypatch.setattr(Path, "read_text", mock_read_text)

        # Act
        result = artifact_manager.get(run_id, "build", "secret.txt")

        # Assert - should return None, not raise
        assert result is None


class TestArtifactPaths:
    """Tests for artifact path tracking."""

    def test_get_artifact_paths(
        self,
        artifact_manager: ArtifactManager,
        runs_dir: Path,
        run_id: str,
    ) -> None:
        """Test getting artifact paths grouped by phase."""
        # Arrange
        run_dir = runs_dir / run_id
        run_dir.mkdir(parents=True)
        artifact_manager.store(run_id, "build", "diff.txt", "diff")
        artifact_manager.store(run_id, "build", "log.txt", "log")
        artifact_manager.store(run_id, "validate", "evidence.json", "{}")

        # Act
        paths = artifact_manager.get_artifact_paths(run_id)

        # Assert
        assert "build" in paths
        assert "validate" in paths
        assert set(paths["build"]) == {"diff.txt", "log.txt"}
        assert paths["validate"] == ["evidence.json"]

    def test_get_artifact_paths_empty(
        self,
        artifact_manager: ArtifactManager,
        run_id: str,
    ) -> None:
        """Test getting artifact paths for empty run."""
        paths = artifact_manager.get_artifact_paths(run_id)
        assert paths == {}


class TestArtifactPathsRunContextIntegration:
    """Tests for artifact path tracking integration with RunContext."""

    def test_artifact_paths_compatible_with_run_context(
        self,
        artifact_manager: ArtifactManager,
        runs_dir: Path,
        run_id: str,
    ) -> None:
        """Test get_artifact_paths returns type compatible with RunContext."""
        from datetime import datetime

        from adw.models import RunContext

        # Arrange - store some artifacts
        run_dir = runs_dir / run_id
        run_dir.mkdir(parents=True)
        artifact_manager.store(run_id, "build", "diff.txt", "diff")
        artifact_manager.store(run_id, "validate", "evidence.json", "{}")

        # Act - get paths and use to update RunContext
        paths = artifact_manager.get_artifact_paths(run_id)

        context = RunContext(
            run_id="01HQKWZ0VDHNK0W4HSCZWJZXW1",
            feature_description="Test feature",
            current_phase="build",
            started_at=datetime.now(),
            artifacts=paths,  # This is the key integration test
        )

        # Assert - paths are correctly stored in context
        assert context.artifacts == {
            "build": ["diff.txt"],
            "validate": ["evidence.json"],
        }

    def test_artifact_paths_serializable_in_context(
        self,
        artifact_manager: ArtifactManager,
        runs_dir: Path,
        run_id: str,
    ) -> None:
        """Test that artifact paths serialize correctly with RunContext."""
        import json
        from datetime import datetime

        from adw.models import RunContext

        # Arrange
        run_dir = runs_dir / run_id
        run_dir.mkdir(parents=True)
        artifact_manager.store(run_id, "build", "diff.txt", "diff")

        paths = artifact_manager.get_artifact_paths(run_id)
        context = RunContext(
            run_id="01HQKWZ0VDHNK0W4HSCZWJZXW1",
            feature_description="Test feature",
            current_phase="build",
            started_at=datetime.now(),
            artifacts=paths,
        )

        # Act - serialize to JSON
        context_json = context.model_dump_json()
        parsed = json.loads(context_json)

        # Assert - artifacts key contains paths, not content
        assert "artifacts" in parsed
        assert parsed["artifacts"] == {"build": ["diff.txt"]}
        # Verify it's paths (strings), not content
        assert parsed["artifacts"]["build"][0] == "diff.txt"
