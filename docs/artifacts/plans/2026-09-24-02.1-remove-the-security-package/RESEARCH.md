# Research: Remove the security package

Curated findings only — no raw conversation transcripts. Line numbers refer to `ad704a17`.

## Key Files & Directories

- `src/adw/security/` — `__init__.py`, `defaults.py`, `interceptor.py`, `override.py`, `patterns.py`, `suggestions.py`. With `models/security.py` and `cli/wizard/security.py`, about 1,580 lines.
- `src/adw/cli/bootstrap.py` — imports `SecurityInterceptor` (L47). `create_orchestrator` takes `allow_dangerous` (L174, docstring L188 and L195), builds the interceptor from `config.security` (L242–252) and passes both to `ClaudeCodeExecutor` (L271–272).
- `src/adw/executors/claude_code.py` — `TYPE_CHECKING` import (L24). `__init__` takes `security_interceptor` and `allow_dangerous` (L52–53, docstring L60–63) and stores them (L68–69). Nothing reads either attribute.
- `src/adw/cli/app.py` — `--allow-dangerous` option on `run` (L192–196), help example (L233–234), passed to `create_orchestrator` (L394).
- `src/adw/exceptions.py` — `SecurityError` is the last class (L189–257). Only `security/interceptor.py` raises it.
- `src/adw/models/config.py` — imports `SecurityConfig` (L12), documents the field (L507) and declares `security: SecurityConfig | None` (L538–540).
- `src/adw/models/__init__.py` — docstring line (L14), import (L68–72), `__all__` entries (L137–140).
- `src/adw/config/registry.py` — `"security"` in `SECTION_ORDER` (L62), catalog entry (L116), `_extract_security_settings` (L186–194).
- `src/adw/config/yaml_generator.py` — fixed commented `# === Security ===` block (L224–230). `generate_project_yaml` never reads the wizard's `security` step.
- `src/adw/cli/wizard/security.py` — `SecurityStepHandler`, `run_security_step`, `validate_regex`, `BUILTIN_BLOCKED_*`. Three prompts: a "configure custom security?" confirm, an "add patterns?" confirm, and a pattern prompt.
- `src/adw/cli/wizard/flow.py` — `WizardStep.SECURITY` (L49), in `STEP_SEQUENCE` (L77) and `STEP_TITLES` (L91).
- `src/adw/cli/init.py` — imports `SecurityStepHandler` (L164) and registers it (L194).
- `src/adw/cli/wizard/__init__.py` — docstring (L22–23), import block (L83–89), `__all__` entries.
- `src/adw/cli/wizard/summary.py` — reads the step (L182) and prints a Security line (L263–272).
- `src/adw/dashboard/settings.py` — `_project_sections` walks `ProjectConfig`'s fields via `_rows`. A `None` model field becomes a `security —` row under Basics; a set one becomes a Security tab. No template mentions security.
- `docs/CONDITIONAL_DOCS.md` — the `docs/architecture/adrs/` entry lists "When modifying dangerous command patterns" and "When implementing security interceptors" (L60–61).

## Tests touched

- Delete: `tests/unit/security/` (6 files), `tests/unit/test_security_error.py`, `tests/unit/test_exceptions.py` (only `TestSecurityError`), `tests/unit/models/test_security.py`, `tests/unit/cli/wizard/test_security.py`.
- Edit:
  - `tests/unit/cli/test_bootstrap.py` — six `mock_project_config.security = None` lines (L82, 155, 200, 238, 281, 317). The mocks use `MagicMock(spec=ProjectConfig)`; the lines existed so bootstrap's `config.security` read returned `None`.
  - `tests/unit/config/test_registry.py` — `test_security_section_exists` (L144–150).
  - `tests/unit/config/test_yaml_generator.py` — `"security": {}` in `MockWizardState` (L30); `"# === Security ==="` asserted present (L121).
  - `tests/unit/cli/wizard/test_flow.py` — `"security"` in the expected step list (L29); `len(STEP_SEQUENCE) == 10` (L62).
  - `tests/unit/cli/wizard/test_summary.py` — `"security": {...}` in about 22 state dicts; `"Security:"` asserted present (L113).
- Add: a `ConfigLoader` test in `tests/unit/config/test_loader.py`, and a dashboard settings-context test in `tests/unit/dashboard/test_settings.py`, both on a `project.yaml` with a legacy `security:` section.

## Architecture Facts

- The package is self-contained. Only `cli/bootstrap.py` and `executors/claude_code.py` (under `TYPE_CHECKING`) import `adw.security`. The package imports only `adw.models.security` and `adw.exceptions.SecurityError`. Removing it strands nothing else.
- `ClaudeCodeExecutor` runs Claude Code with `--dangerously-skip-permissions`; the interceptor was never consulted (B18, D1 in the audit).
- `ProjectConfig.model_config` is `{"frozen": False, "validate_assignment": True}`, so `extra` is pydantic's default `"ignore"`. Unknown top-level keys load silently.
- No script, CI workflow or built-in phase passes `--allow-dangerous`: grep of `scripts/`, `.github/` and `src/adw/defaults/` finds nothing.
- `docs/` outside `artifacts/` has no mention of `SecurityInterceptor`, `SecurityConfig`, `--allow-dangerous` or `blocked_patterns`.

- Baseline at `ad704a17`: 3,581 passed, 5 skipped, coverage 85.34% (`uv run pytest`, 203 s).

## Constraints

- Every commit stays green: ruff, mypy `--strict`, and the tests it touches.
- Keep `logging/redactor.py` and `RedactionConfig`.
- Leave `webhook/security.py` for phase 2.3, and the wizard's structure for phase 2.6.
- The acceptance grep `adw.security` uses `.` as a wildcard. It doesn't match `adw.webhook.security` or `adw/webhook/security.py`, so the webhook's module survives it.

## Useful Commands

```bash
grep -rn --exclude-dir=__pycache__ "SecurityInterceptor\|SecurityConfig\|SecurityError\|allow_dangerous\|adw.security" src tests
uvx vulture src/adw --min-confidence 60 | sed 's/:[0-9]*:/:/' | sort   # diff against the merge-base
uv run pytest tests/unit/cli tests/unit/config tests/unit/models tests/unit/dashboard tests/unit/executors -o addopts=""
```

## Uncertainty

- Whether `adw validate` rejects unknown keys. It validates through `config/checker.py` (`ProjectConfig.model_validate`, L199), which ignores extras like `ConfigLoader` does, so it should not; TASK-004 demonstrates it against a real file.
- Whether the wizard can be driven through stdin end to end. `test_init.py` already feeds `input="c\n"` through `CliRunner`; TASK-004 pipes answers into `adw init --wizard` in a scratch repo, and falls back to `CliRunner` with the same input if Rich prompts reject a pipe.

## References

- Epic: [02 — Cleanup: remove inert features and consolidate](../../epics/02-cleanup-remove-and-consolidate.md), phase 2.1.
- ADR-001: `docs/architecture/adrs/ADR-001-test-reduction-strategy.md`.
