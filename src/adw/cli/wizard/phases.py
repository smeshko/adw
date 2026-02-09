"""Phase customization step for the wizard.

This module handles the phases configuration step where users can customize
individual phase settings including timeouts, hooks, and inputs.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from rich.console import Console
from rich.prompt import Confirm, Prompt
from rich.rule import Rule

from adw.cli.wizard.navigation import nav_confirm_ask

if TYPE_CHECKING:
    from adw.models.wizard import WizardState


# Available phases for customization
AVAILABLE_PHASES: list[str] = ["plan", "build", "validate", "document", "ship"]

# Default timeouts by phase (in seconds)
DEFAULT_TIMEOUTS: dict[str, int] = {
    "plan": 900,  # 15 minutes
    "build": 1800,  # 30 minutes
    "validate": 900,  # 15 minutes
    "document": 900,  # 15 minutes
    "ship": 1200,  # 20 minutes
}


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

    Uses comma-separated input for efficient multi-selection.
    Reprompts if user enters only invalid entries.

    Args:
        console: Console for output.

    Returns:
        List of selected phase names (empty if user enters nothing).
    """
    console.print()
    console.print("[dim]Available phases:[/]")
    for i, phase in enumerate(AVAILABLE_PHASES, 1):
        console.print(f"  [cyan]{i}[/]. {phase}")

    console.print()
    console.print("[dim]Enter phase numbers separated by commas, e.g. 1,3 or 'all'[/]")

    while True:
        selection = Prompt.ask(
            "Phases to customize",
            default="",
            console=console,
        ).strip()

        # Empty input is valid - user chose not to select any
        if not selection:
            return []

        selected, invalid = _parse_phase_selection(selection)

        # Show feedback for invalid entries
        if invalid:
            console.print(f"[yellow]Ignored invalid entries: {', '.join(invalid)}[/]")

        # If we have valid selections, return them
        if selected:
            return selected

        # All entries were invalid - reprompt
        console.print("[yellow]No valid phases selected. Please try again.[/]")
        console.print("[dim]Use numbers (1-5), phase names, or 'all'[/]")


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

    if not enabled:
        return {"enabled": False}

    default_timeout = DEFAULT_TIMEOUTS.get(phase, 300)
    timeout_str = Prompt.ask(
        "Timeout (seconds)",
        default=str(default_timeout),
        console=console,
    )
    timeout = _parse_int(timeout_str, default_timeout)

    # Input files
    input_files = _prompt_input_files(console)

    # LLM model selection
    model = _prompt_model_for_phase(phase, console)

    config: dict[str, Any] = {
        "enabled": enabled,
        "timeout_seconds": timeout,
        "input_files": input_files if input_files else None,
    }

    if model:
        config["llm"] = {"model": model}

    # Document phase special options
    if phase == "document":
        document_config = _configure_document_phase(console)
        config.update(document_config)

    # Ship phase special options
    if phase == "ship":
        ship_config = _configure_ship_phase(console)
        config.update(ship_config)

    return config


def _configure_document_phase(console: Console) -> dict[str, Any]:
    """Configure document phase special options.

    Prompts user to configure doc_mappings which map source file patterns
    to documentation directories for automatic surgical updates.

    Args:
        console: Console for output.

    Returns:
        Document-specific configuration dict.
    """
    console.print()
    console.print("[dim]Document phase options:[/]")
    console.print("[dim]Doc mappings link source file patterns to doc directories.[/]")
    console.print("[dim]When matching source files change, their docs are updated.[/]")

    add_mappings = Confirm.ask("Add doc mappings?", default=False, console=console)

    if not add_mappings:
        return {}

    doc_mappings = _prompt_doc_mappings(console)

    if not doc_mappings:
        return {}

    return {
        "doc_mappings": doc_mappings,
    }


def _configure_ship_phase(console: Console) -> dict[str, Any]:
    """Configure ship phase special options.

    Prompts for deployment commands and PR settings.
    This follows the same pattern as the ship.py standalone step but integrated
    into the common phase configuration flow.

    Args:
        console: Console for output.

    Returns:
        Ship-specific configuration dict.
    """
    console.print()
    console.print("[dim]Ship phase options:[/]")

    # Deployment commands
    console.print("[dim]Enter deployment commands (empty to skip):[/]")
    commands: dict[str, str] = {}

    version_bump = Prompt.ask(
        "Version bump command",
        default="",
        console=console,
    ).strip()
    if version_bump:
        commands["version_bump"] = version_bump

    build_cmd = Prompt.ask(
        "Build command",
        default="",
        console=console,
    ).strip()
    if build_cmd:
        commands["build"] = build_cmd

    publish_cmd = Prompt.ask(
        "Publish command",
        default="",
        console=console,
    ).strip()
    if publish_cmd:
        commands["publish"] = publish_cmd

    return {
        "commands": commands if commands else None,
    }


def _prompt_doc_mappings(console: Console) -> list[dict[str, str]]:
    """Prompt for source pattern to docs directory mappings.

    Args:
        console: Console for output.

    Returns:
        List of doc mapping dictionaries with source_pattern and docs_dir.
    """
    mappings: list[dict[str, str]] = []
    console.print("[dim]Enter source_pattern=docs_dir pairs (empty to finish):[/]")
    console.print("[dim]Example: src/core/**/*.py=docs/architecture[/]")

    while True:
        entry = Prompt.ask(
            "pattern=dir",
            default="",
            console=console,
        ).strip()

        if not entry:
            break

        if "=" not in entry:
            console.print("[yellow]Invalid format. Use source_pattern=docs_dir.[/]")
            continue

        pattern, docs_dir = entry.split("=", 1)
        pattern = pattern.strip()
        docs_dir = docs_dir.strip()

        if not pattern or not docs_dir:
            console.print("[yellow]Both pattern and docs_dir are required.[/]")
            continue

        mappings.append(
            {
                "source_pattern": pattern,
                "docs_dir": docs_dir,
            }
        )
        console.print(f"[green]Added:[/] {pattern} -> {docs_dir}")

    return mappings


def _prompt_model_for_phase(phase: str, console: Console) -> str | None:
    """Prompt for phase-specific model selection.

    Shows a numbered list of model options with descriptions
    and phase-specific defaults. Accepts numeric selection,
    direct model name, or empty input for default.

    Args:
        phase: Phase name (e.g., "plan", "build").
        console: Console for output.

    Returns:
        Model name string, or None if empty input with no preferred default.
    """
    # Model options and descriptions
    models = ["opus", "sonnet", "haiku"]
    model_descriptions = {
        "opus": "Most capable, slower, higher cost",
        "sonnet": "Balanced performance and cost",
        "haiku": "Fastest, lowest cost",
    }

    # Phase-specific defaults
    defaults = {
        "plan": "opus",
        "build": "sonnet",
        "validate": "opus",
        "document": "haiku",
        "ship": "sonnet",
    }
    default = defaults.get(phase)

    # Display numbered list
    console.print()
    console.print(f"[dim]LLM Model for {phase} phase:[/]")
    for i, model in enumerate(models, 1):
        desc = model_descriptions[model]
        default_marker = " [cyan](default)[/]" if model == default else ""
        console.print(f"  [cyan]{i}[/]. {model:7} - {desc}{default_marker}")
    console.print()

    while True:
        prompt_text = f"Model (1-{len(models)} or name)"
        selection = Prompt.ask(
            prompt_text,
            default="" if default else "",
            console=console,
        ).strip()

        # Empty input - use default if available
        if not selection:
            return default

        # Try numeric input
        if selection.isdigit():
            idx = int(selection)
            if 1 <= idx <= len(models):
                return models[idx - 1]
            console.print(
                f"[yellow]Invalid number. Use 1-{len(models)} or type a model name.[/]"
            )
            continue

        # Accept direct model name (case insensitive)
        selection_lower = selection.lower()
        if selection_lower in models:
            return selection_lower

        # Allow any string for custom/full model IDs
        return selection


def _prompt_input_files(console: Console) -> dict[str, str]:
    """Prompt for input file key=path pairs.

    Args:
        console: Console for output.

    Returns:
        Dictionary of variable name to file path mappings.
    """
    add_inputs = nav_confirm_ask("Add input files?", default=False, console=console)

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


def _parse_phase_selection(selection: str) -> tuple[list[str], list[str]]:
    """Parse comma-separated phase selection input.

    Accepts:
    - "all" -> returns all phases
    - "1,3" -> returns phases by number
    - "plan, validate" -> returns phases by name
    - "" or whitespace only -> returns empty list

    Args:
        selection: User input string.

    Returns:
        Tuple of (valid_phases, invalid_entries).
    """
    selection = selection.strip().lower()

    # Empty input
    if not selection:
        return [], []

    # Handle "all" keyword
    if selection == "all":
        return list(AVAILABLE_PHASES), []

    # Split by comma and process each part
    parts = [p.strip() for p in selection.split(",") if p.strip()]
    selected: list[str] = []
    invalid: list[str] = []

    for part in parts:
        matched = False
        # Try as number first
        try:
            idx = int(part)
            if 1 <= idx <= len(AVAILABLE_PHASES):
                phase = AVAILABLE_PHASES[idx - 1]
                if phase not in selected:
                    selected.append(phase)
                matched = True
        except ValueError:
            # Try as phase name
            if part in AVAILABLE_PHASES:
                if part not in selected:
                    selected.append(part)
                matched = True

        if not matched:
            invalid.append(part)

    return selected, invalid
