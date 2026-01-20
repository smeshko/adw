"""Environment builder for hook execution.

This module provides utilities for building environment variables
that are passed to hook scripts during execution.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING

from adw.models import RunContext

if TYPE_CHECKING:
    from adw.models.worktree import PortAllocation


def _parse_ports_env_file(ports_file: Path) -> dict[str, str]:
    """Parse a .ports.env file into a dictionary.

    Parses shell-style environment variable assignments (VAR=VALUE).
    Ignores comments (lines starting with #) and empty lines.

    Args:
        ports_file: Path to the .ports.env file.

    Returns:
        Dictionary of environment variable names to values.
    """
    if not ports_file.exists():
        return {}

    result: dict[str, str] = {}
    try:
        for line in ports_file.read_text().splitlines():
            line = line.strip()
            # Skip empty lines and comments
            if not line or line.startswith("#"):
                continue
            # Parse VAR=VALUE format
            if "=" in line:
                key, _, value = line.partition("=")
                result[key.strip()] = value.strip()
    except OSError:
        return {}

    return result


def build_hook_environment(
    context: RunContext,
    phase: str,
    *,
    artifacts_dir: Path | None = None,
    context_file: Path | None = None,
    port_allocation: PortAllocation | None = None,
    project_root: Path | None = None,
    ports_file: Path | None = None,
) -> dict[str, str]:
    """Build environment variables for hook script execution.

    Creates a dictionary of environment variables by merging the current
    process environment with ADW-specific variables from the run context.

    Args:
        context: The current run context containing run metadata
        phase: The name of the current phase (e.g., "plan", "build")
        artifacts_dir: Optional path to the artifacts directory
        context_file: Optional path to the context JSON file
        port_allocation: Optional port allocation for the run
        project_root: Optional project root path, used as fallback for
                     ADW_WORKTREE_PATH when context.worktree_path is None
        ports_file: Optional path to .ports.env file (Story 10.5).
                   If provided, its contents are auto-sourced into environment.

    Returns:
        A dictionary of environment variables (all string keys and values)

    Example:
        >>> env = build_hook_environment(context, "plan")
        >>> env["ADW_RUN_ID"]
        '01KDSG2VDHNK0W4HSCZWJZXWSQ'
        >>> env["ADW_PHASE"]
        'plan'
    """
    # Start with a copy of the current environment
    env = os.environ.copy()

    # Add ADW-specific environment variables
    adw_vars: dict[str, str] = {
        "ADW_RUN_ID": context.run_id,
        "ADW_PHASE": phase,
        "ADW_FEATURE": context.feature_description,
    }

    # Add optional path variables if provided
    if artifacts_dir is not None:
        adw_vars["ADW_ARTIFACTS_DIR"] = str(artifacts_dir)

    if context_file is not None:
        adw_vars["ADW_CONTEXT_FILE"] = str(context_file)

    # Add worktree path variable (Story 10.5)
    # Priority: context.worktree_path > project_root > (not set)
    if context.worktree_path is not None:
        adw_vars["ADW_WORKTREE_PATH"] = str(context.worktree_path)
    elif project_root is not None:
        adw_vars["ADW_WORKTREE_PATH"] = str(project_root)
    # If both are None, ADW_WORKTREE_PATH is not set (backward compatible)

    # Add branch name variable (ISS-025)
    # This allows hooks to know which git branch is being used
    if context.branch_name is not None:
        adw_vars["ADW_BRANCH_NAME"] = context.branch_name

    # Add PR URL variable (ISS-031)
    # This allows ship phase hooks to know the PR URL for merge operations
    if context.pr_url is not None:
        adw_vars["ADW_PR_URL"] = context.pr_url

    # Add port allocation variables if provided
    if port_allocation is not None:
        adw_vars["ADW_BACKEND_PORT"] = str(port_allocation.backend_port)
        adw_vars["ADW_FRONTEND_PORT"] = str(port_allocation.frontend_port)
        adw_vars["ADW_SLOT"] = str(port_allocation.slot)

    # Story 10.5: Auto-source .ports.env file if provided
    # Also try to auto-detect from worktree_path if not explicitly provided
    effective_ports_file = ports_file
    if effective_ports_file is None and context.worktree_path is not None:
        candidate = context.worktree_path / ".ports.env"
        if candidate.exists():
            effective_ports_file = candidate

    if effective_ports_file is not None:
        adw_vars["ADW_PORTS_FILE"] = str(effective_ports_file)
        # Auto-source the ports file variables (Story 10.5)
        # These provide BACKEND_PORT, FRONTEND_PORT directly to hooks
        ports_vars = _parse_ports_env_file(effective_ports_file)
        adw_vars.update(ports_vars)

    # Merge ADW variables into environment (ADW vars override any existing)
    env.update(adw_vars)

    return env
