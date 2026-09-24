"""Basics configuration step for the wizard.

This module handles the first step of the wizard where users configure
basic project settings: language detection, platform type, and build/test commands.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from rich.console import Console
from rich.prompt import Confirm, Prompt

from adw.config.detector import ProjectTypeDetector

# Supported languages for selection
SUPPORTED_LANGUAGES: list[str] = [
    "python",
    "javascript",
    "go",
    "rust",
    "java",
    "ruby",
    "php",
    "other",
]

# Supported platform types
SUPPORTED_PLATFORMS: list[str] = ["cli", "web", "api", "other"]


def run_basics_step(console: Console, root: Path) -> dict[str, Any]:
    """Execute the basics configuration step.

    This is the main entry point for the basics step, implementing
    the full interactive flow for basic project configuration.

    Args:
        console: Console for output.
        root: The project root directory, where detection looks for markers.

    Returns:
        Configuration dict containing project_name (the project root's
        directory name), language, platform, test_command and build_command.
    """
    detector = ProjectTypeDetector()

    # Step 1: Language detection and confirmation
    detected: str = (
        detector.get_defaults(detector.detect(root))["language"] or "unknown"
    )
    language = _prompt_language(console, detected)

    # Step 2: Platform selection
    platform = _prompt_platform(console)

    # Step 3: Test command (default follows the final language, allow override)
    default_test_cmd = detector.get_defaults(language)["test_command"] or ""
    test_command = _prompt_test_command(console, default_test_cmd)

    # Step 4: Build command (optional)
    build_command = _prompt_build_command(console)

    return {
        "project_name": root.name,
        "language": language,
        "platform": platform,
        "test_command": test_command,
        "build_command": build_command,
    }


def _prompt_language(console: Console, detected: str) -> str:
    """Prompt user to confirm or select language.

    Shows a numbered list but accepts either a number or direct text input,
    allowing users to type custom languages without selecting "other" first.

    Args:
        console: Console for output.
        detected: The auto-detected language.

    Returns:
        The confirmed or selected language.
    """
    if detected != "unknown":
        # Show detection and ask for confirmation
        confirmed = Confirm.ask(
            f"Language detected: [cyan]{detected}[/]. Correct?",
            default=True,
            console=console,
        )
        if confirmed:
            return detected

    # Show language options as numbered list
    console.print()
    console.print("[dim]Available languages:[/]")
    # Filter out 'other' since user can just type any custom language
    display_languages = [lang for lang in SUPPORTED_LANGUAGES if lang != "other"]
    for i, lang in enumerate(display_languages, 1):
        console.print(f"  [cyan]{i}[/]. {lang}")
    console.print("[dim]  Or type a custom language name[/]")
    console.print()

    while True:
        selection = Prompt.ask(
            "Language",
            default=detected if detected != "unknown" else "python",
            console=console,
        ).strip()

        if not selection:
            console.print("[yellow]Language cannot be empty.[/]")
            continue

        # Try to parse as number
        if selection.isdigit():
            idx = int(selection)
            if 1 <= idx <= len(display_languages):
                return display_languages[idx - 1]
            console.print(
                f"[yellow]Invalid number."
                f" Use 1-{len(display_languages)}"
                " or type a name.[/]"
            )
            continue

        # Accept as custom language
        return selection.lower()


def _prompt_platform(console: Console) -> str:
    """Prompt user to select platform type.

    Shows a numbered list but accepts either a number or direct text input,
    allowing users to type custom platforms without selecting "other" first.

    Args:
        console: Console for output.

    Returns:
        The selected platform type.
    """
    # Show platform options as numbered list
    console.print()
    console.print("[dim]Available platforms:[/]")
    # Filter out 'other' since user can just type any custom platform
    display_platforms = [plat for plat in SUPPORTED_PLATFORMS if plat != "other"]
    for i, plat in enumerate(display_platforms, 1):
        console.print(f"  [cyan]{i}[/]. {plat}")
    console.print("[dim]  Or type a custom platform name[/]")
    console.print()

    while True:
        selection = Prompt.ask(
            "Platform",
            default="cli",
            console=console,
        ).strip()

        if not selection:
            console.print("[yellow]Platform cannot be empty.[/]")
            continue

        # Try to parse as number
        if selection.isdigit():
            idx = int(selection)
            if 1 <= idx <= len(display_platforms):
                return display_platforms[idx - 1]
            console.print(
                f"[yellow]Invalid number."
                f" Use 1-{len(display_platforms)}"
                " or type a name.[/]"
            )
            continue

        # Accept as custom platform
        return selection.lower()


def _prompt_test_command(console: Console, default: str) -> str:
    """Prompt user for test command.

    Shows the auto-detected command as default, allows user to
    enter any custom command.

    Args:
        console: Console for output.
        default: The auto-detected test command.

    Returns:
        The test command (may be empty if user skips).
    """
    console.print()
    prompt_text = "Test command"
    if default:
        prompt_text += f" (detected: [cyan]{default}[/])"

    test_cmd = Prompt.ask(
        prompt_text,
        default=default,
        console=console,
    )

    return test_cmd.strip()


def _prompt_build_command(console: Console) -> str:
    """Prompt user for optional build command.

    Args:
        console: Console for output.

    Returns:
        The build command (may be empty if user skips).
    """
    console.print()
    build_cmd = Prompt.ask(
        "Build command (Enter to skip)",
        default="",
        console=console,
    )

    return build_cmd.strip()
