"""Project registry manager for global project tracking.

This module provides the ProjectRegistryManager class for managing the global
project registry at ~/.adw/projects.yaml.

The registry allows users to explicitly manage which projects appear
in cross-project views like the global dashboard.

Key features:
- YAML format for human-readable configuration
- Register/unregister projects
- Discover projects from existing index.jsonl
- Query registered projects by path
"""

import logging
from datetime import UTC, datetime
from pathlib import Path

import yaml

from adw.models.registry import ProjectRegistry, RegisteredProject

logger = logging.getLogger(__name__)

__all__ = ["ProjectRegistryManager"]


class ProjectRegistryManager:
    """Manages the global project registry at ~/.adw/projects.yaml.

    The registry stores projects that have been explicitly registered
    with ADW, enabling cross-project features like:
    - Global run list (adw runs --global)
    - Cross-project statistics
    - TUI dashboard project breakdown

    Attributes:
        registry_path: Path to the projects.yaml file.

    Environment Variables:
        ADW_TEST_REGISTRY_PATH: If set, overrides the default registry path.
            Used during testing to prevent test runs from polluting
            the user's global registry.

    Example:
        >>> from pathlib import Path
        >>> manager = ProjectRegistryManager()
        >>> manager.register(Path("/my/project"), name="My Project")
        >>> projects = manager.get_all()
        >>> manager.unregister(Path("/my/project"))
    """

    def __init__(self, registry_path: Path | None = None) -> None:
        """Initialize the ProjectRegistryManager.

        Args:
            registry_path: Path to the registry file. Defaults to ~/.adw/projects.yaml,
                or the path specified by ADW_TEST_REGISTRY_PATH environment variable.
        """
        import os

        # Allow environment variable to override default path (for testing)
        env_registry_path = os.environ.get("ADW_TEST_REGISTRY_PATH")
        if registry_path is not None:
            self.registry_path = registry_path
        elif env_registry_path:
            self.registry_path = Path(env_registry_path)
        else:
            self.registry_path = Path.home() / ".adw" / "projects.yaml"

    def register(
        self,
        path: Path,
        name: str | None = None,
    ) -> RegisteredProject:
        """Register or update a project in the registry.

        If the project is already registered (by path), its name and
        registered_at timestamp will be updated. Otherwise, a new
        entry is created.

        Args:
            path: Absolute path to the project directory.
            name: Optional display name. Defaults to directory name.

        Returns:
            The registered project entry.

        Example:
            >>> manager.register(Path("/path/to/project"), name="My Project")
        """
        # Load existing registry
        registry = self._load_registry()

        # Resolve and normalize path
        path_str = str(path.resolve())
        # Strip whitespace from name and fallback to directory name if empty
        stripped_name = name.strip() if name else None
        display_name = stripped_name or path.name

        # Check for existing entry
        existing_idx = None
        for i, project in enumerate(registry.projects):
            if project.path == path_str:
                existing_idx = i
                break

        now = datetime.now(UTC)

        if existing_idx is not None:
            # Update existing entry
            updated_project = RegisteredProject(
                path=path_str,
                name=display_name,
                registered_at=now,
            )
            registry.projects[existing_idx] = updated_project
            project = updated_project
        else:
            # Add new entry
            project = RegisteredProject(
                path=path_str,
                name=display_name,
                registered_at=now,
            )
            registry.projects.append(project)

        # Save registry
        self._save_registry(registry)

        return project

    def unregister(self, path: Path) -> bool:
        """Remove a project from the registry.

        Args:
            path: Path to the project directory to unregister.

        Returns:
            True if the project was found and removed, False if not found.

        Example:
            >>> manager.unregister(Path("/path/to/project"))
            True
        """
        registry = self._load_registry()
        path_str = str(path.resolve())

        # Find and remove the project
        original_count = len(registry.projects)
        registry.projects = [p for p in registry.projects if p.path != path_str]

        if len(registry.projects) < original_count:
            self._save_registry(registry)
            return True

        return False

    def get_all(self) -> list[RegisteredProject]:
        """Get all registered projects.

        Returns:
            List of all registered projects, empty list if none.

        Example:
            >>> projects = manager.get_all()
            >>> for p in projects:
            ...     print(f"{p.name}: {p.path}")
        """
        registry = self._load_registry()
        return registry.projects

    def get_by_path(self, path: Path) -> RegisteredProject | None:
        """Find a registered project by its path.

        Args:
            path: Path to the project directory.

        Returns:
            The registered project if found, None otherwise.

        Example:
            >>> project = manager.get_by_path(Path("/path/to/project"))
            >>> if project:
            ...     print(project.name)
        """
        registry = self._load_registry()
        path_str = str(path.resolve())

        for project in registry.projects:
            if project.path == path_str:
                return project

        return None

    def discover_from_index(
        self,
        index_path: Path | None = None,
    ) -> list[RegisteredProject]:
        """Discover unique projects from the global index.

        Scans the index.jsonl file and returns unique projects
        that have ADW runs, regardless of whether they are registered.
        This is useful for auto-discovery of projects.

        Args:
            index_path: Path to index.jsonl. Defaults to ~/.adw/index.jsonl.

        Returns:
            List of discovered projects (not yet registered).

        Example:
            >>> discovered = manager.discover_from_index()
            >>> for p in discovered:
            ...     print(f"Found: {p.name}")
        """
        import json

        if index_path is None:
            index_path = self.registry_path.parent / "index.jsonl"

        if not index_path.exists():
            return []

        # Collect unique projects from index
        seen_paths: dict[str, str] = {}  # path -> name

        try:
            with open(index_path) as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entry = json.loads(line)
                        project_path = entry.get("project_path")
                        project_name = entry.get("project_name")
                        if project_path and project_path not in seen_paths:
                            seen_paths[project_path] = project_name or Path(project_path).name
                    except (json.JSONDecodeError, KeyError):
                        continue  # Skip corrupted entries
        except OSError:
            logger.warning(
                "Failed to read index file",
                extra={"index_path": str(index_path)},
            )
            return []

        # Convert to RegisteredProject entries (with current timestamp)
        now = datetime.now(UTC)
        return [
            RegisteredProject(
                path=path,
                name=name,
                registered_at=now,
            )
            for path, name in seen_paths.items()
        ]

    def _load_registry(self) -> ProjectRegistry:
        """Load the registry from YAML file.

        Returns:
            ProjectRegistry with loaded projects, or empty registry if file
            doesn't exist or is corrupted.
        """
        if not self.registry_path.exists():
            return ProjectRegistry()

        try:
            with open(self.registry_path) as f:
                data = yaml.safe_load(f)

            if data is None:
                return ProjectRegistry()

            return ProjectRegistry.model_validate(data)
        except (yaml.YAMLError, OSError, ValueError) as e:
            # ValueError catches pydantic.ValidationError (which inherits from it)
            # This handles malformed YAML structure (wrong types, missing fields)
            logger.warning(
                "Failed to load registry, returning empty",
                extra={
                    "registry_path": str(self.registry_path),
                    "error": str(e),
                },
            )
            return ProjectRegistry()

    def _save_registry(self, registry: ProjectRegistry) -> None:
        """Save the registry to YAML file.

        Creates parent directories if they don't exist.

        Args:
            registry: The ProjectRegistry to save.
        """
        # Ensure parent directories exist
        self.registry_path.parent.mkdir(parents=True, exist_ok=True)

        # Convert to dict and dump as YAML
        data = registry.model_dump(mode="json")

        with open(self.registry_path, "w") as f:
            yaml.safe_dump(data, f, default_flow_style=False, sort_keys=False)
