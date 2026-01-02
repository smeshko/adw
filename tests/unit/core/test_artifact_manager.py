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
        path = artifact_manager.store(run_id, "verify", "evidence.json", "{}")

        # Assert
        assert path.exists()
        assert path.parent.name == "verify"

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
        artifact_manager.store(run_id, "verify", "evidence.json", "{}")

        # Act
        all_artifacts = artifact_manager.list_artifacts(run_id)

        # Assert
        assert len(all_artifacts) == 2
        phases = {a["phase"] for a in all_artifacts}
        assert phases == {"build", "verify"}

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
        artifact_manager.store(run_id, "verify", "evidence.json", "{}")

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
        artifact_manager.store_json(run_id, "verify", "result.json", data)
        loaded = artifact_manager.get_json(run_id, "verify", "result.json")

        # Assert
        assert loaded == data

    def test_get_json_returns_none_for_missing(
        self,
        artifact_manager: ArtifactManager,
        run_id: str,
    ) -> None:
        """Test that get_json returns None for missing artifact."""
        result = artifact_manager.get_json(run_id, "verify", "missing.json")
        assert result is None

    def test_get_json_returns_none_for_invalid_json(
        self,
        artifact_manager: ArtifactManager,
        runs_dir: Path,
        run_id: str,
    ) -> None:
        """Test that get_json returns None for invalid JSON content."""
        # Arrange
        artifacts_dir = runs_dir / run_id / "artifacts" / "verify"
        artifacts_dir.mkdir(parents=True)
        (artifacts_dir / "invalid.json").write_text("not valid json {")

        # Act
        result = artifact_manager.get_json(run_id, "verify", "invalid.json")

        # Assert
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
        artifact_manager.store(run_id, "verify", "evidence.json", "{}")

        # Act
        paths = artifact_manager.get_artifact_paths(run_id)

        # Assert
        assert "build" in paths
        assert "verify" in paths
        assert set(paths["build"]) == {"diff.txt", "log.txt"}
        assert paths["verify"] == ["evidence.json"]

    def test_get_artifact_paths_empty(
        self,
        artifact_manager: ArtifactManager,
        run_id: str,
    ) -> None:
        """Test getting artifact paths for empty run."""
        paths = artifact_manager.get_artifact_paths(run_id)
        assert paths == {}
