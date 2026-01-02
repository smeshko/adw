"""Template engine for ADW prompt template rendering.

This module provides a simple regex-based template engine that handles
variable substitution and file inclusion in prompt templates.

Two pattern types are supported:
- {{variable.path}} - Variable substitution from context
- {{file:relative/path}} - File content inclusion

No recursive expansion is performed for security and simplicity.
"""

import logging
import re
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from adw.exceptions import ConfigError

logger = logging.getLogger(__name__)

__all__ = ["TemplateEngine", "escape_feature_description"]


def escape_feature_description(description: str) -> str:
    """Escape special characters in feature description for template safety.

    Escapes characters that could cause issues when the feature description
    is used in templates or shell commands:
    - Backslashes (doubled)
    - Double quotes (escaped with backslash)
    - Dollar signs (escaped with backslash for shell)
    - Backticks (escaped with backslash for shell)

    Args:
        description: The raw feature description from user input.

    Returns:
        The escaped feature description safe for template substitution.

    Example:
        >>> escape_feature_description('Add "quoted" text')
        'Add \\"quoted\\" text'
        >>> escape_feature_description('Use $VAR and `cmd`')
        'Use \\$VAR and \\`cmd\\`'
    """
    # Escape backslashes first (order matters)
    result = description.replace("\\", "\\\\")
    # Escape double quotes
    result = result.replace('"', '\\"')
    # Escape dollar signs (shell variable expansion)
    result = result.replace("$", "\\$")
    # Escape backticks (shell command substitution)
    result = result.replace("`", "\\`")
    return result

# Compile patterns once at module level for efficiency
# Matches {{variable}} or {{variable.nested.path}} or {{variable.*}} for wildcards
VARIABLE_PATTERN = re.compile(r"\{\{([a-z_][a-z0-9_.]*(?:\.\*)?)\}\}")
# Matches {{file:path/to/file.txt}}
FILE_PATTERN = re.compile(r"\{\{file:([^}]+)\}\}")


class TemplateEngine:
    """A simple regex-based template engine for prompt rendering.

    Handles two pattern types:
    - {{variable.path}} - Variable substitution from context dict
    - {{file:relative/path}} - File content inclusion

    The engine processes templates in a single pass with no recursive expansion.
    Variables are processed first, then file inclusions.

    Example:
        >>> engine = TemplateEngine(project_root=Path("/project"))
        >>> template = "Hello, {{name}}! Config: {{file:config.txt}}"
        >>> context = {"name": "World"}
        >>> result = engine.render(template, context)
    """

    def __init__(self, project_root: Path | None = None) -> None:
        """Initialize the template engine.

        Args:
            project_root: Root directory for resolving file inclusions.
                         Defaults to current working directory if not provided.
        """
        self.project_root = project_root or Path.cwd()

    def render(
        self,
        template: str,
        context: dict[str, Any] | BaseModel,
        *,
        strict: bool = True,
    ) -> str:
        """Render a template with variable substitution and file inclusion.

        Variables are processed first, then file inclusions. No recursive
        expansion is performed - if a variable value contains template syntax,
        it is NOT expanded.

        Args:
            template: The template string to render.
            context: Dictionary or Pydantic model providing variable values.
            strict: If True, raise ConfigError for unknown variables.
                   If False, leave unknown variables as-is in output.

        Returns:
            The rendered template string.

        Raises:
            ConfigError: If strict=True and an unknown variable is found,
                        or if a file inclusion target doesn't exist.
        """
        # Convert Pydantic models to dict for variable lookup
        context_dict = self._normalize_context(context)

        # Process variables first (single pass, no recursion)
        result = self._process_variables(template, context_dict, strict=strict)

        # Process file inclusions
        result = self._process_file_inclusions(result)

        return result

    def _normalize_context(self, context: dict[str, Any] | BaseModel) -> dict[str, Any]:
        """Convert context to a dictionary for variable lookup.

        Args:
            context: Dictionary or Pydantic model.

        Returns:
            Dictionary representation of the context.
        """
        if isinstance(context, BaseModel):
            return context.model_dump()
        return context

    def _resolve_variable(
        self,
        path: str,
        context: dict[str, Any],
    ) -> Any:
        """Resolve a dot-notation variable path to its value.

        Supports wildcard patterns like "artifacts.build.*" which expands
        to list all keys at that level.

        Args:
            path: Dot-separated path (e.g., "context.nested.value").
                  Use ".*" suffix for wildcard expansion.
            context: Dictionary to look up values in.

        Returns:
            The resolved value. For wildcards, returns a formatted string
            listing all keys/values at that level.

        Raises:
            KeyError: If the path cannot be resolved.
        """
        # Handle wildcard pattern
        if path.endswith(".*"):
            return self._resolve_wildcard(path[:-2], context)

        parts = path.split(".")
        value: Any = context

        for part in parts:
            if isinstance(value, dict):
                if part not in value:
                    raise KeyError(path)
                value = value[part]
            else:
                # Try attribute access for objects
                if not hasattr(value, part):
                    raise KeyError(path)
                value = getattr(value, part)

        return value

    def _resolve_wildcard(
        self,
        path: str,
        context: dict[str, Any],
    ) -> str:
        """Resolve a wildcard path to list all items at that level.

        For example, "artifacts.build" with wildcard expands to list
        all artifacts in the build phase.

        Args:
            path: Dot-separated path without the ".*" suffix.
            context: Dictionary to look up values in.

        Returns:
            Formatted string listing all keys at the target level.
            Returns empty string if path doesn't exist or target is empty.
        """
        try:
            value = self._resolve_variable(path, context) if path else context
        except KeyError:
            return ""

        if isinstance(value, dict):
            if not value:
                return ""
            # Format as newline-separated list of key: value
            lines = []
            for key, content in value.items():
                preview = self._format_wildcard_value(content)
                lines.append(f"- {key}: {preview}")
            return "\n".join(lines)
        elif isinstance(value, list):
            return "\n".join(f"- {item}" for item in value)
        else:
            return str(value)

    def _format_wildcard_value(self, content: Any, max_length: int = 200) -> str:
        """Format a value for wildcard expansion display.

        Handles nested dicts (like artifact phase maps) by showing their keys
        instead of raw dict repr. Truncates long strings.

        Args:
            content: The value to format.
            max_length: Maximum length before truncation.

        Returns:
            Formatted string representation.
        """
        if isinstance(content, dict):
            # For nested dicts (e.g., artifacts.* showing phase maps),
            # show the available keys instead of raw dict repr
            if not content:
                return "(empty)"
            keys = list(content.keys())
            if len(keys) <= 3:
                return f"[{', '.join(keys)}]"
            return f"[{', '.join(keys[:3])}, ... ({len(keys)} total)]"
        elif isinstance(content, str):
            if len(content) > max_length:
                return content[:max_length] + "..."
            return content
        else:
            result = str(content)
            if len(result) > max_length:
                return result[:max_length] + "..."
            return result

    def _process_variables(
        self,
        template: str,
        context: dict[str, Any],
        *,
        strict: bool,
    ) -> str:
        """Process variable substitutions in the template.

        Args:
            template: Template string to process.
            context: Dictionary providing variable values.
            strict: If True, raise ConfigError for unknown variables.

        Returns:
            Template with variables substituted.

        Raises:
            ConfigError: If strict=True and a variable is not found.
        """
        unknown_vars: list[str] = []

        def replace_variable(match: re.Match[str]) -> str:
            var_path = match.group(1)
            try:
                value = self._resolve_variable(var_path, context)
                # Convert None to empty string, otherwise str() convert
                return "" if value is None else str(value)
            except KeyError:
                if strict:
                    unknown_vars.append(var_path)
                    # Return placeholder for now, will raise after collecting all
                    return match.group(0)
                else:
                    # Log warning in lenient mode
                    logger.warning(
                        "Unknown template variable left as-is",
                        extra={"variable": var_path},
                    )
                    return match.group(0)

        result = VARIABLE_PATTERN.sub(replace_variable, template)

        # Raise error after processing all variables (to report all unknowns)
        if strict and unknown_vars:
            raise ConfigError(
                code="UNKNOWN_VARIABLE",
                message=f"Unknown template variable(s): {', '.join(unknown_vars)}",
                suggestion="Check the variable names match the context keys",
            )

        return result

    def _process_file_inclusions(self, template: str) -> str:
        """Process file inclusion patterns in the template.

        Args:
            template: Template string to process.

        Returns:
            Template with file contents included.

        Raises:
            ConfigError: If a file inclusion target doesn't exist.
        """

        def replace_file(match: re.Match[str]) -> str:
            file_path = match.group(1).strip()
            full_path = self.project_root / file_path

            # Security: Prevent path traversal attacks
            try:
                resolved_path = full_path.resolve()
                project_resolved = self.project_root.resolve()
                if not resolved_path.is_relative_to(project_resolved):
                    raise ConfigError(
                        code="TEMPLATE_PATH_TRAVERSAL",
                        message=f"Path traversal not allowed: {file_path}",
                        suggestion="Use paths relative to project root, not '..'",
                    )
            except ValueError:
                # is_relative_to raises ValueError on Python < 3.9 or invalid paths
                raise ConfigError(
                    code="TEMPLATE_PATH_TRAVERSAL",
                    message=f"Invalid file path: {file_path}",
                    suggestion="Use valid paths relative to the project root",
                ) from None

            if not resolved_path.exists():
                raise ConfigError(
                    code="TEMPLATE_FILE_NOT_FOUND",
                    message=f"Template file not found: {file_path}",
                    suggestion=f"Create the file at {full_path} or fix the path",
                )

            try:
                return resolved_path.read_text(encoding="utf-8")
            except PermissionError as err:
                raise ConfigError(
                    code="TEMPLATE_FILE_PERMISSION",
                    message=f"Permission denied reading file: {file_path}",
                    suggestion="Check file permissions and ownership",
                ) from err
            except IsADirectoryError as err:
                raise ConfigError(
                    code="TEMPLATE_FILE_IS_DIRECTORY",
                    message=f"Path is a directory, not a file: {file_path}",
                    suggestion="Provide a path to a file, not a directory",
                ) from err
            except UnicodeDecodeError as err:
                raise ConfigError(
                    code="TEMPLATE_FILE_ENCODING",
                    message=f"File is not valid UTF-8: {file_path}",
                    suggestion="Ensure the file is saved with UTF-8 encoding",
                ) from err

        return FILE_PATTERN.sub(replace_file, template)
