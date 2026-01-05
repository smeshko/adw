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


def build_hook_environment(
    context: RunContext,
    phase: str,
    *,
    artifacts_dir: Path | None = None,
    context_file: Path | None = None,
    port_allocation: PortAllocation | None = None,
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

    # Add port allocation variables if provided
    if port_allocation is not None:
        adw_vars["ADW_BACKEND_PORT"] = str(port_allocation.backend_port)
        adw_vars["ADW_FRONTEND_PORT"] = str(port_allocation.frontend_port)
        adw_vars["ADW_SLOT"] = str(port_allocation.slot)

    # Merge ADW variables into environment (ADW vars override any existing)
    env.update(adw_vars)

    return env
