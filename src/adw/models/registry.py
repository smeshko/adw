"""Project registry models for global project tracking.

This module contains the models for tracking registered projects
in the global registry at ~/.adw/projects.yaml.

The registry allows users to explicitly manage which projects appear
in cross-project views like the global dashboard.
"""

from datetime import datetime

from pydantic import BaseModel, Field


class RegisteredProject(BaseModel):
    """A project registered in the global registry.

    Each entry represents a project that the user has explicitly registered
    with ADW for cross-project tracking and dashboard visibility.

    Attributes:
        path: Absolute path to the project directory.
        name: Display name for the project (defaults to directory name).
        registered_at: When the project was registered (UTC timestamp).

    Example:
        >>> from datetime import datetime, UTC
        >>> project = RegisteredProject(
        ...     path="/Users/dev/my-api",
        ...     name="my-api",
        ...     registered_at=datetime.now(UTC),
        ... )
        >>> # Serialize to dict for YAML storage
        >>> data = project.model_dump(mode="json")
    """

    path: str = Field(..., description="Absolute path to project directory")
    name: str = Field(..., description="Display name for the project")
    registered_at: datetime = Field(
        ..., description="When project was registered (UTC)"
    )

    model_config = {
        "frozen": False,  # Allow mutation for development, use model_copy
        "validate_assignment": True,  # Validate on attribute assignment
        "json_schema_extra": {
            "example": {
                "path": "/Users/dev/my-api",
                "name": "my-api",
                "registered_at": "2026-01-25T10:00:00Z",
            }
        },
    }


class ProjectRegistry(BaseModel):
    """Global project registry stored at ~/.adw/projects.yaml.

    Contains the list of all projects that have been explicitly registered
    with ADW. This registry is used by cross-project features like:
    - Global run list (adw runs --global)
    - Cross-project statistics
    - TUI dashboard project breakdown

    Attributes:
        projects: List of registered projects.

    Example:
        >>> from datetime import datetime, UTC
        >>> from adw.models.registry import ProjectRegistry, RegisteredProject
        >>> registry = ProjectRegistry(
        ...     projects=[
        ...         RegisteredProject(
        ...             path="/Users/dev/my-api",
        ...             name="my-api",
        ...             registered_at=datetime.now(UTC),
        ...         ),
        ...     ]
        ... )
        >>> # Serialize to YAML
        >>> import yaml
        >>> yaml_str = yaml.safe_dump(registry.model_dump(mode="json"))
    """

    projects: list[RegisteredProject] = Field(
        default_factory=list, description="List of registered projects"
    )

    model_config = {
        "frozen": False,
        "validate_assignment": True,
        "json_schema_extra": {
            "example": {
                "projects": [
                    {
                        "path": "/Users/dev/my-api",
                        "name": "my-api",
                        "registered_at": "2026-01-25T10:00:00Z",
                    },
                    {
                        "path": "/Users/dev/frontend",
                        "name": "frontend-app",
                        "registered_at": "2026-01-25T14:30:00Z",
                    },
                ]
            }
        },
    }
