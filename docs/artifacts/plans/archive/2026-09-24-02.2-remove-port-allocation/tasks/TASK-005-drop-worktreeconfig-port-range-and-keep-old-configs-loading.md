# TASK-005: Drop WorktreeConfig.port_range and keep old configs loading

Depends on: TASK-004
Suggested commit: `refactor(config): drop WorktreeConfig.port_range`

## Goal

`WorktreeConfig` has no port settings, and a `project.yaml` that still has `worktree.port_range` loads and keeps its other worktree values.

## Files

- `src/adw/models/config.py`:
  - delete `PortRangeConfig` (`:190-217`)
  - `WorktreeConfig`: drop the `port_range` field (`:258-261`) and the `validate_port_ranges` validator (`:269-316`)
  - `WorktreeConfig` docstring: drop the `port_range` attribute line, the `port_range:` lines in the YAML example, and "(determines slot count)"
  - the `max_concurrent` field description: "(slot count)" goes
  - keep `model_validator` and `Self`, which `RetryConfig` and `ProjectConfig` still use
- `src/adw/models/__init__.py`: drop `PortRangeConfig` from the `adw.models.config` import (`:38`) and from `__all__` (`:101`).
- `src/adw/config/registry.py` (`_build_catalog`):
  - `SECTION_ORDER`: `"ports"` becomes `"worktree"` (`:60`)
  - drop `PortRangeConfig` from the import (`:90`)
  - `self._extract_from_model(WorktreeConfig, skip_nested=["port_range"])` becomes `self._extract_from_model(WorktreeConfig)` (`:111-113`)
  - drop `self._settings["ports"] = ...` (`:114`)
- `tests/unit/models/test_config.py`: delete the port-range tests in `TestWorktreeConfig` (`:54-158`), and add `test_legacy_port_range_is_ignored` in their place. If the class is left empty, replace it with a `TestWorktreeConfig` holding only the new test.
- `tests/unit/config/test_registry.py`: delete `test_ports_section_has_defaults` (`:159-167`).

## Acceptance

- [ ] `_from_yaml` of a `project.yaml` whose `worktree:` block has `max_concurrent: 3` and a `port_range:` with overlapping starts (`backend_start: 9100`, `frontend_start: 9100`) loads without error, and `worktree.max_concurrent == 3`. Before this task that YAML fails with "overlaps", so the test shows the key is really ignored and not just still valid.
- [ ] `grep -rn "PortRange\|port_range\|backend_start\|frontend_start" src` returns nothing, and `grep -rln "PortRange\|port_range\|backend_start\|frontend_start" tests` lists only `tests/unit/models/test_config.py`.
- [ ] `uv run pytest tests/unit/models tests/unit/config tests/unit/dashboard -o addopts=""` passes, and `scripts/preflight.sh` passes.

Evidence: `test_legacy_port_range_is_ignored` failing RED with the "overlaps" `ValidationError`, then passing, plus both greps and the pytest and preflight tails.

## Steps

### RED
- [ ] Add `test_legacy_port_range_is_ignored` to `tests/unit/models/test_config.py`. Write the YAML with `name`, `language` and a `worktree:` block holding `max_concurrent: 3` and a `port_range:` with `backend_start: 9100` and `frontend_start: 9100`. Assert that `_from_yaml` returns a config with `config.worktree.max_concurrent == 3`. Add a comment that this is the pre-2.2 format, and that this file is the one intended match of the plan's `port_range` grep. Don't assert the attribute is gone: ADR-001 lists that as a trivial attribute test.
- [ ] Run it: it fails with a `ValidationError` ("Backend port range … overlaps with frontend port range"), because `validate_port_ranges` still runs.

### GREEN
- [ ] Remove `PortRangeConfig`, the field, the validator and the registry section as listed.
- [ ] Delete the old port-range tests and `test_ports_section_has_defaults`.
- [ ] Run the partial suite: green. `tests/unit/dashboard` confirms the settings page still renders without the `worktree.port_range.*` rows.

### REFACTOR
- [ ] `scripts/preflight.sh` passes.

## Notes

- `test_config.py` imports `WorktreeConfig` only for the tests this task deletes. Drop it from the import if ruff flags it as unused.
- Pydantic's default `extra="ignore"` is what makes the old key load. Neither `WorktreeConfig` nor `ProjectConfig` sets `extra=`, so there's nothing to change for back-compat.
