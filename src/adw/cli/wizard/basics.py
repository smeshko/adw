"""Basics configuration step for the wizard.

This module handles the first step of the wizard where users configure
basic project settings: language detection, platform type, and build/test commands.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from rich.console import Console

if TYPE_CHECKING:
    from adw.models.wizard import WizardState

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

    # Detect language from project markers
    language = detect_language(root)

    # Platform selection will be implemented in Task 4
    platform = "cli"

    # Detect test command based on language
    test_command = detect_test_command(language)

    # Build command will be implemented in Task 4
    build_command = ""

    return {
        "language": language,
        "platform": platform,
        "test_command": test_command,
        "build_command": build_command,
    }
