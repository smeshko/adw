"""Unit tests for ProjectRegistryManager.

Tests cover:
- register() - creates file if not exists, adds/updates entry
- unregister() - removes entry by path
- get_all() - returns all registered projects
- get_by_path() - finds project by path
- discover_from_index() - discovers unique projects from index.jsonl
- Edge cases: empty file, missing file, duplicate handling
"""

from datetime import UTC, datetime
from pathlib import Path

import pytest
import yaml

from adw.core.project_registry import ProjectRegistryManager
from adw.models.registry import RegisteredProject


class TestProjectRegistryManagerInit:
    """Tests for ProjectRegistryManager initialization."""

    def test_default_registry_path_uses_home_directory(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that default registry path is ~/.adw/projects.yaml when no env var set."""
        monkeypatch.delenv("ADW_TEST_REGISTRY_PATH", raising=False)
        manager = ProjectRegistryManager()
        expected = Path.home() / ".adw" / "projects.yaml"
        assert manager.registry_path == expected

    def test_custom_registry_path(self, tmp_path: Path) -> None:
        """Test that custom registry path can be provided."""
        custom_path = tmp_path / "custom" / "projects.yaml"
        manager = ProjectRegistryManager(registry_path=custom_path)
        assert manager.registry_path == custom_path

    def test_custom_path_takes_precedence_over_env_var(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that explicit registry_path takes precedence over environment variable."""
        env_path = tmp_path / "env" / "projects.yaml"
        custom_path = tmp_path / "custom" / "projects.yaml"
        monkeypatch.setenv("ADW_TEST_REGISTRY_PATH", str(env_path))

        manager = ProjectRegistryManager(registry_path=custom_path)
        assert manager.registry_path == custom_path

    def test_env_var_overrides_default(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that ADW_TEST_REGISTRY_PATH environment variable overrides default."""
        env_path = tmp_path / "test" / "projects.yaml"
        monkeypatch.setenv("ADW_TEST_REGISTRY_PATH", str(env_path))

        manager = ProjectRegistryManager()
        assert manager.registry_path == env_path


class TestRegister:
    """Tests for ProjectRegistryManager.register()."""

    def test_register_new_project(self, tmp_path: Path) -> None:
        """Test registering a new project creates entry."""
        registry_path = tmp_path / "projects.yaml"
        manager = ProjectRegistryManager(registry_path=registry_path)

        project_path = Path("/Users/dev/my-api")
        result = manager.register(project_path)

        assert result.path == str(project_path)
        assert result.name == "my-api"  # Default to directory name

    def test_register_with_custom_name(self, tmp_path: Path) -> None:
        """Test registering with custom name."""
        registry_path = tmp_path / "projects.yaml"
        manager = ProjectRegistryManager(registry_path=registry_path)

        project_path = Path("/Users/dev/my-api")
        result = manager.register(project_path, name="My Awesome API")

        assert result.path == str(project_path)
        assert result.name == "My Awesome API"

    def test_register_creates_file_if_not_exists(self, tmp_path: Path) -> None:
        """Test that register creates registry file if it doesn't exist."""
        registry_path = tmp_path / "projects.yaml"
        manager = ProjectRegistryManager(registry_path=registry_path)

        manager.register(Path("/Users/dev/my-api"))

        assert registry_path.exists()

    def test_register_creates_parent_directories(self, tmp_path: Path) -> None:
        """Test that register creates parent directories."""
        registry_path = tmp_path / "nested" / "dirs" / "projects.yaml"
        manager = ProjectRegistryManager(registry_path=registry_path)

        manager.register(Path("/Users/dev/my-api"))

        assert registry_path.exists()
        assert registry_path.parent.exists()

    def test_register_updates_existing(self, tmp_path: Path) -> None:
        """Test that registering same path updates existing entry."""
        registry_path = tmp_path / "projects.yaml"
        manager = ProjectRegistryManager(registry_path=registry_path)

        project_path = Path("/Users/dev/my-api")
        manager.register(project_path, name="old-name")
        result = manager.register(project_path, name="new-name")

        # Should have updated the name
        assert result.name == "new-name"

        # Should still be only one entry
        all_projects = manager.get_all()
        assert len(all_projects) == 1
        assert all_projects[0].name == "new-name"

    def test_register_sets_registered_at(self, tmp_path: Path) -> None:
        """Test that register sets registered_at timestamp."""
        registry_path = tmp_path / "projects.yaml"
        manager = ProjectRegistryManager(registry_path=registry_path)

        before = datetime.now(UTC)
        result = manager.register(Path("/Users/dev/my-api"))
        after = datetime.now(UTC)

        assert before <= result.registered_at <= after

    def test_register_multiple_projects(self, tmp_path: Path) -> None:
        """Test registering multiple different projects."""
        registry_path = tmp_path / "projects.yaml"
        manager = ProjectRegistryManager(registry_path=registry_path)

        manager.register(Path("/Users/dev/project-a"), name="Project A")
        manager.register(Path("/Users/dev/project-b"), name="Project B")

        all_projects = manager.get_all()
        assert len(all_projects) == 2
        names = {p.name for p in all_projects}
        assert names == {"Project A", "Project B"}


class TestUnregister:
    """Tests for ProjectRegistryManager.unregister()."""

    def test_unregister_removes_project(self, tmp_path: Path) -> None:
        """Test that unregister removes project from registry."""
        registry_path = tmp_path / "projects.yaml"
        manager = ProjectRegistryManager(registry_path=registry_path)

        project_path = Path("/Users/dev/my-api")
        manager.register(project_path)
        result = manager.unregister(project_path)

        assert result is True
        assert manager.get_all() == []

    def test_unregister_nonexistent_returns_false(self, tmp_path: Path) -> None:
        """Test that unregistering non-existent project returns False."""
        registry_path = tmp_path / "projects.yaml"
        manager = ProjectRegistryManager(registry_path=registry_path)

        result = manager.unregister(Path("/not/registered"))

        assert result is False

    def test_unregister_preserves_other_projects(self, tmp_path: Path) -> None:
        """Test that unregister only removes the specified project."""
        registry_path = tmp_path / "projects.yaml"
        manager = ProjectRegistryManager(registry_path=registry_path)

        manager.register(Path("/Users/dev/project-a"))
        manager.register(Path("/Users/dev/project-b"))
        manager.register(Path("/Users/dev/project-c"))

        manager.unregister(Path("/Users/dev/project-b"))

        all_projects = manager.get_all()
        assert len(all_projects) == 2
        paths = {p.path for p in all_projects}
        assert "/Users/dev/project-a" in paths
        assert "/Users/dev/project-c" in paths
        assert "/Users/dev/project-b" not in paths


class TestGetAll:
    """Tests for ProjectRegistryManager.get_all()."""

    def test_get_all_returns_registered_projects(self, tmp_path: Path) -> None:
        """Test that get_all returns all registered projects."""
        registry_path = tmp_path / "projects.yaml"
        manager = ProjectRegistryManager(registry_path=registry_path)

        manager.register(Path("/Users/dev/project-a"))
        manager.register(Path("/Users/dev/project-b"))

        all_projects = manager.get_all()

        assert len(all_projects) == 2
        assert all(isinstance(p, RegisteredProject) for p in all_projects)

    def test_get_all_empty_registry(self, tmp_path: Path) -> None:
        """Test that get_all returns empty list for empty registry."""
        registry_path = tmp_path / "projects.yaml"
        manager = ProjectRegistryManager(registry_path=registry_path)

        all_projects = manager.get_all()

        assert all_projects == []

    def test_get_all_missing_file(self, tmp_path: Path) -> None:
        """Test that get_all returns empty list when file doesn't exist."""
        registry_path = tmp_path / "nonexistent.yaml"
        manager = ProjectRegistryManager(registry_path=registry_path)

        all_projects = manager.get_all()

        assert all_projects == []


class TestGetByPath:
    """Tests for ProjectRegistryManager.get_by_path()."""

    def test_get_by_path_finds_project(self, tmp_path: Path) -> None:
        """Test that get_by_path finds registered project."""
        registry_path = tmp_path / "projects.yaml"
        manager = ProjectRegistryManager(registry_path=registry_path)

        project_path = Path("/Users/dev/my-api")
        manager.register(project_path, name="My API")

        result = manager.get_by_path(project_path)

        assert result is not None
        assert result.path == str(project_path)
        assert result.name == "My API"

    def test_get_by_path_returns_none_for_unregistered(
        self, tmp_path: Path
    ) -> None:
        """Test that get_by_path returns None for unregistered path."""
        registry_path = tmp_path / "projects.yaml"
        manager = ProjectRegistryManager(registry_path=registry_path)

        result = manager.get_by_path(Path("/not/registered"))

        assert result is None

    def test_get_by_path_resolves_path(self, tmp_path: Path) -> None:
        """Test that get_by_path resolves path for comparison."""
        registry_path = tmp_path / "projects.yaml"
        manager = ProjectRegistryManager(registry_path=registry_path)

        # Register with resolved path
        project_path = tmp_path / "my-project"
        project_path.mkdir()
        manager.register(project_path)

        # Query with same resolved path should find it
        result = manager.get_by_path(project_path)
        assert result is not None


class TestDiscoverFromIndex:
    """Tests for ProjectRegistryManager.discover_from_index()."""

    def test_discover_from_index_returns_unique_projects(
        self, tmp_path: Path
    ) -> None:
        """Test that discover_from_index returns unique projects from index."""
        registry_path = tmp_path / "projects.yaml"
        index_path = tmp_path / "index.jsonl"
        manager = ProjectRegistryManager(registry_path=registry_path)

        # Create mock index with multiple runs from same projects
        _create_mock_index(
            index_path,
            [
                {"project_path": "/Users/dev/project-a", "project_name": "project-a"},
                {"project_path": "/Users/dev/project-a", "project_name": "project-a"},
                {"project_path": "/Users/dev/project-b", "project_name": "project-b"},
            ],
        )

        projects = manager.discover_from_index(index_path=index_path)

        # Should return unique projects only
        assert len(projects) == 2
        paths = {p.path for p in projects}
        assert "/Users/dev/project-a" in paths
        assert "/Users/dev/project-b" in paths

    def test_discover_from_index_empty_index(self, tmp_path: Path) -> None:
        """Test that discover returns empty list for empty index."""
        registry_path = tmp_path / "projects.yaml"
        index_path = tmp_path / "index.jsonl"
        index_path.touch()  # Create empty file
        manager = ProjectRegistryManager(registry_path=registry_path)

        projects = manager.discover_from_index(index_path=index_path)

        assert projects == []

    def test_discover_from_index_missing_file(self, tmp_path: Path) -> None:
        """Test that discover returns empty list when index doesn't exist."""
        registry_path = tmp_path / "projects.yaml"
        index_path = tmp_path / "nonexistent.jsonl"
        manager = ProjectRegistryManager(registry_path=registry_path)

        projects = manager.discover_from_index(index_path=index_path)

        assert projects == []


class TestYAMLPersistence:
    """Tests for YAML file persistence."""

    def test_registry_persists_as_yaml(self, tmp_path: Path) -> None:
        """Test that registry is stored as valid YAML."""
        registry_path = tmp_path / "projects.yaml"
        manager = ProjectRegistryManager(registry_path=registry_path)

        manager.register(Path("/Users/dev/my-api"), name="my-api")

        # Read raw YAML and verify structure
        with open(registry_path) as f:
            data = yaml.safe_load(f)

        assert "projects" in data
        assert len(data["projects"]) == 1
        assert data["projects"][0]["path"] == "/Users/dev/my-api"
        assert data["projects"][0]["name"] == "my-api"

    def test_registry_survives_reload(self, tmp_path: Path) -> None:
        """Test that registry data survives manager reload."""
        registry_path = tmp_path / "projects.yaml"

        # Register with first manager
        manager1 = ProjectRegistryManager(registry_path=registry_path)
        manager1.register(Path("/Users/dev/my-api"), name="my-api")

        # Load with second manager
        manager2 = ProjectRegistryManager(registry_path=registry_path)
        all_projects = manager2.get_all()

        assert len(all_projects) == 1
        assert all_projects[0].name == "my-api"


def _create_mock_index(path: Path, entries: list[dict]) -> None:
    """Create a mock index.jsonl file for testing."""
    import json
    from datetime import UTC, datetime

    with open(path, "w") as f:
        for i, entry in enumerate(entries):
            full_entry = {
                "run_id": f"01KDSG2VDHNK0W4HSCZWJZXWS{i:01d}",
                "project_path": entry["project_path"],
                "project_name": entry["project_name"],
                "feature_description": "Test feature",
                "started_at": datetime.now(UTC).isoformat(),
                "completed_at": None,
                "status": "completed",
                "phase_reached": "validate",
                "phases_completed": ["plan", "build", "validate"],
            }
            f.write(json.dumps(full_entry) + "\n")
