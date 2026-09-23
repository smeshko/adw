# TASK-003: Drop ProjectConfig.webhook and warn on a leftover webhook section

Depends on: TASK-001
Suggested commit: `refactor(config): drop the webhook config and warn on a leftover section`

## Goal

`ProjectConfig` has no `webhook` field, and `models/webhook.py` is gone. A `project.yaml` written by the pre-epic wizard still loads, and `adw validate` warns that its `webhook:` section is ignored.

## Files

- `src/adw/models/config.py`: drop `from adw.models.webhook import WebhookConfig` (`:13`) and the `webhook` field (`:557-560`).
- `src/adw/models/webhook.py`: delete it.
- `src/adw/models/__init__.py`: drop the docstring line (`:18`), the import (`:75`), and the `# Webhook models`, `"ProviderConfig"` and `"WebhookConfig"` entries in `__all__` (`:143-145`).
- `src/adw/config/registry.py`:
  - drop `"webhook"` from `SECTION_ORDER` (`:63`)
  - drop the `adw.models.webhook` import (`:97`)
  - drop the `webhook` and `webhook_provider` catalog entries (`:117-118`)
  - drop `_extract_webhook_settings` (`:196-218`)
- `src/adw/config/checker.py`:
  - Add a module constant `REMOVED_PROJECT_SECTIONS: dict[str, str] = {"webhook": "the webhook server was removed"}`.
  - Add a private `_check_removed_sections(data, rel_path, report)` that adds one finding per key of `data` present in the map:
    - `severity=Severity.WARNING`
    - `field=<key>`
    - `message=f"'{key}' is no longer used and is ignored: {reason}"`
    - `suggestion=f"Delete the '{key}:' section from project.yaml"`
  - Call it in `check_project_config` after the `data is None` check and before Layer 3 (schema), only when `isinstance(data, dict)`.
- `tests/unit/models/test_webhook_events.py` and `tests/unit/models/test_webhook_linear.py`: delete them.
- `tests/unit/config/test_loader.py`: add `test_load_ignores_removed_webhook_section`.
- `tests/unit/config/test_checker.py`, class `TestConfigCheckerProjectConfig`: add `test_removed_webhook_section_warns`.

## Acceptance

- [ ] `test_load_ignores_removed_webhook_section`: the `ConfigLoader(project_root=tmp_path).load()` call on the pre-epic fixture returns a `ProjectConfig` named `legacy`, and `"webhook" not in config.model_dump()`.
- [ ] `test_removed_webhook_section_warns`: `ConfigChecker(tmp_path).check_project_config()` on the same fixture gives `report.errors == []` and exactly one warning, with `field == "webhook"` and `"ignored"` in its message.
- [ ] `grep -rn "WebhookConfig\|ProviderConfig\|models.webhook\|_extract_webhook_settings" src tests` returns nothing.
- [ ] `uv run pytest tests/unit/config tests/unit/models tests/unit/cli -o addopts=""` passes.

Evidence:
- the RED run: the loader test fails because `model_dump()` has `webhook`, and the checker test fails because it finds no warning
- the GREEN run of both tests
- the grep

## Steps

### RED
- [ ] Put the pre-epic fixture YAML from RESEARCH.md ("Useful Commands") in a module-level constant, `LEGACY_WEBHOOK_PROJECT_YAML`, in each test file. It's a literal string, so neither test depends on the removed generator.
- [ ] Write both tests. Each writes the fixture to `tmp_path / ".adw" / "project.yaml"`.
- [ ] Run them and confirm both fail on today's code, for the reasons under Evidence.

### GREEN
- [ ] Add `REMOVED_PROJECT_SECTIONS` and `_check_removed_sections` to `checker.py`, and call it.
- [ ] Remove the `webhook` field and the import from `models/config.py`, then `git rm src/adw/models/webhook.py tests/unit/models/test_webhook_events.py tests/unit/models/test_webhook_linear.py`.
- [ ] Remove the re-exports in `models/__init__.py` and the webhook parts of `registry.py`.
- [ ] Run the partial suite and confirm it is green.

### REFACTOR
- [ ] Keep `_check_removed_sections` next to `_check_project_semantics`, and give it a docstring that says 2.1 and 2.2 extend the map.
- [ ] `scripts/preflight.sh` passes.

## Notes

- `ProjectConfig` has no `extra=` setting, so Pydantic ignores the key. No model change is needed to accept it.
- Put the warning on the raw dict, not on the validated model. After this task the model has no trace of the key.
- Phase 2.2's leftover key is nested (`worktree.port_range`). The map keeps top-level keys only; 2.2 extends the lookup when it needs dotted paths.
