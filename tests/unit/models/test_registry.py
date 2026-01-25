"""Unit tests for ProjectRegistry model.

Tests cover:
- Model instantiation with required fields
- Default values for optional fields
- YAML serialization/deserialization round-trip
- Field validation (path, name, datetime)
- ProjectRegistry container model
"""

from datetime import UTC, datetime

import yaml

from adw.models.registry import ProjectRegistry, RegisteredProject


class TestRegisteredProjectModel:
    """Tests for RegisteredProject model instantiation and validation."""

    def test_create_registered_project_with_required_fields(self) -> None:
        """Test creating RegisteredProject with all required fields."""
        registered_at = datetime(2026, 1, 25, 10, 0, tzinfo=UTC)
        project = RegisteredProject(
            path="/Users/dev/my-api",
            name="my-api",
            registered_at=registered_at,
        )

        assert project.path == "/Users/dev/my-api"
        assert project.name == "my-api"
        assert project.registered_at == registered_at

    def test_path_is_string(self) -> None:
        """Test that path field is stored as string."""
        project = RegisteredProject(
            path="/path/to/project",
            name="project",
            registered_at=datetime.now(UTC),
        )

        assert isinstance(project.path, str)
        assert project.path == "/path/to/project"

    def test_registered_at_is_datetime(self) -> None:
        """Test that registered_at field is a datetime."""
        now = datetime.now(UTC)
        project = RegisteredProject(
            path="/path/to/project",
            name="project",
            registered_at=now,
        )

        assert isinstance(project.registered_at, datetime)
        assert project.registered_at == now

    def test_name_can_contain_special_characters(self) -> None:
        """Test that project name can contain hyphens and underscores."""
        project = RegisteredProject(
            path="/path/to/my-awesome_project",
            name="my-awesome_project",
            registered_at=datetime.now(UTC),
        )

        assert project.name == "my-awesome_project"


class TestProjectRegistryModel:
    """Tests for ProjectRegistry container model."""

    def test_empty_projects_list_by_default(self) -> None:
        """Test that ProjectRegistry defaults to empty projects list."""
        registry = ProjectRegistry()

        assert registry.projects == []

    def test_create_registry_with_projects(self) -> None:
        """Test creating ProjectRegistry with projects list."""
        now = datetime.now(UTC)
        projects = [
            RegisteredProject(
                path="/Users/dev/project-a",
                name="project-a",
                registered_at=now,
            ),
            RegisteredProject(
                path="/Users/dev/project-b",
                name="project-b",
                registered_at=now,
            ),
        ]

        registry = ProjectRegistry(projects=projects)

        assert len(registry.projects) == 2
        assert registry.projects[0].name == "project-a"
        assert registry.projects[1].name == "project-b"

    def test_projects_list_is_independent_copy(self) -> None:
        """Test that default projects list is a new list each time."""
        registry1 = ProjectRegistry()
        registry2 = ProjectRegistry()

        registry1.projects.append(
            RegisteredProject(
                path="/path",
                name="test",
                registered_at=datetime.now(UTC),
            )
        )

        # registry2 should not be affected
        assert len(registry2.projects) == 0


class TestRegisteredProjectSerialization:
    """Tests for RegisteredProject JSON/YAML serialization."""

    def test_serialize_to_dict(self) -> None:
        """Test serializing RegisteredProject to dictionary."""
        registered_at = datetime(2026, 1, 25, 10, 0, tzinfo=UTC)
        project = RegisteredProject(
            path="/Users/dev/my-api",
            name="my-api",
            registered_at=registered_at,
        )

        data = project.model_dump()

        assert data["path"] == "/Users/dev/my-api"
        assert data["name"] == "my-api"
        assert data["registered_at"] == registered_at

    def test_deserialize_from_dict(self) -> None:
        """Test deserializing RegisteredProject from dictionary."""
        data = {
            "path": "/Users/dev/my-api",
            "name": "my-api",
            "registered_at": datetime(2026, 1, 25, 10, 0, tzinfo=UTC),
        }

        project = RegisteredProject.model_validate(data)

        assert project.path == "/Users/dev/my-api"
        assert project.name == "my-api"

    def test_json_round_trip(self) -> None:
        """Test JSON serialization round-trip preserves data."""
        original = RegisteredProject(
            path="/Users/dev/my-api",
            name="my-api",
            registered_at=datetime(2026, 1, 25, 10, 0, tzinfo=UTC),
        )

        json_str = original.model_dump_json()
        restored = RegisteredProject.model_validate_json(json_str)

        assert restored.path == original.path
        assert restored.name == original.name
        assert restored.registered_at == original.registered_at


class TestProjectRegistrySerialization:
    """Tests for ProjectRegistry YAML serialization."""

    def test_yaml_serialization(self) -> None:
        """Test that ProjectRegistry can be serialized to YAML."""
        now = datetime(2026, 1, 25, 10, 0, tzinfo=UTC)
        registry = ProjectRegistry(
            projects=[
                RegisteredProject(
                    path="/Users/dev/my-api",
                    name="my-api",
                    registered_at=now,
                ),
                RegisteredProject(
                    path="/Users/dev/frontend",
                    name="frontend-app",
                    registered_at=now,
                ),
            ]
        )

        # Serialize to dict, then to YAML
        data = registry.model_dump(mode="json")
        yaml_str = yaml.safe_dump(data, default_flow_style=False)

        assert "projects:" in yaml_str
        assert "path: /Users/dev/my-api" in yaml_str
        assert "name: my-api" in yaml_str

    def test_yaml_deserialization(self) -> None:
        """Test that ProjectRegistry can be deserialized from YAML."""
        yaml_str = """
projects:
  - path: /Users/dev/my-api
    name: my-api
    registered_at: '2026-01-25T10:00:00+00:00'
  - path: /Users/dev/frontend
    name: frontend-app
    registered_at: '2026-01-25T14:30:00+00:00'
"""
        data = yaml.safe_load(yaml_str)
        registry = ProjectRegistry.model_validate(data)

        assert len(registry.projects) == 2
        assert registry.projects[0].path == "/Users/dev/my-api"
        assert registry.projects[0].name == "my-api"
        assert registry.projects[1].path == "/Users/dev/frontend"
        assert registry.projects[1].name == "frontend-app"

    def test_yaml_round_trip(self) -> None:
        """Test YAML serialization round-trip preserves all data."""
        now = datetime(2026, 1, 25, 10, 0, tzinfo=UTC)
        original = ProjectRegistry(
            projects=[
                RegisteredProject(
                    path="/Users/dev/project-a",
                    name="project-a",
                    registered_at=now,
                ),
            ]
        )

        # Serialize to YAML
        data = original.model_dump(mode="json")
        yaml_str = yaml.safe_dump(data, default_flow_style=False)

        # Deserialize from YAML
        loaded_data = yaml.safe_load(yaml_str)
        restored = ProjectRegistry.model_validate(loaded_data)

        assert len(restored.projects) == len(original.projects)
        assert restored.projects[0].path == original.projects[0].path
        assert restored.projects[0].name == original.projects[0].name

    def test_empty_registry_yaml_serialization(self) -> None:
        """Test that empty registry serializes correctly."""
        registry = ProjectRegistry()

        data = registry.model_dump(mode="json")
        yaml_str = yaml.safe_dump(data, default_flow_style=False)

        assert "projects: []" in yaml_str


class TestModelCopyPattern:
    """Tests for immutable update patterns using model_copy."""

    def test_model_copy_updates_registered_project(self) -> None:
        """Test using model_copy to update RegisteredProject."""
        original = RegisteredProject(
            path="/path/to/project",
            name="old-name",
            registered_at=datetime(2026, 1, 1, tzinfo=UTC),
        )

        new_time = datetime(2026, 1, 25, tzinfo=UTC)
        updated = original.model_copy(
            update={
                "name": "new-name",
                "registered_at": new_time,
            }
        )

        # Original unchanged
        assert original.name == "old-name"
        assert original.registered_at == datetime(2026, 1, 1, tzinfo=UTC)

        # Updated has new values
        assert updated.name == "new-name"
        assert updated.registered_at == new_time
        assert updated.path == original.path  # Unchanged field preserved
