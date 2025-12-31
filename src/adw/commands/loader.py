"""Command loader for loading and rendering phase prompts.

This module implements the CommandLoader class that combines command resolution
with template rendering to produce fully rendered prompts ready for LLM execution.

The loader integrates:
- CommandResolver (from Story 2.1) for three-tier command resolution
- TemplateEngine (from Story 2.2) for variable substitution and file inclusion
"""

from pathlib import Path
from typing import TYPE_CHECKING

from adw.commands.resolver import CommandResolver
from adw.commands.template import TemplateEngine

if TYPE_CHECKING:
    from adw.models import RunContext


class CommandLoader:
    """Loads and renders command prompts from resolved directories.

    Combines command resolution with template rendering to produce
    fully rendered prompts ready for LLM execution.

    The loader:
    1. Uses CommandResolver to find the command directory
    2. Reads prompt.md from the resolved directory
    3. Builds template context from RunContext
    4. Uses TemplateEngine to render the prompt

    Example:
        >>> loader = CommandLoader(project_root=Path("."))
        >>> command = loader.load_prompt("plan", context)
        >>> print(command.prompt_content)
        "..."
    """

    def __init__(
        self,
        project_root: Path | None = None,
        resolver: CommandResolver | None = None,
        template_engine: TemplateEngine | None = None,
    ) -> None:
        """Initialize the CommandLoader.

        Args:
            project_root: Root directory for the project. Defaults to cwd.
            resolver: Optional CommandResolver instance. Created if not provided.
            template_engine: Optional TemplateEngine instance. Created if not provided.
        """
        self.project_root = project_root or Path.cwd()
        self.resolver = resolver or CommandResolver(project_root=self.project_root)
        self.template_engine = template_engine or TemplateEngine(
            project_root=self.project_root
        )

    def load_prompt(self, phase: str, context: "RunContext") -> str:
        """Load and render a prompt for the given phase.

        Resolves the command using the three-tier hierarchy, reads the prompt.md
        file, and returns the prompt content (rendering will be added in Task 4).

        Args:
            phase: The phase name (e.g., "plan", "build").
            context: The current run context containing variables for rendering.

        Returns:
            The prompt content (currently unrendered, rendering added in Task 4).

        Raises:
            ConfigError: If the command cannot be resolved (COMMAND_NOT_FOUND).
        """
        # Resolve command using three-tier hierarchy
        resolved = self.resolver.resolve(phase)

        # Read prompt.md with UTF-8 encoding
        prompt_path = resolved.path / "prompt.md"
        prompt_content = prompt_path.read_text(encoding="utf-8")

        return prompt_content
