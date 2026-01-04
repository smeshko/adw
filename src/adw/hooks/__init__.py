"""ADW hooks module - shell script execution and git integration.

This module provides utilities for executing pre-hook and post-hook
shell scripts during phase execution, as well as git branch management
for workflow automation.
"""

from adw.hooks.environment import build_hook_environment
from adw.hooks.git_branch import (
    check_uncommitted_changes,
    create_or_switch_branch,
    sanitize_branch_name,
)
from adw.hooks.runner import HookRunner, find_hook

__all__: list[str] = [
    "HookRunner",
    "find_hook",
    "build_hook_environment",
    "sanitize_branch_name",
    "check_uncommitted_changes",
    "create_or_switch_branch",
]
