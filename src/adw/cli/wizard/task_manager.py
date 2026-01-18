"""Task manager configuration step for the wizard.

This module handles the task manager integration step of the wizard where users
configure integration with external task management systems like Linear.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

from rich.console import Console
from rich.prompt import Confirm, Prompt

if TYPE_CHECKING:
    from adw.models.wizard import WizardState

# Team key validation pattern: 2-10 uppercase letters
TEAM_KEY_PATTERN = re.compile(r"^[A-Z]{2,10}$")

# Default state mappings for ADW phases to Linear statuses
# NOTE: These must match the defaults in TaskManagerConfig (src/adw/models/config.py)
DEFAULT_STATE_MAPPINGS: dict[str, str] = {
    "plan": "In Progress",
    "build": "In Progress",
    "validate": "In Review",
    "document": "In Review",
    "failed": "In Progress",
}

# Default PR title format
DEFAULT_PR_TITLE_FORMAT = "{task_id}: {description}"

# Default label prefix
DEFAULT_LABEL_PREFIX = "adw:"


def validate_team_key(key: str) -> tuple[bool, str]:
    """Validate Linear team key format.

    Team keys must be 2-10 uppercase letters (e.g., 'RULE', 'ENG', 'ADW').
    The input is automatically converted to uppercase before validation.

    Args:
        key: The team key to validate.

    Returns:
        A tuple of (is_valid, result) where:
        - If valid: (True, normalized_key)
        - If invalid: (False, error_message)
    """
    key = key.strip().upper()

    if not key:
        return False, "Team key cannot be empty"

    if not TEAM_KEY_PATTERN.match(key):
        return False, "Team key must be 2-10 uppercase letters (e.g., 'RULE', 'ENG')"

    return True, key


class TaskManagerStepHandler:
    """Handler for the task manager configuration wizard step.

    This step:
    - Prompts to enable/disable task manager integration
    - If enabled, prompts for:
      - Task manager type (Linear for MVP)
      - Team key with validation
      - Comment sync options
      - PR title format
      - Label management
      - Context options
      - State mapping configuration
    """

    def execute(self, state: WizardState, console: Console) -> dict[str, Any]:
        """Execute the task manager configuration step.

        Args:
            state: Current wizard state.
            console: Console for output.

        Returns:
            Configuration collected from this step.
        """
        return run_task_manager_step(state, console)


def run_task_manager_step(
    state: WizardState,
    console: Console,
) -> dict[str, Any]:
    """Execute the task manager configuration step.

    This is the main entry point for the task manager step, implementing
    the full interactive flow for task manager configuration.

    Args:
        state: Current wizard state.
        console: Console for output.

    Returns:
        Configuration dict containing all task manager settings.
    """
    # Step 1: Ask if user wants to enable task manager integration
    console.print()
    enabled = Confirm.ask(
        "Set up task manager integration?",
        default=False,
        console=console,
    )

    if not enabled:
        return _disabled_config()

    # Task manager is enabled - collect full configuration
    # Step 2: Select task manager type (Linear only for MVP)
    task_manager_type = _prompt_task_manager_type(console)

    # Step 3: Get team key with validation
    team_key = _prompt_team_key(console)

    # Step 4: Comment sync options
    sync_comments, comment_failures_only = _prompt_comment_options(console)

    # Step 5: PR title format
    pr_title_format = _prompt_pr_title_format(console)

    # Step 6: Label management
    labels_enabled, label_prefix = _prompt_label_options(console)

    # Step 7: Auto-close option
    auto_close = _prompt_auto_close(console)

    # Step 8: Context options
    include_labels, include_parent = _prompt_context_options(console)

    # Step 9: State mapping configuration
    state_mapping = _prompt_state_mapping(console)

    return {
        "enabled": True,
        "type": task_manager_type,
        "team_key": team_key,
        "sync_comments": sync_comments,
        "comment_on_failure_only": comment_failures_only,
        "pr_title_format": pr_title_format,
        "labels_enabled": labels_enabled,
        "label_prefix": label_prefix,
        "auto_close": auto_close,
        "include_labels": include_labels,
        "include_parent": include_parent,
        "state_mapping": state_mapping,
    }


def _disabled_config() -> dict[str, Any]:
    """Return configuration for disabled task manager.

    Returns:
        Configuration dict with type set to 'none'.
    """
    return {
        "enabled": False,
        "type": "none",
        "team_key": None,
        "sync_comments": False,
        "comment_on_failure_only": False,
        "pr_title_format": DEFAULT_PR_TITLE_FORMAT,
        "labels_enabled": True,
        "label_prefix": DEFAULT_LABEL_PREFIX,
        "auto_close": False,
        "include_labels": True,
        "include_parent": True,
        "state_mapping": None,
    }


def _prompt_task_manager_type(console: Console) -> str:
    """Prompt for task manager type selection.

    Currently only Linear is supported for MVP.

    Args:
        console: Console for output.

    Returns:
        Selected task manager type.
    """
    console.print()
    console.print("[dim]Currently supported: Linear[/]")
    task_manager_type = Prompt.ask(
        "Task manager",
        choices=["linear"],
        default="linear",
        console=console,
    )
    return task_manager_type


def _prompt_team_key(console: Console) -> str:
    """Prompt for team key with validation.

    Keeps prompting until a valid team key is entered.

    Args:
        console: Console for output.

    Returns:
        Validated team key (uppercase).
    """
    console.print()
    while True:
        key = Prompt.ask(
            "Team key (e.g., 'RULE' for RULE-123)",
            console=console,
        )
        is_valid, result = validate_team_key(key)
        if is_valid:
            return result
        console.print(f"[yellow]{result}[/]")


def _prompt_comment_options(console: Console) -> tuple[bool, bool]:
    """Prompt for comment sync options.

    Args:
        console: Console for output.

    Returns:
        Tuple of (sync_comments, comment_failures_only).
    """
    console.print()
    sync_comments = Confirm.ask(
        "Sync comments on status changes?",
        default=False,
        console=console,
    )

    comment_failures_only = False
    if sync_comments:
        comment_failures_only = Confirm.ask(
            "Comment on failures only?",
            default=False,
            console=console,
        )

    return sync_comments, comment_failures_only


def _prompt_pr_title_format(console: Console) -> str:
    """Prompt for PR title format.

    Args:
        console: Console for output.

    Returns:
        PR title format string.
    """
    console.print()
    pr_title = Prompt.ask(
        "PR title format",
        default=DEFAULT_PR_TITLE_FORMAT,
        console=console,
    )
    return pr_title.strip() or DEFAULT_PR_TITLE_FORMAT


def _prompt_label_options(console: Console) -> tuple[bool, str | None]:
    """Prompt for label management options.

    Args:
        console: Console for output.

    Returns:
        Tuple of (labels_enabled, label_prefix).
    """
    console.print()
    labels_enabled = Confirm.ask(
        "Enable label management?",
        default=True,
        console=console,
    )

    label_prefix: str | None = None
    if labels_enabled:
        label_prefix = Prompt.ask(
            "Label prefix",
            default=DEFAULT_LABEL_PREFIX,
            console=console,
        )
        label_prefix = label_prefix.strip() or DEFAULT_LABEL_PREFIX

    return labels_enabled, label_prefix


def _prompt_auto_close(console: Console) -> bool:
    """Prompt for auto-close option.

    Args:
        console: Console for output.

    Returns:
        Whether to auto-close tasks when PR is merged.
    """
    console.print()
    return Confirm.ask(
        "Auto-close task when PR merged?",
        default=False,
        console=console,
    )


def _prompt_context_options(console: Console) -> tuple[bool, bool]:
    """Prompt for context inclusion options.

    Args:
        console: Console for output.

    Returns:
        Tuple of (include_labels, include_parent).
    """
    console.print()
    include_labels = Confirm.ask(
        "Include task labels in context?",
        default=True,
        console=console,
    )

    include_parent = Confirm.ask(
        "Include parent task info?",
        default=True,
        console=console,
    )

    return include_labels, include_parent


def _prompt_state_mapping(console: Console) -> dict[str, str] | None:
    """Prompt for state mapping configuration.

    Args:
        console: Console for output.

    Returns:
        Custom state mapping dict or None if using defaults.
    """
    console.print()
    configure_mapping = Confirm.ask(
        "Configure state mapping?",
        default=False,
        console=console,
    )

    if not configure_mapping:
        return None

    # Show what default mappings would be and allow override
    console.print()
    console.print("[dim]Configure phase → Linear state mappings:[/]")

    state_mapping: dict[str, str] = {}
    for phase, default_state in DEFAULT_STATE_MAPPINGS.items():
        state = Prompt.ask(
            f"  {phase}",
            default=default_state,
            console=console,
        )
        state_mapping[phase] = state.strip() or default_state

    return state_mapping
