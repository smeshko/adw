"""Command resolver for three-tier command resolution.

This module implements the CommandResolver class that resolves commands
from the three-tier hierarchy: project -> user -> bundled.
"""

from pathlib import Path


class CommandResolver:
    """Resolves commands from the three-tier hierarchy.

    The resolver checks for commands in the following order:
    1. Project level: .adw/commands/{name}/
    2. User level: ~/.adw/commands/{name}/
    3. Bundled level: Package defaults

    Example:
        >>> resolver = CommandResolver(project_root=Path("."))
        >>> command = resolver.resolve("plan")
        >>> print(command.tier)
        "bundled"
    """

    def __init__(self, project_root: Path | None = None) -> None:
        """Initialize the CommandResolver.

        Args:
            project_root: The project root directory. If None, uses current directory.
        """
        self.project_root = project_root or Path.cwd()
