"""Phase Extensions System.

This module provides the extension infrastructure for phase-specific behavior.
Extensions allow phases to define custom lifecycle hooks without modifying
core orchestration files.

Exports:
    PhaseExtension: Protocol for phase extensions
    ExtensionRegistry: Registry for managing extensions
    BuildExtension: Git diff capture for build phase
    DocumentExtension: PR creation for document phase
    ShipExtension: Skip logic for ship phase
    create_default_registry: Factory for creating registry with built-in extensions

Example:
    >>> from adw.core.extensions import ExtensionRegistry, PhaseExtension
    >>>
    >>> registry = ExtensionRegistry()
    >>> registry.register(my_extension)

    >>> # Or use factory for built-in extensions
    >>> registry = create_default_registry(git_config, runs_dir)
"""

from pathlib import Path

from adw.core.extensions.base import PhaseExtension
from adw.core.extensions.build import BuildExtension
from adw.core.extensions.document import DocumentExtension
from adw.core.extensions.registry import ExtensionRegistry
from adw.core.extensions.ship import ShipExtension
from adw.models import GitConfig


def create_default_registry(
    git_config: GitConfig,
    runs_dir: Path,
    project_root: Path | None = None,
) -> ExtensionRegistry:
    """Create registry with all built-in extensions.

    Factory function that creates an ExtensionRegistry pre-populated
    with the standard phase extensions:
    - BuildExtension: Git diff capture
    - DocumentExtension: PR description and auto-PR creation
    - ShipExtension: Skip logic based on PR state, hook env from config

    Args:
        git_config: Git configuration with auto_create_pr setting.
        runs_dir: Path to .adw/runs directory.
        project_root: Path to project root for loading phase configs.

    Returns:
        ExtensionRegistry with all built-in extensions registered.

    Example:
        >>> registry = create_default_registry(
        ...     git_config=GitConfig(auto_create_pr=True),
        ...     runs_dir=Path(".adw/runs"),
        ...     project_root=Path("/project"),
        ... )
    """
    registry = ExtensionRegistry()
    registry.register(BuildExtension())
    registry.register(DocumentExtension(git_config, runs_dir))
    registry.register(ShipExtension(project_root=project_root))
    return registry


__all__ = [
    "BuildExtension",
    "DocumentExtension",
    "ExtensionRegistry",
    "PhaseExtension",
    "ShipExtension",
    "create_default_registry",
]
