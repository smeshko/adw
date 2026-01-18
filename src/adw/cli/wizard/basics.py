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

    # Language detection and confirmation will be implemented in Task 2 & 4
    language = "unknown"

    # Platform selection will be implemented in Task 4
    platform = "cli"

    # Test command detection will be implemented in Task 3 & 4
    test_command = ""

    # Build command will be implemented in Task 4
    build_command = ""

    return {
        "language": language,
        "platform": platform,
        "test_command": test_command,
        "build_command": build_command,
    }
