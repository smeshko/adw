"""Template engine for ADW prompt template rendering.

This module provides a simple regex-based template engine that handles
variable substitution and file inclusion in prompt templates.

Supported patterns:
- {{variable.path}} - Variable substitution from context
- {{include:rel}} - File under the command directory
- {{shared:rel}} - File under the shared commands directory
- {{file:rel}} - File under the project root

Includes are expanded first and variables substituted second, so ADW's
names inside included files are filled. A {{variable.path}} placeholder is
filled only when its first segment is a key of the render context, so
placeholders meant for the LLM pass through.

No recursive expansion is performed for security and simplicity: included
text is not rescanned for directives, and variable values are never expanded.
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

__all__ = [
    "TemplateEngine",
    "build_task_context",
]


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
# Matches {{include:rel}}, {{shared:rel}} and {{file:rel}} inclusion directives.
# include resolves under the command directory, shared under the commands
# directory and file under the project root.
DIRECTIVE_PATTERN = re.compile(r"\{\{(include|shared|file):([^}]+)\}\}")
# Error-code prefix for each directive kind
DIRECTIVE_ERROR_PREFIXES: dict[str, str] = {
    "include": "INCLUDE",
    "shared": "SHARED",
    "file": "TEMPLATE",
}


class TemplateEngine:
    """A simple regex-based template engine for prompt rendering.

    Handles {{variable.path}} substitution and the {{include:...}},
    {{shared:...}} and {{file:...}} inclusion directives.

    The engine makes one pass per stage with no recursive expansion.
    Inclusions are processed first, then variables. Only variables whose
    top-level name is a context key are filled; others are left verbatim.

    Example:
        >>> engine = TemplateEngine(project_root=Path("/project"))
        >>> template = "Hello, {{name}}! Config: {{file:config.txt}}"
        >>> context = {"name": "World"}
        >>> result = engine.render(template, context)
    """

    def __init__(self, project_root: Path | None = None) -> None:
        """Initialize the template engine.

        Args:
            project_root: Root directory for resolving {{file:...}} inclusions.
                         Defaults to current working directory if not provided.
        """
        self.project_root = project_root or Path.cwd()

    def render(
        self,
        template: str,
        context: dict[str, Any] | BaseModel,
        *,
        command_root: Path | None = None,
        shared_root: Path | None = None,
    ) -> str:
        """Render a template with file inclusion and variable substitution.

        Inclusions are expanded first, in one pass, then variables are
        substituted, so variables inside included files are filled. No
        recursive expansion is performed: included text is not rescanned for
        directives, and if a variable value contains template syntax,
        including an inclusion directive, it is NOT expanded.

        A {{name.path}} placeholder is filled only when ``name``, its first
        segment, is a key of ``context``. Any other placeholder belongs to the
        prompt's reader and is left verbatim without logging. A known name
        whose path does not resolve is also left verbatim, with one warning.

        Args:
            template: The template string to render.
            context: Dictionary or Pydantic model providing variable values.
            command_root: Directory for resolving {{include:...}} inclusions.
            shared_root: Directory for resolving {{shared:...}} inclusions.

        Returns:
            The rendered template string.

        Raises:
            ConfigError: If a file inclusion target cannot be read.
        """
        # Convert Pydantic models to dict for variable lookup
        context_dict = self._normalize_context(context)

        result = self._expand_directives(
            template, command_root=command_root, shared_root=shared_root
        )

        # Substitute variables last (single pass, no recursion), so ADW names
        # inside included files are filled and values are never expanded
        return self._process_variables(result, context_dict)

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
    ) -> str:
        """Process variable substitutions in the template.

        Only placeholders whose top-level name is a key of ``context`` are
        filled; the rest pass through untouched.

        Args:
            template: Template string to process.
            context: Dictionary providing variable values.

        Returns:
            Template with variables substituted.
        """

        def replace_variable(match: re.Match[str]) -> str:
            var_path = match.group(1)
            if var_path.split(".", 1)[0] not in context:
                return match.group(0)
            try:
                value = self._resolve_variable(var_path, context)
            except KeyError:
                logger.warning(
                    "Template variable not found, left as-is: {{%s}}",
                    var_path,
                    extra={"variable": var_path},
                )
                return match.group(0)
            # Convert None to empty string, otherwise str() convert
            return "" if value is None else str(value)

        return VARIABLE_PATTERN.sub(replace_variable, template)

    def _expand_directives(
        self,
        template: str,
        *,
        command_root: Path | None,
        shared_root: Path | None,
    ) -> str:
        """Replace every inclusion directive with its file's contents.

        The replacement text is not rescanned, so directives inside an
        included file stay literal.

        Args:
            template: Template string to process.
            command_root: Root for {{include:...}}.
            shared_root: Root for {{shared:...}}.

        Returns:
            Template with every directive replaced.

        Raises:
            ConfigError: If a directive's root is missing or its file cannot
                        be read.
        """
        roots = {
            "include": command_root,
            "shared": shared_root,
            "file": self.project_root,
        }

        def replace_directive(match: re.Match[str]) -> str:
            kind = match.group(1)
            return self._read_under(
                roots[kind], match.group(2).strip(), DIRECTIVE_ERROR_PREFIXES[kind]
            )

        return DIRECTIVE_PATTERN.sub(replace_directive, template)

    @staticmethod
    def _read_under(root: Path | None, rel: str, error_prefix: str) -> str:
        """Read ``rel`` as UTF-8, refusing any path that leaves ``root``.

        Args:
            root: Directory the path must stay inside.
            rel: Path relative to ``root``.
            error_prefix: Prefix for error codes, e.g. "INCLUDE".

        Returns:
            The file's contents.

        Raises:
            ConfigError: ``<prefix>_NO_ROOT``, ``_PATH_TRAVERSAL``,
                        ``_FILE_NOT_FOUND``, ``_FILE_PERMISSION``,
                        ``_FILE_IS_DIRECTORY`` or ``_FILE_ENCODING``.
        """
        if root is None:
            raise ConfigError(
                code=f"{error_prefix}_NO_ROOT",
                message=f"No root directory to resolve {rel} against",
                suggestion="Pass command_root and shared_root to render()",
            )

        # Security: Prevent path traversal attacks. resolve() can itself raise
        # ValueError, e.g. on an embedded NUL byte.
        try:
            resolved_path = (root / rel).resolve()
            if not resolved_path.is_relative_to(root.resolve()):
                raise ValueError(rel)
        except ValueError:
            raise ConfigError(
                code=f"{error_prefix}_PATH_TRAVERSAL",
                message=f"Path traversal not allowed: {rel}",
                suggestion=f"Use a path inside {root}",
            ) from None

        if not resolved_path.exists():
            raise ConfigError(
                code=f"{error_prefix}_FILE_NOT_FOUND",
                message=f"File not found: {rel}",
                suggestion=f"Create the file under {root} or fix the path",
            )

        try:
            return resolved_path.read_text(encoding="utf-8")
        except PermissionError as err:
            raise ConfigError(
                code=f"{error_prefix}_FILE_PERMISSION",
                message=f"Permission denied reading file: {rel}",
                suggestion=f"Check permissions of {resolved_path}",
            ) from err
        except IsADirectoryError as err:
            raise ConfigError(
                code=f"{error_prefix}_FILE_IS_DIRECTORY",
                message=f"Path is a directory, not a file: {rel}",
                suggestion=f"Point to a file under {root}",
            ) from err
        except UnicodeDecodeError as err:
            raise ConfigError(
                code=f"{error_prefix}_FILE_ENCODING",
                message=f"File is not valid UTF-8: {rel}",
                suggestion=f"Save {resolved_path} with UTF-8 encoding",
            ) from err
