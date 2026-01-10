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
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel

from adw.exceptions import ConfigError

if TYPE_CHECKING:
    from adw.models.task import TaskInfo

logger = logging.getLogger(__name__)

__all__ = ["TemplateEngine", "escape_feature_description", "build_task_context"]


class GracefulDict(dict[str, Any]):
    """A dict subclass that returns a chainable placeholder for missing keys.

    Used for task.custom field access when task_info is None.
    Ensures {{task.custom.<field>}} and nested paths like
    {{task.custom.metadata.details.component}} resolve to empty string
    instead of raising KeyError or staying as placeholder.

    For missing keys, returns another GracefulDict instance (allowing
    infinite nesting), which converts to empty string when used as str.
    """

    def __missing__(self, _key: str) -> "GracefulDict":
        """Return a new GracefulDict for any missing key, allowing nested access."""
        return GracefulDict()

    def __getitem__(self, key: str) -> Any:
        """Return value for key, or new GracefulDict if missing."""
        try:
            return super().__getitem__(key)
        except KeyError:
            return GracefulDict()

    def get(self, key: str, default: Any = None) -> Any:
        """Return value for key with default."""
        result = super().get(key)
        if result is None:
            return default if default is not None else GracefulDict()
        return result

    def __str__(self) -> str:
        """Return empty string when converted to string (for template output)."""
        return ""

    def __repr__(self) -> str:
        """Return empty string for repr (used in f-strings and str() calls)."""
        if not self:
            return ""
        return super().__repr__()

    def __bool__(self) -> bool:
        """Return False when empty (for conditional checks)."""
        return bool(super().keys())

# Priority label mapping (1=Urgent, 2=High, 3=Medium, 4=Low)
PRIORITY_LABELS: dict[int, str] = {
    1: "Urgent",
    2: "High",
    3: "Medium",
    4: "Low",
}


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


def build_task_context(task_info: "TaskInfo | None") -> dict[str, Any]:
    """Build task variable context from TaskInfo for template rendering.

    Converts TaskInfo model fields into a flat dict structure suitable for
    template variable substitution via {{task.*}} syntax.

    The returned dict supports:
    - Direct field access: {{task.id}}, {{task.title}}, etc.
    - Priority label: {{task.priority_label}} -> "High"
    - Labels as string: {{task.labels}} -> "bug, urgent"
    - Custom fields: {{task.custom.field_name}}

    Args:
        task_info: TaskInfo model from task manager, or None if no task context.

    Returns:
        Dict mapping task variable names to string values. Returns empty dict
        if task_info is None, allowing graceful degradation in templates.

    Example:
        >>> from adw.models.task import TaskInfo
        >>> task = TaskInfo(
        ...     id="abc123",
        ...     identifier="RULE-123",
        ...     title="Fix login bug",
        ...     priority=2,
        ...     labels=["bug", "urgent"],
        ... )
        >>> context = build_task_context(task)
        >>> context["id"]
        'abc123'
        >>> context["priority_label"]
        'High'
        >>> context["labels"]
        'bug, urgent'
    """
    if task_info is None:
        logger.debug("No task_info available, task context will use empty strings")
        # Return dict with all keys as empty strings for graceful degradation
        # This ensures {{task.*}} variables resolve to empty string, not stay as-is
        # Use GracefulDict for custom so {{task.custom.<field>}} also resolves to ""
        return {
            "id": "",
            "identifier": "",
            "title": "",
            "description": "",
            "status": "",
            "priority": "",
            "priority_label": "",
            "labels": "",
            "assignee": "",
            "parent_id": "",
            "parent_title": "",
            "custom": GracefulDict(),
        }

    return {
        "id": task_info.id or "",
        "identifier": task_info.identifier or "",
        "title": task_info.title or "",
        "description": task_info.description or "",
        "status": task_info.status or "",
        "priority": str(task_info.priority) if task_info.priority else "",
        "priority_label": PRIORITY_LABELS.get(task_info.priority or 0, ""),
        "labels": ", ".join(task_info.labels) if task_info.labels else "",
        "assignee": task_info.assignee or "",
        "parent_id": task_info.parent_id or "",
        "parent_title": task_info.parent_title or "",
        "custom": task_info.custom_fields or {},
    }


# Compile patterns once at module level for efficiency
# Matches {{variable}} or {{variable.nested.path}} or {{variable.*}} for wildcards
VARIABLE_PATTERN = re.compile(r"\{\{([a-z_][a-z0-9_.]*(?:\.\*)?)\}\}")
# Pattern to match artifact references in templates: {{artifacts.phase.name}}
# Also matches wildcards like {{artifacts.phase.*}} and {{artifacts.*}}
# ISS-017: Consolidated from phase_runner.py to template.py
ARTIFACT_REF_PATTERN = re.compile(r"\{\{artifacts\.([a-z_][a-z0-9_.]*(?:\.\*)?)\}\}")
# Matches {{file:path/to/file.txt}} - resolves relative to project root
FILE_PATTERN = re.compile(r"\{\{file:([^}]+)\}\}")
# Matches {{include:filename}} - resolves relative to command directory
INCLUDE_PATTERN = re.compile(r"\{\{include:([^}]+)\}\}")
# Matches {{shared:filename}} - resolves relative to shared commands directory
SHARED_PATTERN = re.compile(r"\{\{shared:([^}]+)\}\}")


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

    def __init__(
        self,
        project_root: Path | None = None,
        command_root: Path | None = None,
        shared_root: Path | None = None,
    ) -> None:
        """Initialize the template engine.

        Args:
            project_root: Root directory for resolving {{file:...}} inclusions.
                         Defaults to current working directory if not provided.
            command_root: Directory for resolving {{include:...}} inclusions.
                         Used for files bundled with the command (e.g., SDK defaults).
                         If not provided, {{include:...}} patterns will error.
            shared_root: Directory for resolving {{shared:...}} inclusions.
                        Used for files shared across all commands (e.g., commands/).
                        If not provided, {{shared:...}} patterns will error.
        """
        self.project_root = project_root or Path.cwd()
        self.command_root = command_root
        self.shared_root = shared_root

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

        # Process command-local includes ({{include:...}})
        result = self._process_includes(result)

        # Process shared includes ({{shared:...}})
        result = self._process_shared_inclusions(result)

        # Process project file inclusions ({{file:...}})
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
                # For GracefulDict (used for task.custom when no task_info),
                # use __getitem__ directly to get empty string default
                if isinstance(value, GracefulDict):
                    value = value[part]
                elif part not in value:
                    raise KeyError(path)
                else:
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

    def _process_includes(self, template: str) -> str:
        """Process command-local include patterns in the template.

        Resolves {{include:filename}} relative to command_root (the command directory).
        This is used for files bundled with commands (e.g., SDK defaults).

        Args:
            template: Template string to process.

        Returns:
            Template with included file contents.

        Raises:
            ConfigError: If command_root is not set, file doesn't exist,
                        or path traversal is attempted.
        """
        if not INCLUDE_PATTERN.search(template):
            return template  # No includes, skip processing

        if self.command_root is None:
            raise ConfigError(
                code="INCLUDE_NO_COMMAND_ROOT",
                message="Cannot process {{include:...}} without command_root",
                suggestion="Set command_root when initializing TemplateEngine",
            )

        def replace_include(match: re.Match[str]) -> str:
            file_path = match.group(1).strip()
            full_path = self.command_root / file_path  # type: ignore[operator]

            # Security: Prevent path traversal attacks
            try:
                resolved_path = full_path.resolve()
                command_resolved = self.command_root.resolve()  # type: ignore[union-attr]
                if not resolved_path.is_relative_to(command_resolved):
                    raise ConfigError(
                        code="INCLUDE_PATH_TRAVERSAL",
                        message=f"Path traversal not allowed: {file_path}",
                        suggestion="Use paths relative to command directory, not '..'",
                    )
            except ValueError:
                raise ConfigError(
                    code="INCLUDE_PATH_TRAVERSAL",
                    message=f"Invalid include path: {file_path}",
                    suggestion="Use valid paths relative to the command directory",
                ) from None

            if not resolved_path.exists():
                raise ConfigError(
                    code="INCLUDE_FILE_NOT_FOUND",
                    message=f"Include file not found: {file_path}",
                    suggestion=f"Create the file at {full_path} or fix the path",
                )

            try:
                return resolved_path.read_text(encoding="utf-8")
            except PermissionError as err:
                raise ConfigError(
                    code="INCLUDE_FILE_PERMISSION",
                    message=f"Permission denied reading file: {file_path}",
                    suggestion="Check file permissions and ownership",
                ) from err
            except IsADirectoryError as err:
                raise ConfigError(
                    code="INCLUDE_FILE_IS_DIRECTORY",
                    message=f"Path is a directory, not a file: {file_path}",
                    suggestion="Provide a path to a file, not a directory",
                ) from err
            except UnicodeDecodeError as err:
                raise ConfigError(
                    code="INCLUDE_FILE_ENCODING",
                    message=f"File is not valid UTF-8: {file_path}",
                    suggestion="Ensure the file is saved with UTF-8 encoding",
                ) from err

        return INCLUDE_PATTERN.sub(replace_include, template)

    def _process_shared_inclusions(self, template: str) -> str:
        """Process shared include patterns in the template.

        Resolves {{shared:filename}} relative to shared_root (the commands directory).
        This is used for files shared across all commands.

        Args:
            template: Template string to process.

        Returns:
            Template with included file contents.

        Raises:
            ConfigError: If shared_root is not set, file doesn't exist,
                        or path traversal is attempted.
        """
        if not SHARED_PATTERN.search(template):
            return template  # No shared includes, skip processing

        if self.shared_root is None:
            raise ConfigError(
                code="SHARED_NO_ROOT",
                message="Cannot process {{shared:...}} without shared_root",
                suggestion="Set shared_root when initializing TemplateEngine",
            )

        def replace_shared(match: re.Match[str]) -> str:
            file_path = match.group(1).strip()
            full_path = self.shared_root / file_path  # type: ignore[operator]

            # Security: Prevent path traversal attacks
            try:
                resolved_path = full_path.resolve()
                shared_resolved = self.shared_root.resolve()  # type: ignore[union-attr]
                if not resolved_path.is_relative_to(shared_resolved):
                    raise ConfigError(
                        code="SHARED_PATH_TRAVERSAL",
                        message=f"Path traversal not allowed: {file_path}",
                        suggestion="Use paths relative to shared directory, not '..'",
                    )
            except ValueError:
                raise ConfigError(
                    code="SHARED_PATH_TRAVERSAL",
                    message=f"Invalid shared path: {file_path}",
                    suggestion="Use valid paths relative to the shared directory",
                ) from None

            if not resolved_path.exists():
                raise ConfigError(
                    code="SHARED_FILE_NOT_FOUND",
                    message=f"Shared file not found: {file_path}",
                    suggestion=f"Create the file at {full_path} or fix the path",
                )

            try:
                return resolved_path.read_text(encoding="utf-8")
            except PermissionError as err:
                raise ConfigError(
                    code="SHARED_FILE_PERMISSION",
                    message=f"Permission denied reading file: {file_path}",
                    suggestion="Check file permissions and ownership",
                ) from err
            except IsADirectoryError as err:
                raise ConfigError(
                    code="SHARED_FILE_IS_DIRECTORY",
                    message=f"Path is a directory, not a file: {file_path}",
                    suggestion="Provide a path to a file, not a directory",
                ) from err
            except UnicodeDecodeError as err:
                raise ConfigError(
                    code="SHARED_FILE_ENCODING",
                    message=f"File is not valid UTF-8: {file_path}",
                    suggestion="Ensure the file is saved with UTF-8 encoding",
                ) from err

        return SHARED_PATTERN.sub(replace_shared, template)
