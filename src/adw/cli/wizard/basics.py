"""Basics configuration step for the wizard.

This module handles the first step of the wizard where users configure
basic project settings: language detection, platform type, and build/test commands.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from rich.console import Console
from rich.prompt import Confirm, Prompt

if TYPE_CHECKING:
    from adw.models.wizard import WizardState

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

# Language detection markers - maps language to file markers
LANGUAGE_MARKERS: dict[str, list[str]] = {
    "python": ["pyproject.toml", "setup.py", "setup.cfg"],
    "javascript": ["package.json"],
    "go": ["go.mod"],
    "rust": ["Cargo.toml"],
    "java": ["pom.xml", "build.gradle", "build.gradle.kts"],
    "ruby": ["Gemfile"],
    "php": ["composer.json"],
}

# Default test commands by language
DEFAULT_TEST_COMMANDS: dict[str, str] = {
    "python": "pytest",
    "javascript": "npm test",
    "go": "go test ./...",
    "rust": "cargo test",
    "java": "./gradlew test",  # Alternative: mvn test
    "ruby": "bundle exec rspec",
    "php": "./vendor/bin/phpunit",
}


def detect_language(project_root: Path) -> str:
    """Detect project language from marker files.

    Checks the project root for common language marker files and returns
    the detected language. If no markers are found, returns "unknown".

    Args:
        project_root: The project root directory to check.

    Returns:
        Lowercase language name (e.g., "python", "javascript") or "unknown".
    """
    for language, markers in LANGUAGE_MARKERS.items():
        if any((project_root / marker).exists() for marker in markers):
            return language
    return "unknown"


def detect_test_command(language: str) -> str:
    """Get the default test command for a language.

    Returns the conventional test command for the given language.
    For unknown or custom languages, returns an empty string.

    Args:
        language: The detected or selected language (lowercase).

    Returns:
        Default test command string, or empty string if unknown.
    """
    return DEFAULT_TEST_COMMANDS.get(language, "")


class BasicsStepHandler:
    """Handler for the basics configuration wizard step.

    This step:
    - Auto-detects project language from marker files
    - Prompts for language confirmation or selection
    - Prompts for platform type (cli/web/api/other)
    - Auto-detects and prompts for test command
    - Prompts for optional build command
    """

    def __init__(self, project_root: Path | None = None) -> None:
        """Initialize the basics step handler.

        Args:
            project_root: The project root directory for detection.
                         If None, uses current working directory.
        """
        self.project_root = project_root or Path.cwd()

    def execute(self, state: WizardState, console: Console) -> dict[str, Any]:
        """Execute the basics configuration step.

        Args:
            state: Current wizard state.
            console: Console for output.

        Returns:
            Configuration collected from this step containing:
            - language: The detected/selected language
            - platform: The selected platform type
            - test_command: The test command (may be empty)
            - build_command: The build command (may be empty)
        """
        return run_basics_step(state, console, self.project_root)


def run_basics_step(
    state: WizardState,
    console: Console,
    project_root: Path | None = None,
) -> dict[str, Any]:
    """Execute the basics configuration step.

    This is the main entry point for the basics step, implementing
    the full interactive flow for basic project configuration.

    Args:
        state: Current wizard state.
        console: Console for output.
        project_root: The project root directory. Defaults to cwd.

    Returns:
        Configuration dict containing language, platform, test_command,
        and build_command values.
    """
    root = project_root or Path.cwd()

    # Step 1: Language detection and confirmation
    detected_language = detect_language(root)
    language = _prompt_language(console, detected_language)

    # Step 2: Platform selection
    platform = _prompt_platform(console)

    # Step 3: Test command (auto-detect based on final language, allow override)
    default_test_cmd = detect_test_command(language)
    test_command = _prompt_test_command(console, default_test_cmd)

    # Step 4: Build command (optional)
    build_command = _prompt_build_command(console)

    return {
        "language": language,
        "platform": platform,
        "test_command": test_command,
        "build_command": build_command,
    }


def _prompt_language(console: Console, detected: str) -> str:
    """Prompt user to confirm or select language.

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

    # Show language selection
    console.print()
    language = Prompt.ask(
        "Select language",
        choices=SUPPORTED_LANGUAGES,
        default=detected if detected != "unknown" else "python",
        console=console,
    )

    # Handle "other" - prompt for custom language
    if language == "other":
        language = Prompt.ask(
            "Enter language name",
            console=console,
        )
        # Normalize to lowercase
        language = language.lower().strip()

    return language


def _prompt_platform(console: Console) -> str:
    """Prompt user to select platform type.

    Args:
        console: Console for output.

    Returns:
        The selected platform type.
    """
    console.print()
    platform = Prompt.ask(
        "Platform type",
        choices=SUPPORTED_PLATFORMS,
        default="cli",
        console=console,
    )

    # Handle "other" - prompt for custom platform
    if platform == "other":
        platform = Prompt.ask(
            "Enter platform type",
            console=console,
        )
        # Normalize to lowercase
        platform = platform.lower().strip()

    return platform


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
