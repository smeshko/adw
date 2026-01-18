"""Phase customization step for the wizard.

This module handles the phases configuration step where users can customize
individual phase settings including timeouts, hooks, and inputs.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from rich.console import Console
from rich.prompt import Confirm, Prompt
from rich.rule import Rule

if TYPE_CHECKING:
    from adw.models.wizard import WizardState


# Available phases for customization
AVAILABLE_PHASES: list[str] = ["plan", "build", "validate", "document"]

# Default timeouts by phase (in seconds)
DEFAULT_TIMEOUTS: dict[str, int] = {
    "plan": 300,  # 5 minutes
    "build": 600,  # 10 minutes
    "validate": 900,  # 15 minutes
    "document": 300,  # 5 minutes
}

# Triage modes for validate phase
TRIAGE_MODES: list[str] = ["auto", "manual", "hybrid"]

# Review focus areas for validate phase
REVIEW_FOCUS_AREAS: list[str] = ["security", "error_handling", "edge_cases"]


class PhasesStepHandler:
    """Handler for the phases configuration wizard step.

    This step:
    - Prompts if user wants to customize phase settings
    - If yes, allows multi-select of phases to customize
    - For each selected phase, prompts for:
      - Enabled/disabled
      - Timeout override
      - Pre-hook script path
      - Post-hook script path
      - Input files (key=path pairs)
    - For validate phase, additional prompts for code review settings
    """

    def execute(self, state: WizardState, console: Console) -> dict[str, Any]:
        """Execute the phases configuration step.

        Args:
            state: Current wizard state.
            console: Console for output.

        Returns:
            Configuration collected from this step containing:
            - customized: Whether any customization was done
            - phases: Dict of phase configurations
        """
        return run_phases_step(state, console)


def run_phases_step(
    state: WizardState,
    console: Console,
) -> dict[str, Any]:
    """Execute the phases configuration step.

    This is the main entry point for the phases step, implementing
    the full interactive flow for phase customization.

    Args:
        state: Current wizard state.
        console: Console for output.

    Returns:
        Configuration dict containing customized flag and phase configs.
    """
    # Step 1: Ask if user wants to customize phases
    customize = Confirm.ask(
        "Customize phase settings?",
        default=False,
        console=console,
    )

    if not customize:
        return {
            "customized": False,
            "phases": {},
        }

    # Step 2: Multi-select which phases to customize
    selected_phases = _prompt_phase_selection(console)

    if not selected_phases:
        return {
            "customized": False,
            "phases": {},
        }

    # Step 3: Configure each selected phase
    phase_configs: dict[str, dict[str, Any]] = {}

    for phase in selected_phases:
        config = _configure_phase(phase, console)
        phase_configs[phase] = config

    return {
        "customized": True,
        "phases": phase_configs,
    }


def _prompt_phase_selection(console: Console) -> list[str]:
    """Prompt user to select which phases to customize.

    Args:
        console: Console for output.

    Returns:
        List of selected phase names.
    """
    console.print()
    console.print("[dim]Select phases to customize (press Enter for each):[/]")

    selected: list[str] = []

    for phase in AVAILABLE_PHASES:
        if Confirm.ask(
            f"Customize [cyan]{phase}[/] phase?",
            default=False,
            console=console,
        ):
            selected.append(phase)

    return selected


def _configure_phase(phase: str, console: Console) -> dict[str, Any]:
    """Configure a single phase.

    Args:
        phase: The phase name to configure.
        console: Console for output.

    Returns:
        Configuration dict for the phase.
    """
    console.print()
    console.print(Rule(f"[bold cyan]{phase.upper()}[/] Phase", style="cyan"))

    # Base configuration
    enabled = Confirm.ask("Enabled?", default=True, console=console)

    default_timeout = DEFAULT_TIMEOUTS.get(phase, 300)
    timeout_str = Prompt.ask(
        "Timeout (seconds)",
        default=str(default_timeout),
        console=console,
    )
    timeout = _parse_int(timeout_str, default_timeout)

    pre_hook = (
        Prompt.ask(
            "Pre-hook script path",
            default="",
            console=console,
        ).strip()
        or None
    )

    post_hook = (
        Prompt.ask(
            "Post-hook script path",
            default="",
            console=console,
        ).strip()
        or None
    )

    # Input files
    input_files = _prompt_input_files(console)

    config: dict[str, Any] = {
        "enabled": enabled,
        "timeout_seconds": timeout,
        "pre_hook": pre_hook,
        "post_hook": post_hook,
        "input_files": input_files if input_files else None,
    }

    # Validate phase special options
    if phase == "validate":
        validate_config = _configure_validate_phase(console)
        config.update(validate_config)

    return config


def _configure_validate_phase(console: Console) -> dict[str, Any]:
    """Configure validate phase special options.

    Args:
        console: Console for output.

    Returns:
        Validate-specific configuration dict.
    """
    console.print()
    console.print("[dim]Validation phase options:[/]")

    code_review = Confirm.ask("Enable code review?", default=True, console=console)
    tests = Confirm.ask("Enable tests?", default=True, console=console)

    test_timeout_str = Prompt.ask(
        "Test timeout (seconds)",
        default="300",
        console=console,
    )
    test_timeout = _parse_int(test_timeout_str, 300)

    max_iterations_str = Prompt.ask(
        "Max validation iterations",
        default="5",
        console=console,
    )
    max_iterations = _parse_int(max_iterations_str, 5)

    triage_mode = Prompt.ask(
        "Triage mode",
        choices=TRIAGE_MODES,
        default="auto",
        console=console,
    )

    review_focus = _prompt_review_focus(console)

    return {
        "enable_review": code_review,
        "enable_tests": tests,
        "test_timeout_seconds": test_timeout,
        "max_iterations": max_iterations,
        "triage_mode": triage_mode,
        "review_focus": review_focus,
    }


def _prompt_input_files(console: Console) -> dict[str, str]:
    """Prompt for input file key=path pairs.

    Args:
        console: Console for output.

    Returns:
        Dictionary of variable name to file path mappings.
    """
    add_inputs = Confirm.ask("Add input files?", default=False, console=console)

    if not add_inputs:
        return {}

    input_files: dict[str, str] = {}
    console.print("[dim]Enter key=path pairs (empty to finish):[/]")

    while True:
        entry = Prompt.ask(
            "key=path",
            default="",
            console=console,
        ).strip()

        if not entry:
            break

        if "=" not in entry:
            console.print("[yellow]Invalid format. Use key=path.[/]")
            continue

        key, path = entry.split("=", 1)
        key = key.strip()
        path = path.strip()

        if not key or not path:
            console.print("[yellow]Both key and path are required.[/]")
            continue

        input_files[key] = path

    return input_files


def _prompt_review_focus(console: Console) -> list[str]:
    """Prompt for review focus areas multi-select.

    Args:
        console: Console for output.

    Returns:
        List of selected review focus areas.
    """
    console.print("[dim]Select review focus areas:[/]")

    selected: list[str] = []

    for area in REVIEW_FOCUS_AREAS:
        if Confirm.ask(
            f"Focus on [cyan]{area.replace('_', ' ')}[/]?",
            default=True,
            console=console,
        ):
            selected.append(area)

    return selected


def _parse_int(value: str, default: int) -> int:
    """Parse string to integer with fallback.

    Args:
        value: String value to parse.
        default: Default value if parsing fails.

    Returns:
        Parsed integer or default.
    """
    try:
        return int(value)
    except ValueError:
        return default
