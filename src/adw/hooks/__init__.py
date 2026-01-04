"""ADW hooks module - shell script execution and git integration.

This module provides utilities for executing pre-hook and post-hook
shell scripts during phase execution, git branch management, commit
automation, and git diff capture for build artifacts.
"""

from adw.hooks.environment import build_hook_environment
from adw.hooks.git_branch import (
    check_uncommitted_changes,
    create_or_switch_branch,
    sanitize_branch_name,
)
from adw.hooks.git_commit import (
    create_commit,
    format_commit_message,
    get_unstaged_modifications,
    has_staged_changes,
    stage_changes,
)
from adw.hooks.git_diff import (
    capture_diff,
    capture_staged_diff,
    count_binary_files,
    get_diff_stats,
    has_commits,
    truncate_diff,
)
from adw.hooks.runner import HookRunner, find_hook
from adw.models.artifacts import DiffStats

__all__: list[str] = [
    "HookRunner",
    "find_hook",
    "build_hook_environment",
    # Git branch functions
    "sanitize_branch_name",
    "check_uncommitted_changes",
    "create_or_switch_branch",
    # Git commit functions
    "stage_changes",
    "has_staged_changes",
    "get_unstaged_modifications",
    "create_commit",
    "format_commit_message",
    # Git diff functions
    "DiffStats",
    "capture_diff",
    "capture_staged_diff",
    "count_binary_files",
    "get_diff_stats",
    "has_commits",
    "truncate_diff",
]
