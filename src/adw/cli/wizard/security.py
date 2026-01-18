"""Security configuration step for the wizard.

This module handles the security configuration step where users can
customize security settings including dangerous operation permissions
and blocked patterns for commands and environment files.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt

if TYPE_CHECKING:
    from adw.models.wizard import WizardState

# Built-in blocked command patterns (always active, not user-configurable)
BUILTIN_BLOCKED_COMMANDS: list[str] = [
    r"rm\s+-rf\s+/",
    r"sudo\s+rm",
    r":\(\)\s*\{\s*:\|\:&\s*\}",  # Fork bomb
]

# Built-in blocked env file patterns (always active, not user-configurable)
BUILTIN_BLOCKED_ENV_FILES: list[str] = [
    ".env",
    ".env.local",
    "*.pem",
    "*.key",
]


def validate_regex(pattern: str) -> tuple[bool, str]:
    """Validate that a regex pattern is syntactically correct.

    Validates that the input is a non-empty, valid regular expression
    that can be compiled without errors.

    Args:
        pattern: The regex pattern to validate.

    Returns:
        A tuple of (is_valid, result) where result is either the original
        pattern (if valid) or an error message string (if invalid).
    """
    if not pattern.strip():
        return (False, "Pattern cannot be empty")

    try:
        re.compile(pattern)
        return (True, pattern)
    except re.error as e:
        return (False, f"Invalid regex: {e}")


class SecurityStepHandler:
    """Handler for the security configuration wizard step.

    This step:
    - Prompts user if they want to configure custom security settings
    - If yes, prompts for dangerous operations permission
    - Shows warning and requires confirmation for dangerous operations
    - Allows adding custom blocked command patterns (regex)
    - Allows adding custom blocked env file patterns (glob-style)
    """

    def execute(self, state: WizardState, console: Console) -> dict[str, Any]:
        """Execute the security configuration step.

        Args:
            state: Current wizard state.
            console: Console for output.

        Returns:
            Configuration collected from this step containing:
            - security_custom: Whether user customized security
            - security_allow_dangerous: Whether dangerous operations are allowed
            - security_blocked_commands: List of additional blocked command patterns
            - security_blocked_env_files: List of additional blocked env file patterns
        """
        return run_security_step(state, console)


def run_security_step(
    state: WizardState,
    console: Console,
) -> dict[str, Any]:
    """Execute the security configuration step.

    This is the main entry point for the security step, implementing
    the full interactive flow for security configuration.

    Args:
        state: Current wizard state.
        console: Console for output.

    Returns:
        Configuration dict containing security_custom, security_allow_dangerous,
        security_blocked_commands, and security_blocked_env_files values.
    """
    console.print()
    console.print(
        "[dim]Security settings control what operations ADW is allowed to perform.[/]"
    )
    console.print(
        "[dim]Default: Dangerous operations blocked, standard protections active.[/]"
    )
    console.print()

    # Ask if user wants to configure security settings
    configure = Confirm.ask(
        "Configure security settings?",
        default=False,
        console=console,
    )

    if not configure:
        # Use safe defaults
        return {
            "security_custom": False,
            "security_allow_dangerous": False,
            "security_blocked_commands": [],
            "security_blocked_env_files": [],
        }

    # Interactive configuration
    console.print()

    # Handle dangerous operations
    allow_dangerous = _prompt_dangerous_operations(console)

    # Handle blocked command patterns
    blocked_commands = _prompt_blocked_commands(console)

    # Handle blocked env file patterns
    blocked_env_files = _prompt_blocked_env_files(console)

    return {
        "security_custom": True,
        "security_allow_dangerous": allow_dangerous,
        "security_blocked_commands": blocked_commands,
        "security_blocked_env_files": blocked_env_files,
    }


def _prompt_dangerous_operations(console: Console) -> bool:
    """Prompt for dangerous operations permission.

    Args:
        console: Console for output.

    Returns:
        True if dangerous operations are allowed, False otherwise.
    """
    allow_dangerous = Confirm.ask(
        "Allow dangerous operations (warns instead of blocking)?",
        default=False,
        console=console,
    )

    if not allow_dangerous:
        return False

    # Show warning panel
    console.print()
    console.print(
        Panel(
            "[yellow bold]Warning: Reduced Safety Mode[/]\n\n"
            "Enabling this option means:\n"
            "  - Dangerous commands will show warnings instead of blocking\n"
            "  - You'll be prompted to confirm risky operations\n"
            "  - LLM may execute destructive commands with your approval\n\n"
            "[dim]Only enable if you understand the risks.[/]",
            title="Security Warning",
            border_style="yellow",
        )
    )

    # Require explicit confirmation
    really_sure = Confirm.ask(
        "Are you sure you want to enable dangerous operations?",
        default=False,
        console=console,
    )

    return really_sure


def _prompt_blocked_commands(console: Console) -> list[str]:
    """Prompt for additional blocked command patterns.

    Args:
        console: Console for output.

    Returns:
        List of user-provided blocked command regex patterns.
    """
    console.print()
    add_patterns = Confirm.ask(
        "Add blocked command patterns?",
        default=False,
        console=console,
    )

    if not add_patterns:
        return []

    console.print()
    console.print("[dim]Enter regex patterns for commands to block.[/]")
    console.print("[dim]Examples: rm\\s+-rf, sudo\\s+.*, npm\\s+publish[/]")
    console.print("[dim]Enter empty line to finish.[/]")
    console.print()

    patterns: list[str] = []

    while True:
        pattern = Prompt.ask(
            "Regex pattern (empty to finish)",
            default="",
            console=console,
        )

        if not pattern:
            break

        is_valid, result = validate_regex(pattern)
        if is_valid:
            patterns.append(pattern)
            console.print(f"[green]Added: {pattern}[/]")
        else:
            console.print(f"[red]{result}. Please try again.[/]")

    return patterns


def _prompt_blocked_env_files(console: Console) -> list[str]:
    """Prompt for additional blocked env file patterns.

    Args:
        console: Console for output.

    Returns:
        List of user-provided blocked env file patterns (glob-style).
    """
    console.print()

    # Show what's always blocked
    console.print("[dim]These file patterns are always blocked:[/]")
    for pattern in BUILTIN_BLOCKED_ENV_FILES:
        console.print(f"[dim]  - {pattern}[/]")
    console.print()

    add_patterns = Confirm.ask(
        "Add blocked env file patterns?",
        default=False,
        console=console,
    )

    if not add_patterns:
        return []

    console.print()
    console.print("[dim]Enter file patterns (glob-style) to block.[/]")
    console.print("[dim]Examples: .secrets, config/*.json, **/credentials.*[/]")
    console.print("[dim]Enter empty line to finish.[/]")
    console.print()

    patterns: list[str] = []

    while True:
        pattern = Prompt.ask(
            "File pattern (empty to finish)",
            default="",
            console=console,
        )

        if not pattern:
            break

        # No validation needed for glob patterns
        patterns.append(pattern)
        console.print(f"[green]Added: {pattern}[/]")

    return patterns
