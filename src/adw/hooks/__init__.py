"""ADW hooks module - shell script execution.

This module provides utilities for executing pre-hook and post-hook
shell scripts during phase execution.
"""

from adw.hooks.environment import build_hook_environment
from adw.hooks.runner import HookRunner, find_hook

__all__: list[str] = [
    "HookRunner",
    "find_hook",
    "build_hook_environment",
]
