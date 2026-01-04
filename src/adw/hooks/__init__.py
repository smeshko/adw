"""ADW hooks module - shell script execution and git integration.

This module provides utilities for executing pre-hook and post-hook
shell scripts during phase execution, as well as git diff capture
for build artifacts.
"""

from adw.hooks.environment import build_hook_environment
from adw.hooks.git_diff import (
    DiffStats,
    capture_diff,
    capture_staged_diff,
    get_diff_stats,
    truncate_diff,
)
from adw.hooks.runner import HookRunner, find_hook

__all__: list[str] = [
    "HookRunner",
    "find_hook",
    "build_hook_environment",
    # Git diff functions
    "DiffStats",
    "capture_diff",
    "capture_staged_diff",
    "get_diff_stats",
    "truncate_diff",
]
