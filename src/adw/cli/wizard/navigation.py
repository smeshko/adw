"""Navigation helpers for wizard prompts.

This module provides utilities for handling navigation commands (back/cancel)
within wizard prompts. Since Rich prompts don't support real-time key detection,
navigation is handled by checking if the user's input is exactly "b" or "c"
after they press Enter.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from rich.console import Console
from rich.prompt import Prompt


class NavigationSignal(Enum):
    """Signals for wizard navigation."""

    BACK = "back"
    CANCEL = "cancel"


class NavigationError(Exception):
    """Raised when navigation is requested during a prompt."""

    def __init__(self, signal: NavigationSignal) -> None:
        """Initialize with navigation signal.

        Args:
            signal: The navigation signal that was triggered.
        """
        self.signal = signal
        super().__init__(f"Navigation requested: {signal.value}")


def check_navigation(value: str) -> NavigationSignal | None:
    """Check if input is a navigation command.

    Args:
        value: The user's input string.

    Returns:
        NavigationSignal if navigation requested, None otherwise.
    """
    lower = value.lower().strip()
    if lower == "b":
        return NavigationSignal.BACK
    if lower == "c":
        return NavigationSignal.CANCEL
    return None


def nav_prompt_ask(
    question: str,
    *,
    console: Console | None = None,
    default: str = ...,  # type: ignore[assignment]
    choices: list[str] | None = None,
    show_choices: bool = True,
    **kwargs: Any,
) -> str:
    """Navigation-aware version of Prompt.ask.

    Checks if user input is a navigation command (b/c) and raises
    NavigationError if so. Otherwise returns the input normally.

    Args:
        question: The question to ask.
        console: Console for output.
        default: Default value if user presses Enter.
        choices: List of valid choices (optional).
        show_choices: Whether to show choices in prompt.
        **kwargs: Additional arguments passed to Prompt.ask.

    Returns:
        The user's input string.

    Raises:
        NavigationError: If user enters 'b' (back) or 'c' (cancel).
    """
    # Build prompt kwargs
    prompt_kwargs: dict[str, Any] = {**kwargs}
    if console is not None:
        prompt_kwargs["console"] = console
    if default is not ...:  # type: ignore[comparison-overlap]
        prompt_kwargs["default"] = default
    if choices is not None:
        prompt_kwargs["choices"] = choices
        prompt_kwargs["show_choices"] = show_choices

    result: str = Prompt.ask(question, **prompt_kwargs)

    # Check for navigation commands
    nav = check_navigation(result)
    if nav is not None:
        raise NavigationError(nav)

    return result


def nav_confirm_ask(
    question: str,
    *,
    console: Console | None = None,
    default: bool = True,
    **kwargs: Any,  # noqa: ARG001
) -> bool:
    """Navigation-aware confirm prompt using text input.

    Unlike Rich's Confirm.ask which only accepts y/n, this uses a text
    prompt that accepts y/yes/n/no as well as navigation commands (b/back).

    Args:
        question: The question to ask.
        console: Console for output.
        default: Default value if user presses Enter.

    Returns:
        True for yes, False for no.

    Raises:
        NavigationError: If user enters 'b' or 'back' for back navigation.
    """
    default_str = "y" if default else "n"
    prompt_text = f"{question} [y/n]"

    while True:
        prompt_kwargs: dict[str, Any] = {"default": default_str}
        if console is not None:
            prompt_kwargs["console"] = console

        result = Prompt.ask(prompt_text, **prompt_kwargs).lower().strip()

        # Check for navigation commands first
        nav = check_navigation(result)
        if nav is not None:
            raise NavigationError(nav)

        # Parse yes/no responses
        if result in ("y", "yes", "true", "1"):
            return True
        if result in ("n", "no", "false", "0"):
            return False

        # Invalid input - show error and re-prompt
        if console:
            console.print("[yellow]Please enter Y or N[/]")
