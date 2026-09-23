"""Read-only settings view.

Builds the Settings page's template context from a project's effective
configuration. Nothing here writes to disk: settings change only when
someone edits ``.adw/project.yaml`` or ``.adw/commands/<phase>/config.yaml``.

Phase values are merged the way ``PhaseRunner`` merges them:

- ``enabled`` comes from the resolved command tier's ``config.yaml``, unless
  the project file sets it explicitly (``is_phase_enabled``).
- ``input_files`` and ``llm`` are the tier's, overlaid key by key by the
  project file's (``_merge_configs_with_project``).
- Phase-specific fields (``lint_command``, ``doc_mappings``, ship
  ``commands``, ``bypass_ci``, ``wait_for_merge``) come from the project
  file only (``_load_project_config``).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ValidationError

from adw.commands.resolver import CommandResolver
from adw.config.loader import ConfigLoader
from adw.core.constants import PHASE_SEQUENCE
from adw.exceptions import ConfigError
from adw.models.command import CommandConfig, PhaseLLMConfig, get_config_class

_LABELS = {"project": "Basics", "llm": "LLM"}


def settings_context(project_root: Path, tab: str) -> dict[str, Any]:
    """Build the read-only settings context for one project.

    Args:
        project_root: Root directory of the registered project.
        tab: Requested tab key; an unknown key falls back to the first tab.

    Returns:
        Dict with ``settings_tabs``, ``active_tab``, ``sections``,
        ``phases``, ``config_error`` and ``has_project_file``.
    """
    loader = ConfigLoader(project_root=project_root)
    sections: dict[str, list[dict[str, Any]]] = {}
    config_error: str | None = None
    try:
        sections = _project_sections(loader)
    except (ConfigError, OSError) as e:
        config_error = str(e)

    settings_tabs = [(key, _label(key)) for key in sections]
    settings_tabs.append(("phases", "Phases"))
    tab_keys = [key for key, _ in settings_tabs]

    return {
        "settings_tabs": settings_tabs,
        "active_tab": tab if tab in tab_keys else tab_keys[0],
        "sections": sections,
        "phases": [_phase(project_root, phase) for phase in PHASE_SEQUENCE],
        "config_error": config_error,
        "has_project_file": loader.has_project_config,
    }


def _label(key: str) -> str:
    return _LABELS.get(key, key.replace("_", " ").title())


def _project_sections(loader: ConfigLoader) -> dict[str, list[dict[str, Any]]]:
    """Group the project config's rows: scalars under Basics, one tab per model."""
    sections: dict[str, list[dict[str, Any]]] = {"project": []}
    for row in _rows(loader.load()):
        head, dot, tail = row["name"].partition(".")
        if dot:
            sections.setdefault(head, []).append({**row, "name": tail})
        else:
            sections["project"].append(row)
    return sections


def _phase(project_root: Path, phase: str) -> dict[str, Any]:
    """Resolve one phase's effective config, or the error a run would hit."""
    sources: list[tuple[str, str]] = []
    entry: dict[str, Any] = {
        "name": phase,
        "label": _label(phase),
        "sources": sources,
        "error": None,
        "rows": [],
    }
    project_path = project_root / ".adw" / "commands" / phase / "config.yaml"
    try:
        command = CommandResolver(project_root).resolve(phase)
        tier = None
        # A project-tier command's config.yaml is the project file itself.
        if command.tier != "project" and command.has_config:
            tier_path = command.path / "config.yaml"
            tier = _load_phase_file(tier_path, phase)
            sources.append((command.tier, str(tier_path)))
        project = None
        if project_path.is_file():
            project = _load_phase_file(project_path, phase)
            sources.append(("project", str(project_path.relative_to(project_root))))
    except (ConfigError, OSError, yaml.YAMLError, ValidationError) as e:
        entry["error"] = str(e)
        return entry
    entry["rows"] = _rows(_merge(phase, tier, project))
    return entry


def _load_phase_file(path: Path, phase: str) -> CommandConfig:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return get_config_class(phase).model_validate(data or {})


def _merge(
    phase: str, tier: CommandConfig | None, project: CommandConfig | None
) -> CommandConfig:
    """Overlay the project config on the tier config by the run's rules."""
    merged = project.model_copy() if project else get_config_class(phase)()
    if tier is None:
        return merged
    if project is None or "enabled" not in project.model_fields_set:
        merged.enabled = tier.enabled
    project_inputs = project.input_files if project else None
    if tier.input_files is not None or project_inputs is not None:
        merged.input_files = {**(tier.input_files or {}), **(project_inputs or {})}
    project_llm = project.llm if project else None
    if tier.llm is not None:
        overrides = project_llm.model_dump(exclude_none=True) if project_llm else {}
        merged.llm = PhaseLLMConfig(
            **{**tier.llm.model_dump(exclude_none=True), **overrides}
        )
    return merged


def _rows(model: BaseModel, prefix: str = "") -> list[dict[str, Any]]:
    """Flatten a config model into rows; nested models get dotted names."""
    rows: list[dict[str, Any]] = []
    for name, field in type(model).model_fields.items():
        value = getattr(model, name)
        if isinstance(value, BaseModel):
            rows.extend(_rows(value, f"{prefix}{name}."))
        else:
            rows.append(
                {
                    "name": f"{prefix}{name}",
                    "lines": _lines(value),
                    "description": field.description or "",
                }
            )
    return rows


def _lines(value: Any) -> list[str]:
    """Render a value as display lines: one per dict entry or list item."""
    if isinstance(value, dict):
        return [f"{k}: {_inline(v)}" for k, v in value.items()] or ["{}"]
    if isinstance(value, list):
        return [_inline(v) for v in value] or ["[]"]
    return [_inline(value)]


def _inline(value: Any) -> str:
    """Render a value on one line."""
    if value is None:
        return "—"
    if isinstance(value, bool):
        return str(value).lower()
    if isinstance(value, BaseModel):
        value = value.model_dump()
    if isinstance(value, dict):
        return ", ".join(f"{k}: {_inline(v)}" for k, v in value.items())
    if isinstance(value, list):
        return ", ".join(_inline(v) for v in value)
    return str(value)
