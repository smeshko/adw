"""Evidence config loader for CLI commands.

This module provides functionality to load evidence gathering command
configurations from the project's .adw/project.yaml file.
"""

from pathlib import Path

import yaml
from pydantic import ValidationError

from adw.models.evidence import CommandConfig


def load_evidence_commands(project_root: Path) -> list[CommandConfig]:
    """Load evidence command configurations from project config.

    Reads the evidence.commands section from .adw/project.yaml and
    returns a list of validated CommandConfig objects.

    Args:
        project_root: Path to the project root directory

    Returns:
        List of CommandConfig objects, or empty list if none configured

    Note:
        Invalid command configurations are silently skipped with a warning.
        Returns empty list if config file doesn't exist or has no commands.

    Example:
        >>> from pathlib import Path
        >>> commands = load_evidence_commands(Path("/my/project"))
        >>> for cmd in commands:
        ...     print(f"{cmd.name}: {cmd.cmd}")
        version: adw --version
    """
    config_path = project_root / ".adw" / "project.yaml"

    if not config_path.exists():
        return []

    try:
        content = config_path.read_text()
        data = yaml.safe_load(content)
    except (yaml.YAMLError, OSError):
        return []

    if not isinstance(data, dict):
        return []

    evidence = data.get("evidence")
    if not isinstance(evidence, dict):
        return []

    commands_data = evidence.get("commands")
    if not isinstance(commands_data, list):
        return []

    commands: list[CommandConfig] = []
    for cmd_data in commands_data:
        if not isinstance(cmd_data, dict):
            continue

        try:
            command = CommandConfig.model_validate(cmd_data)
            commands.append(command)
        except ValidationError:
            # Skip invalid command configurations
            continue

    return commands
