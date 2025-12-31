"""Command loader for loading and rendering phase prompts.

This module implements the CommandLoader class that combines command resolution
with template rendering to produce fully rendered prompts ready for LLM execution.

The loader integrates:
- CommandResolver (from Story 2.1) for three-tier command resolution
- TemplateEngine (from Story 2.2) for variable substitution and file inclusion
"""

import json
from pathlib import Path
from typing import TYPE_CHECKING, Any

from adw.commands.resolver import CommandResolver
from adw.commands.template import TemplateEngine
from adw.exceptions import ConfigError

if TYPE_CHECKING:
    from adw.models import ResolvedCommand, RunContext


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

    def load_prompt(
        self,
        phase: str,
        context: "RunContext",
        *,
        pre_hook_output: str = "",
        strict: bool = True,
    ) -> str:
        """Load and render a prompt for the given phase.

        Resolves the command using the three-tier hierarchy, reads the prompt.md
        file, builds context from RunContext, and renders using TemplateEngine.

        Args:
            phase: The phase name (e.g., "plan", "build").
            context: The current run context containing variables for rendering.
            pre_hook_output: Optional output from pre-hook execution.
            strict: If True (default), raise error for unknown variables.

        Returns:
            The fully rendered prompt string.

        Raises:
            ConfigError: If the command cannot be resolved (COMMAND_NOT_FOUND)
                        or if strict=True and unknown variables are found.
        """
        # Resolve command using three-tier hierarchy
        resolved = self.resolver.resolve(phase)

        # Read prompt.md with UTF-8 encoding
        prompt_path = resolved.path / "prompt.md"
        prompt_content = prompt_path.read_text(encoding="utf-8")

        # Build template context from RunContext
        template_context = self._build_context(context, pre_hook_output=pre_hook_output)

        # Render the prompt using TemplateEngine
        rendered = self.template_engine.render(
            prompt_content, template_context, strict=strict
        )

        return rendered

    def _build_context(
        self,
        context: "RunContext",
        *,
        pre_hook_output: str = "",
    ) -> dict[str, Any]:
        """Build template context dictionary from RunContext.

        Creates a flat dictionary with all variables needed for template rendering.

        Args:
            context: The current run context.
            pre_hook_output: Optional output from pre-hook execution.

        Returns:
            Dictionary with template variables:
            - run_id: The ULID run identifier
            - feature_request: The feature description
            - current_phase: Name of the currently active phase
            - artifacts: Dict of phase -> list of artifact paths
            - pre_hook_output: Output from pre-hook (empty string if none)
        """
        return {
            "run_id": context.run_id,
            "feature_request": context.feature_description,
            "current_phase": context.current_phase,
            "artifacts": context.artifacts,
            "pre_hook_output": pre_hook_output,
        }

    def _load_schema(self, resolved: "ResolvedCommand") -> dict[str, Any] | None:
        """Load optional schema.json from command directory.

        Args:
            resolved: The resolved command with path information.

        Returns:
            Parsed JSON Schema dict if schema.json exists, None otherwise.

        Raises:
            ConfigError: If schema.json exists but contains invalid JSON.
        """
        schema_path = resolved.path / "schema.json"

        if not schema_path.exists():
            return None

        try:
            schema_content = schema_path.read_text(encoding="utf-8")
            return json.loads(schema_content)
        except json.JSONDecodeError as e:
            raise ConfigError(
                code="INVALID_SCHEMA",
                message=f"Invalid JSON in schema.json at {schema_path}: {e}",
            ) from e
