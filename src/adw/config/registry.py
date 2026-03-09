"""Configuration registry for extracting settings with defaults and descriptions.

This module provides a centralized registry of all configuration settings
used by ADW, extracting metadata from Pydantic models to enable generation
of complete config files with commented defaults.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, get_args, get_origin

from pydantic import BaseModel
from pydantic.fields import FieldInfo
from pydantic_core import PydanticUndefined


@dataclass
class SettingDefinition:
    """Definition of a single configuration setting.

    Attributes:
        name: Setting name (e.g., "enabled" or "git.branch_prefix")
        type_hint: Type annotation as string (e.g., "int", "str | None")
        default: Default value (None if required or no default)
        description: Human-readable description of the setting
        is_nested: Whether this setting contains nested settings
        is_required: Whether this setting is required (no default)
        children: Nested settings if is_nested is True
    """

    name: str
    type_hint: str
    default: Any
    description: str
    is_nested: bool = False
    is_required: bool = False
    children: list[SettingDefinition] = field(default_factory=list)


class ConfigRegistry:
    """Registry of all configuration settings with metadata.

    Extracts setting definitions from Pydantic models, providing
    a complete catalog of available settings with their defaults
    and descriptions for config file generation.

    Example:
        >>> registry = ConfigRegistry()
        >>> settings = registry.get_all_settings("git")
        >>> for setting in settings:
        ...     print(f"{setting.name}: {setting.default}")
    """

    # Section order for project.yaml generation
    SECTION_ORDER = [
        "project",  # name, language, platform, commands
        "git",
        "task_manager",
        "ports",
        "llm",
        "security",
        "webhook",
        "ship",
    ]

    # Phase-specific settings
    PHASE_SETTINGS = [
        "enabled",
        "input_files",
    ]

    def __init__(self) -> None:
        """Initialize the config registry and build settings catalog."""
        self._settings: dict[str, list[SettingDefinition]] = {}
        self._build_catalog()

    def _build_catalog(self) -> None:
        """Build the complete settings catalog from Pydantic models."""
        # Import models here to avoid circular imports
        from adw.models.command import (
            ShipCommandConfig,
            ShipCommandsConfig,
            ValidateCommandConfig,
        )
        from adw.models.config import (
            GitConfig,
            LLMConfig,
            PhaseConfig,
            PortRangeConfig,
            ProjectConfig,
            RetryConfig,
            TaskManagerConfig,
            TaskManagerLabelsConfig,
            WorktreeConfig,
        )
        from adw.models.webhook import ProviderConfig, WebhookConfig

        # Project-level settings (top-level scalar fields)
        self._settings["project"] = self._extract_project_settings(ProjectConfig)

        # Nested config sections
        self._settings["git"] = self._extract_from_model(GitConfig)
        self._settings["llm"] = self._extract_from_model(LLMConfig)
        self._settings["task_manager"] = self._extract_from_model(
            TaskManagerConfig, skip_nested=["labels"]
        )
        self._settings["task_manager_labels"] = self._extract_from_model(
            TaskManagerLabelsConfig
        )
        self._settings["worktree"] = self._extract_from_model(
            WorktreeConfig, skip_nested=["port_range"]
        )
        self._settings["ports"] = self._extract_from_model(PortRangeConfig)
        self._settings["retry"] = self._extract_from_model(RetryConfig)
        self._settings["security"] = self._extract_security_settings()
        self._settings["webhook"] = self._extract_webhook_settings(WebhookConfig)
        self._settings["webhook_provider"] = self._extract_from_model(ProviderConfig)
        self._settings["ship"] = self._extract_from_model(
            ShipCommandConfig, skip_nested=["commands"]
        )
        self._settings["ship_commands"] = self._extract_from_model(ShipCommandsConfig)
        self._settings["validate"] = self._extract_from_model(
            ValidateCommandConfig, skip_nested=["llm"]
        )

        # Phase-specific settings
        self._settings["phase"] = self._extract_from_model(PhaseConfig)

    def _extract_project_settings(
        self, model: type[BaseModel]
    ) -> list[SettingDefinition]:
        """Extract top-level project settings (non-nested).

        Args:
            model: The ProjectConfig model class.

        Returns:
            List of setting definitions for scalar project fields.
        """
        settings = []
        scalar_fields = [
            "name",
            "language",
            "framework",
            "platform",
            "test_command",
            "build_command",
        ]

        for field_name in scalar_fields:
            if field_name not in model.model_fields:
                continue

            field_info = model.model_fields[field_name]
            settings.append(self._field_to_setting(field_name, field_info))

        return settings

    def _extract_from_model(
        self,
        model: type[BaseModel],
        skip_nested: list[str] | None = None,
    ) -> list[SettingDefinition]:
        """Extract settings from a Pydantic model.

        Args:
            model: The Pydantic model class to extract from.
            skip_nested: Field names to skip (for separately catalogued nested configs).

        Returns:
            List of setting definitions.
        """
        skip_nested = skip_nested or []
        settings = []

        for field_name, field_info in model.model_fields.items():
            if field_name in skip_nested:
                continue

            setting = self._field_to_setting(field_name, field_info)
            settings.append(setting)

        return settings

    def _extract_security_settings(self) -> list[SettingDefinition]:
        """Extract security settings with custom descriptions.

        Returns:
            List of security-related setting definitions.
        """
        from adw.models.security import SecurityConfig

        return self._extract_from_model(SecurityConfig)

    def _extract_webhook_settings(
        self, model: type[BaseModel]
    ) -> list[SettingDefinition]:
        """Extract webhook settings, skipping complex nested structures.

        Args:
            model: The WebhookConfig model class.

        Returns:
            List of webhook setting definitions.
        """
        settings = []
        # Only include simple scalar fields, not complex nested mappings
        simple_fields = ["enabled", "port", "host", "path", "secret_header"]

        for field_name in simple_fields:
            if field_name not in model.model_fields:
                continue

            field_info = model.model_fields[field_name]
            settings.append(self._field_to_setting(field_name, field_info))

        return settings

    def _field_to_setting(
        self, field_name: str, field_info: FieldInfo
    ) -> SettingDefinition:
        """Convert a Pydantic field to a SettingDefinition.

        Args:
            field_name: Name of the field.
            field_info: Pydantic FieldInfo object.

        Returns:
            SettingDefinition with extracted metadata.
        """
        # Get type hint as string
        type_hint = self._type_to_string(field_info.annotation)

        # Get default value
        default = field_info.default
        is_required = default is PydanticUndefined

        # Handle default_factory
        if default is PydanticUndefined and field_info.default_factory is not None:
            try:
                default = field_info.default_factory()  # type: ignore[call-arg]
                is_required = False
            except Exception:
                default = None

        # For BaseModel defaults, use None (they're nested)
        is_nested = isinstance(default, BaseModel)
        if is_nested:
            default = None

        # Get description
        description = field_info.description or f"Configure {field_name}"

        return SettingDefinition(
            name=field_name,
            type_hint=type_hint,
            default=default,
            description=description,
            is_nested=is_nested,
            is_required=is_required,
        )

    def _type_to_string(self, annotation: Any) -> str:
        """Convert a type annotation to a human-readable string.

        Args:
            annotation: Type annotation to convert.

        Returns:
            String representation of the type.
        """
        if annotation is None:
            return "Any"

        origin = get_origin(annotation)
        args = get_args(annotation)

        # Handle Union types (including X | None)
        if origin is type(int | str):  # UnionType
            type_strs = [self._type_to_string(arg) for arg in args]
            return " | ".join(type_strs)

        # Handle generic types like list[str], dict[str, Any]
        if origin is not None:
            origin_name = getattr(origin, "__name__", str(origin))
            if args:
                arg_strs = [self._type_to_string(arg) for arg in args]
                return f"{origin_name}[{', '.join(arg_strs)}]"
            return origin_name

        # Handle Literal types
        if hasattr(annotation, "__origin__") and annotation.__origin__ is type(None):
            return "None"

        # Simple types
        if hasattr(annotation, "__name__"):
            return str(annotation.__name__)

        return str(annotation)

    def get_all_settings(self, section: str) -> list[SettingDefinition]:
        """Get all settings for a configuration section.

        Args:
            section: Section name (e.g., "git", "llm", "project").

        Returns:
            Ordered list of setting definitions for the section.

        Raises:
            KeyError: If the section is not found.
        """
        if section not in self._settings:
            raise KeyError(f"Unknown config section: {section}")

        return list(self._settings[section])

    def get_phase_settings(self, phase: str) -> list[SettingDefinition]:
        """Get settings available for a specific phase.

        All phases share the same base settings (enabled,
        input_files). Phase-specific settings may be added via the phase
        name for validation phases.

        Args:
            phase: Phase name (e.g., "plan", "build", "validate").

        Returns:
            List of setting definitions for the phase.
        """
        # Base phase settings apply to all phases
        return list(self._settings.get("phase", []))

    def get_section_order(self) -> list[str]:
        """Get the recommended order for configuration sections.

        Returns:
            List of section names in display order.
        """
        return list(self.SECTION_ORDER)

    def has_section(self, section: str) -> bool:
        """Check if a section exists in the registry.

        Args:
            section: Section name to check.

        Returns:
            True if section exists, False otherwise.
        """
        return section in self._settings

    def list_sections(self) -> list[str]:
        """List all available configuration sections.

        Returns:
            List of all section names.
        """
        return list(self._settings.keys())
