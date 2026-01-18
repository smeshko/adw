"""LLM retry configuration step for the wizard.

This module handles the optional LLM retry configuration step where users can
customize retry behavior for transient LLM failures using exponential backoff.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from rich.console import Console
from rich.prompt import Confirm, Prompt

if TYPE_CHECKING:
    from adw.models.wizard import WizardState


# Default retry configuration values
DEFAULT_MAX_RETRIES = 3
DEFAULT_BASE_DELAY = 1.0
DEFAULT_MAX_DELAY = 60.0
DEFAULT_MULTIPLIER = 2.0

# Validation limits
MIN_RETRIES = 1
MAX_RETRIES = 10
MIN_DELAY = 0.1
MAX_DELAY_LIMIT = 300.0
MIN_MULTIPLIER = 1.0  # Exclusive - must be > 1.0
MAX_MULTIPLIER = 5.0


def validate_max_retries(value: str) -> tuple[bool, int | str]:
    """Validate max retries value.

    Args:
        value: The max retries as a string.

    Returns:
        A tuple of (is_valid, result) where result is either the parsed
        integer (if valid) or an error message string (if invalid).
    """
    try:
        retries = int(value)
    except ValueError:
        return (False, "Must be a valid integer")

    if retries < MIN_RETRIES:
        return (False, f"Max retries must be at least {MIN_RETRIES}")

    if retries > MAX_RETRIES:
        return (False, f"Max retries cannot exceed {MAX_RETRIES}")

    return (True, retries)


def validate_base_delay(value: str) -> tuple[bool, float | str]:
    """Validate base delay value.

    Args:
        value: The base delay in seconds as a string.

    Returns:
        A tuple of (is_valid, result) where result is either the parsed
        float (if valid) or an error message string (if invalid).
    """
    try:
        delay = float(value)
    except ValueError:
        return (False, "Must be a valid number")

    if delay < MIN_DELAY:
        return (False, f"Base delay must be at least {MIN_DELAY}s")

    if delay > MAX_DELAY_LIMIT:
        return (False, f"Base delay cannot exceed {MAX_DELAY_LIMIT}s")

    return (True, delay)


def validate_max_delay(value: str, base_delay: float) -> tuple[bool, float | str]:
    """Validate max delay value with cross-validation against base delay.

    Args:
        value: The max delay in seconds as a string.
        base_delay: The base delay to compare against.

    Returns:
        A tuple of (is_valid, result) where result is either the parsed
        float (if valid) or an error message string (if invalid).
    """
    try:
        delay = float(value)
    except ValueError:
        return (False, "Must be a valid number")

    if delay < base_delay:
        return (False, f"Max delay must be >= base delay ({base_delay}s)")

    if delay > MAX_DELAY_LIMIT:
        return (False, f"Max delay cannot exceed {MAX_DELAY_LIMIT}s")

    return (True, delay)


def validate_multiplier(value: str) -> tuple[bool, float | str]:
    """Validate delay multiplier value.

    Args:
        value: The multiplier as a string.

    Returns:
        A tuple of (is_valid, result) where result is either the parsed
        float (if valid) or an error message string (if invalid).
    """
    try:
        mult = float(value)
    except ValueError:
        return (False, "Must be a valid number")

    if mult <= MIN_MULTIPLIER:
        return (False, f"Multiplier must be greater than {MIN_MULTIPLIER}")

    if mult > MAX_MULTIPLIER:
        return (False, f"Multiplier cannot exceed {MAX_MULTIPLIER}")

    return (True, mult)


class RetryStepHandler:
    """Handler for the LLM retry configuration wizard step.

    This step:
    - Prompts user if they want to configure custom retry behavior
    - If yes, prompts for max_retries, base_delay, max_delay, and multiplier
    - Validates all values and ensures max_delay >= base_delay
    """

    def execute(self, state: WizardState, console: Console) -> dict[str, Any]:
        """Execute the retry configuration step.

        Args:
            state: Current wizard state.
            console: Console for output.

        Returns:
            Configuration collected from this step containing:
            - retry_custom: Whether user customized retry behavior
            - retry_max_retries: Maximum number of retries
            - retry_base_delay: Base delay in seconds
            - retry_max_delay: Maximum delay in seconds
            - retry_multiplier: Delay multiplier for exponential backoff
        """
        return run_retry_step(state, console)


def run_retry_step(
    state: WizardState,
    console: Console,
) -> dict[str, Any]:
    """Execute the LLM retry configuration step.

    This is the main entry point for the retry step, implementing
    the full interactive flow for retry configuration.

    Args:
        state: Current wizard state.
        console: Console for output.

    Returns:
        Configuration dict containing retry_custom, retry_max_retries,
        retry_base_delay, retry_max_delay, and retry_multiplier values.
    """
    console.print()
    console.print(
        "[dim]ADW uses exponential backoff when LLM calls fail transiently.[/]"
    )
    console.print(
        f"[dim]Defaults: {DEFAULT_MAX_RETRIES} retries, {DEFAULT_BASE_DELAY}s base, "
        f"{DEFAULT_MAX_DELAY}s max, {DEFAULT_MULTIPLIER}x multiplier[/]"
    )
    console.print()

    # Ask if user wants to configure custom retry behavior
    configure = Confirm.ask(
        "Configure LLM retry behavior?",
        default=False,
        console=console,
    )

    if not configure:
        # Use defaults
        return {
            "retry_custom": False,
            "retry_max_retries": DEFAULT_MAX_RETRIES,
            "retry_base_delay": DEFAULT_BASE_DELAY,
            "retry_max_delay": DEFAULT_MAX_DELAY,
            "retry_multiplier": DEFAULT_MULTIPLIER,
        }

    # Interactive configuration
    console.print()

    # Get max retries
    max_retries = _prompt_max_retries(console)

    # Get base delay
    base_delay = _prompt_base_delay(console)

    # Get max delay (with cross-validation)
    max_delay = _prompt_max_delay(console, base_delay)

    # Get multiplier
    multiplier = _prompt_multiplier(console)

    return {
        "retry_custom": True,
        "retry_max_retries": max_retries,
        "retry_base_delay": base_delay,
        "retry_max_delay": max_delay,
        "retry_multiplier": multiplier,
    }


def _prompt_max_retries(console: Console) -> int:
    """Prompt user for max retries with validation loop.

    Args:
        console: Console for output.

    Returns:
        The validated max retries value.
    """
    while True:
        value_str = Prompt.ask(
            "Max retries",
            default=str(DEFAULT_MAX_RETRIES),
            console=console,
        )

        is_valid, result = validate_max_retries(value_str)
        if is_valid:
            return int(result)
        else:
            console.print(f"[red]Error:[/] {result}")


def _prompt_base_delay(console: Console) -> float:
    """Prompt user for base delay with validation loop.

    Args:
        console: Console for output.

    Returns:
        The validated base delay value.
    """
    while True:
        value_str = Prompt.ask(
            "Base delay (seconds)",
            default=str(DEFAULT_BASE_DELAY),
            console=console,
        )

        is_valid, result = validate_base_delay(value_str)
        if is_valid:
            return float(result)
        else:
            console.print(f"[red]Error:[/] {result}")


def _prompt_max_delay(console: Console, base_delay: float) -> float:
    """Prompt user for max delay with cross-validation against base delay.

    Args:
        console: Console for output.
        base_delay: The base delay to validate against.

    Returns:
        The validated max delay value.
    """
    while True:
        value_str = Prompt.ask(
            "Max delay (seconds)",
            default=str(DEFAULT_MAX_DELAY),
            console=console,
        )

        is_valid, result = validate_max_delay(value_str, base_delay)
        if is_valid:
            return float(result)
        else:
            console.print(f"[red]Error:[/] {result}")


def _prompt_multiplier(console: Console) -> float:
    """Prompt user for delay multiplier with validation loop.

    Args:
        console: Console for output.

    Returns:
        The validated multiplier value.
    """
    while True:
        value_str = Prompt.ask(
            "Delay multiplier",
            default=str(DEFAULT_MULTIPLIER),
            console=console,
        )

        is_valid, result = validate_multiplier(value_str)
        if is_valid:
            return float(result)
        else:
            console.print(f"[red]Error:[/] {result}")
