"""Command resolver for three-tier command resolution.

This module implements the CommandResolver class that resolves commands
from the three-tier hierarchy: project -> user -> bundled.
"""

from importlib.resources import files
from pathlib import Path
from typing import Literal

from adw.exceptions import ConfigError
from adw.models import ResolvedCommand


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

    def resolve(self, command_name: str) -> ResolvedCommand:
        """Resolve a command by name using the three-tier hierarchy.

        Checks for the command in order:
        1. Project tier: {project_root}/.adw/commands/{name}/
        2. User tier: ~/.adw/commands/{name}/
        3. Bundled tier: Package defaults

        Args:
            command_name: The name of the command to resolve (e.g., "plan").

        Returns:
            ResolvedCommand with the resolved path and tier information.

        Raises:
            ConfigError: If the command is not found at any tier (COMMAND_NOT_FOUND)
                        or if the command directory is invalid (INVALID_COMMAND).
        """
        # Try project tier first
        project_path = self.project_root / ".adw" / "commands" / command_name
        if self._is_valid_command_dir(project_path):
            return self._create_resolved_command(command_name, project_path, "project")

        # Try user tier
        user_path = Path.home() / ".adw" / "commands" / command_name
        if self._is_valid_command_dir(user_path):
            return self._create_resolved_command(command_name, user_path, "user")

        # Try bundled tier
        bundled_path = self._get_bundled_command_path(command_name)
        if bundled_path is not None and self._is_valid_command_dir(bundled_path):
            return self._create_resolved_command(command_name, bundled_path, "bundled")

        # Command not found anywhere
        raise ConfigError(
            code="COMMAND_NOT_FOUND",
            message=f"Command '{command_name}' not found",
            suggestion="Check available commands with 'adw list-commands'",
            recoverable=False,
        )

    def _is_valid_command_dir(self, path: Path) -> bool:
        """Check if a path is a valid command directory.

        A valid command directory must:
        - Exist as a directory
        - Contain a prompt.md file

        Args:
            path: The path to check.

        Returns:
            True if the path is a valid command directory.
        """
        if not path.is_dir():
            return False
        return (path / "prompt.md").is_file()

    def _get_bundled_command_path(self, command_name: str) -> Path | None:
        """Get the path to a bundled command.

        Uses importlib.resources to access package resources.

        Args:
            command_name: The name of the command.

        Returns:
            Path to the bundled command directory, or None if not found.
        """
        try:
            # Use importlib.resources.files for Python 3.9+
            defaults_traversable = files("adw") / "defaults" / "commands" / command_name
            # Convert Traversable to Path using str() - works for both
            # installed packages and editable installs
            path = Path(str(defaults_traversable))
            if path.is_dir():
                return path
        except (TypeError, FileNotFoundError):
            pass
        return None

    def _create_resolved_command(
        self,
        name: str,
        path: Path,
        tier: Literal["project", "user", "bundled"],
    ) -> ResolvedCommand:
        """Create a ResolvedCommand from a command directory.

        Detects presence of optional files (schema, hooks).

        Args:
            name: The command name.
            path: The command directory path.
            tier: Which tier the command was resolved from.

        Returns:
            ResolvedCommand with detected optional files.
        """
        has_schema = (path / "schema.json").is_file()
        has_pre_hook = (path / "pre.sh").is_file() or (path / "pre-hook.sh").is_file()
        has_post_hook = (
            (path / "post.sh").is_file() or (path / "post-hook.sh").is_file()
        )

        return ResolvedCommand(
            name=name,
            path=path,
            tier=tier,
            has_schema=has_schema,
            has_pre_hook=has_pre_hook,
            has_post_hook=has_post_hook,
        )
