"""Environment builder for hook execution.

This module provides utilities for building environment variables
that are passed to hook scripts during execution.
"""

from __future__ import annotations

import os
from pathlib import Path

from adw.models import RunContext


def build_hook_environment(
    context: RunContext,
    phase: str,
    *,
    artifacts_dir: Path | None = None,
    context_file: Path | None = None,
    project_root: Path | None = None,
) -> dict[str, str]:
    """Build environment variables for hook script execution.

    Creates a dictionary of environment variables by merging the current
    process environment with ADW-specific variables from the run context.

    Args:
        context: The current run context containing run metadata
        phase: The name of the current phase (e.g., "plan", "build")
        artifacts_dir: Optional path to the artifacts directory
        context_file: Optional path to the context JSON file
        project_root: Optional project root path, used as fallback for
                     ADW_WORKTREE_PATH when context.worktree_path is None

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

    # Add worktree path variable
    # Priority: context.worktree_path > project_root > (not set)
    if context.worktree_path is not None:
        adw_vars["ADW_WORKTREE_PATH"] = str(context.worktree_path)
    elif project_root is not None:
        adw_vars["ADW_WORKTREE_PATH"] = str(project_root)
    # If both are None, ADW_WORKTREE_PATH is not set (backward compatible)

    # Add branch name variable
    # This allows hooks to know which git branch is being used
    if context.branch_name is not None:
        adw_vars["ADW_BRANCH_NAME"] = context.branch_name

    # Add PR URL variable
    # This allows ship phase hooks to know the PR URL for merge operations
    if context.pr_url is not None:
        adw_vars["ADW_PR_URL"] = context.pr_url

    # Merge ADW variables into environment (ADW vars override any existing)
    env.update(adw_vars)

    return env
