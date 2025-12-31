"""Command-related Pydantic models.

This module defines models for command resolution and representation.
"""

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict


class ResolvedCommand(BaseModel):
    """A resolved command from the three-tier hierarchy.

    Represents a command that has been located in one of:
    - Project level: .adw/commands/{name}/
    - User level: ~/.adw/commands/{name}/
    - Bundled level: Package defaults

    Attributes:
        name: The command name (e.g., "plan", "build").
        path: The resolved directory path containing command files.
        tier: Which tier the command was resolved from.
        has_schema: Whether schema.json exists in the command directory.
        has_pre_hook: Whether pre.sh or pre-hook.sh exists.
        has_post_hook: Whether post.sh or post-hook.sh exists.

    Example:
        >>> cmd = ResolvedCommand(
        ...     name="plan",
        ...     path=Path(".adw/commands/plan"),
        ...     tier="project",
        ...     has_schema=True,
        ... )
        >>> print(cmd.tier)
        "project"
    """

    model_config = ConfigDict(frozen=True)

    name: str
    path: Path
    tier: Literal["project", "user", "bundled"]
    has_schema: bool = False
    has_pre_hook: bool = False
    has_post_hook: bool = False
