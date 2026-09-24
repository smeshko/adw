# TASK-002: Remove the security config section

Depends on: TASK-001
Suggested commit: `refactor(config): drop the security config section`

## Goal

`ProjectConfig` has no `security` field, so the settings catalog, the generated `project.yaml` and the dashboard settings page show no security section. A `project.yaml` that still has a `security:` section loads, and the section is ignored.

## Files

- `src/adw/models/security.py`: delete (`PatternCategory`, `BlockedPattern`, `SecurityConfig`, `ToolCallLog`).
- `src/adw/models/config.py`: delete the `SecurityConfig` import (L12), the `security:` docstring line (L507) and the `security` field (L538–540).
- `src/adw/models/__init__.py`: delete the `- security: ...` docstring line (L14), the `from adw.models.security import (...)` block (L68–72), and the `# Security models` comment and its three `__all__` entries (L137–140).
- `src/adw/config/registry.py`: delete `"security"` from `SECTION_ORDER` (L62), the `self._settings["security"] = ...` line (L116) and `_extract_security_settings` (L186–194).
- `src/adw/config/yaml_generator.py`: delete the `# === Security ===` block (L224–228) and the `lines.append("")` that follows it (L230), so one blank line still separates the LLM and Webhook sections.
- `tests/unit/models/test_security.py`: delete.
- `tests/unit/config/test_registry.py`: delete `test_security_section_exists` (L144–150).
- `tests/unit/config/test_yaml_generator.py`: delete `"security": {}` from `MockWizardState` (L30); change `assert "# === Security ===" in yaml_content` (L121) to `not in`.
- `tests/unit/config/test_loader.py`: add `test_load_ignores_legacy_security_section` to `TestConfigLoader`.
- `tests/unit/dashboard/test_settings.py`: add `test_legacy_security_section_is_not_shown` to `TestSettingsContext`.

## Acceptance

- [ ] `grep -rn --exclude-dir=__pycache__ "SecurityConfig\|BlockedPattern\|ToolCallLog\|models.security\|_extract_security" src tests` returns nothing.
- [ ] The new loader test passes: a `project.yaml` with a `security:` section (a `blocked_patterns` list of pattern dicts and a `blocked_env_files` list) loads through `ConfigLoader`, and `"security"` is not in `config.model_dump()`.
- [ ] The new dashboard test passes: `settings_context` for a project whose `project.yaml` has a `security:` section has no `"security"` key in `sections`, and no row named `security` under `sections["project"]`.
- [ ] `scripts/preflight.sh` passes.
- [ ] `uv run pytest tests/unit/config tests/unit/models tests/unit/dashboard tests/unit/cli -o addopts=""` passes.

Evidence: the empty grep, the preflight output and the pytest summary line, plus the RED run of the two new tests before the field goes.

## Steps

### RED
- [ ] Add `test_load_ignores_legacy_security_section` to `tests/unit/config/test_loader.py`. Write the file with `name`, `language` and:
  ```yaml
  security:
    blocked_patterns:
      - pattern: "rm -rf"
        description: "Recursive delete"
        category: destructive
    blocked_env_files:
      - '\.secrets$'
  ```
  Assert `ConfigLoader(project_root=tmp_path).load()` succeeds, `config.name` is read, and `"security" not in config.model_dump()`.
- [ ] Add `test_legacy_security_section_is_not_shown` to `TestSettingsContext` in `tests/unit/dashboard/test_settings.py`. Append the same `security:` block to the fixture project's `project.yaml`, call `settings_context(project, "project")`, and assert `"security" not in ctx["sections"]`, `"security" not in _values(ctx["sections"]["project"])` and `ctx["config_error"] is None`.
- [ ] Flip the `# === Security ===` assertion in `test_yaml_generator.py` to `not in`.
- [ ] Run the three tests and confirm they fail: the field is still on the model, so the dump has `security`, the dashboard shows a Security tab, and the generator prints the block.

### GREEN
- [ ] `git rm src/adw/models/security.py tests/unit/models/test_security.py`.
- [ ] Edit `models/config.py`, `models/__init__.py`, `config/registry.py` and `config/yaml_generator.py` as listed in Files.
- [ ] Delete `test_security_section_exists` and the `"security": {}` mock key.
- [ ] Run the targeted pytest command from Acceptance.

### REFACTOR
- [ ] Check the `ProjectConfig` docstring's attribute list still reads in field order.
- [ ] Run `scripts/preflight.sh` and the grep from Acceptance.

## Notes

- Line numbers refer to `ad704a17`.
- The dashboard needs no code change: `dashboard/settings.py` builds its sections from `ProjectConfig`'s fields.
- `ProjectConfig` keeps pydantic's default `extra="ignore"`. Don't add `extra="forbid"`; it would break every old config with any removed section.
