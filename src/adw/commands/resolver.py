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

    def _find_hook_path(
        self, command_dir: Path, hook_type: str
    ) -> Path | None:
        """Find a hook script in the command directory.

        Searches for hook scripts with various naming patterns:
        - {hook_type}.sh (e.g., pre.sh, post.sh)
        - {hook_type}-hook.sh (e.g., pre-hook.sh, post-hook.sh)
        - {hook_type}-hook (e.g., pre-hook, post-hook)

        Args:
            command_dir: Directory to search for hooks.
            hook_type: Type of hook to find ("pre" or "post").

        Returns:
            Path to the hook script if found, None otherwise.
        """
        patterns = [
            f"{hook_type}.sh",
            f"{hook_type}-hook.sh",
            f"{hook_type}-hook",
        ]
        for pattern in patterns:
            hook_path = command_dir / pattern
            if hook_path.is_file():
                return hook_path
        return None

    def _create_resolved_command(
        self,
        name: str,
        path: Path,
        tier: Literal["project", "user", "bundled"],
    ) -> ResolvedCommand:
        """Create a ResolvedCommand from a command directory.

        Detects presence of optional files (schema, hooks, config).

        Args:
            name: The command name.
            path: The command directory path.
            tier: Which tier the command was resolved from.

        Returns:
            ResolvedCommand with detected optional files.
        """
        has_schema = (path / "schema.json").is_file()
        pre_hook_path = self._find_hook_path(path, "pre")
        post_hook_path = self._find_hook_path(path, "post")
        has_config = (path / "config.yaml").is_file()

        return ResolvedCommand(
            name=name,
            path=path,
            tier=tier,
            has_schema=has_schema,
            pre_hook_path=pre_hook_path,
            post_hook_path=post_hook_path,
            has_config=has_config,
        )
