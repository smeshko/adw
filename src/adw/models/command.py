"""Command-related Pydantic models.

This module defines models for command resolution and representation.
"""

from pathlib import Path
from typing import Any, Literal

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


class LoadedCommand(BaseModel):
    """A fully loaded command ready for execution.

    Represents a command that has been resolved and loaded, including
    the rendered prompt content and optional schema.

    Attributes:
        name: The command name (e.g., "plan", "build").
        resolved: The ResolvedCommand with path and tier information.
        prompt_content: The fully rendered prompt content.
        output_schema: Optional JSON Schema for output validation.
        has_pre_hook: Whether this command has a pre-execution hook.
        has_post_hook: Whether this command has a post-execution hook.

    Example:
        >>> loaded = LoadedCommand(
        ...     name="plan",
        ...     resolved=resolved_cmd,
        ...     prompt_content="Create a plan for...",
        ...     output_schema={"type": "object"},
        ... )
        >>> print(loaded.prompt_content)
        "Create a plan for..."
    """

    model_config = ConfigDict(frozen=True)

    name: str
    resolved: ResolvedCommand
    prompt_content: str
    output_schema: dict[str, Any] | None = None
    has_pre_hook: bool = False
    has_post_hook: bool = False
