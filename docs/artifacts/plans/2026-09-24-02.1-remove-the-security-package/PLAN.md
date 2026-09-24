# Plan: Remove the security package

Status: done
Branch: feature/adw-17
Risk: medium
Epic: 02 — Cleanup: remove inert features and consolidate ([epic](../../epics/02-cleanup-remove-and-consolidate.md))
Phase: 2.1 — Remove the security package
Linear: ADW-17
Created: 2026-09-24

## Goal

No configuration surface claims to block commands that nothing actually blocks. The inert `SecurityInterceptor`, its config, the `--allow-dangerous` flag, the wizard's security step and every test of them are gone, and an old `project.yaml` with a `security:` section still loads.

## Scope

- Delete `src/adw/security/` (6 modules) and `tests/unit/security/` (6 files).
- Delete `SecurityError` from `src/adw/exceptions.py`, with `tests/unit/test_security_error.py` and `tests/unit/test_exceptions.py` (which tests only `SecurityError`).
- Remove the runtime wiring:
  - the `SecurityInterceptor` import and construction in `cli/bootstrap.py`, and `create_orchestrator`'s `allow_dangerous` parameter
  - `ClaudeCodeExecutor`'s `security_interceptor` and `allow_dangerous` parameters and attributes
  - the `--allow-dangerous` option of `adw run` and its help example
- Remove the config surface:
  - `ProjectConfig.security`, `src/adw/models/security.py` (`BlockedPattern`, `SecurityConfig`, `ToolCallLog`) and their `adw.models` re-exports
  - the `security` section in `config/registry.py` and the commented `# === Security ===` block in `config/yaml_generator.py`
  - the dashboard settings page's security row or tab, which disappears with the field because `dashboard/settings.py` walks `ProjectConfig`'s fields
- Remove the wizard step: `cli/wizard/security.py`, `WizardStep.SECURITY` and its sequence and title entries, its registration in `cli/init.py`, its re-exports in `cli/wizard/__init__.py`, and the Security line of the summary panel.
- Delete the stale "security interceptors" and "dangerous command patterns" conditions in `docs/CONDITIONAL_DOCS.md`.

## Out of Scope

- `logging/redactor.py` and `RedactionConfig`. They are separate and they work.
- `src/adw/webhook/security.py` and `tests/unit/webhook/test_security.py`: webhook signature checks, removed with the webhook server in phase 2.3.
- Real enforcement, such as a generated Claude Code PreToolUse hook. The epic calls that a new feature for a new epic.
- The wizard's structure (`WizardFlowController`, `WizardStep`, `STEP_TITLES`). Phase 2.6 replaces it; this phase only drops one step from it.
- `config/registry.py`'s other sections and its rename. Phase 2.8 does that.
- A deprecation warning for a leftover `security:` key, or a stub for `--allow-dangerous`.
- Historical docs: ADR-001 and `docs/testing/TEST_REDUCTION_PLAN.md` describe the test suite at the time they were written. Epic 03 sweeps the rest of `docs/`.

## Research Summary

See [RESEARCH.md](RESEARCH.md). In short:

- **Inert.** Nothing calls the interceptor's check. `ClaudeCodeExecutor` stores `security_interceptor` and `allow_dangerous` and never reads them, and every run passes `--dangerously-skip-permissions`.
- **Self-contained.** Only `cli/bootstrap.py` and `executors/claude_code.py` import `adw.security`. The package imports only `adw.models.security` and `adw.exceptions.SecurityError`. Nothing else becomes dead.
- **Wizard answers were never written.** `yaml_generator.generate_project_yaml` never reads the wizard's `security` step; it prints a fixed commented block. Only the summary panel reads those answers.
- **Legacy keys are ignored.** `ProjectConfig` uses pydantic's default `extra="ignore"`, so a `security:` section left in `project.yaml` loads once the field is gone.
- **Dashboard.** `dashboard/settings.py` builds its sections from `ProjectConfig`'s fields. Removing the field removes the Security tab (or the `security —` row under Basics) with no dashboard edit.

## Decisions

- **Ignore a leftover `security:` section silently.** Pydantic's default drops it. A warning would be new code to delete later, and phases 2.2 and 2.3 leave `port_range` and `webhook` behind the same way.
- **Remove `--allow-dangerous` outright.** Typer then fails with "No such option" and exits 2. No script, workflow or built-in phase passes it (grep of `scripts/`, `.github/`, `src/adw/defaults/`). Phase 2.4 made the same call for `adw global dashboard`.
- **Three commits, each green:**
  1. TASK-001: the package, `SecurityError` and the runtime wiring. They go together because the interceptor raises `SecurityError`, and bootstrap is its only constructor.
  2. TASK-002: the config model and its surfaces (registry, generator, dashboard). This depends on TASK-001, because bootstrap reads `config.security` until then.
  3. TASK-003: the wizard step, which touches only `cli/wizard/`, `cli/init.py` and their tests.
- **Tests that pin the new behaviour, not trivia.** ADR-001 rules out smoke tests, so the RED steps are:
  - a legacy `security:` section loads through `ConfigLoader`, and is absent from the dumped config (TASK-002)
  - the dashboard settings context for such a project has no security section or row (TASK-002)
  - the generated `project.yaml` and the wizard summary panel no longer mention Security (flipped asserts in TASK-002 and TASK-003)
- **`tests/unit/test_exceptions.py` goes entirely.** Its only class is `TestSecurityError`, and `test_security_error.py` duplicates it.

## Risks

- **A lazy or `TYPE_CHECKING` import still reaches `adw.security`.** Mitigation: `claude_code.py` has one under `TYPE_CHECKING`; TASK-001 removes it, and mypy `--strict` plus the acceptance grep catch any other.
- **A test asserts the wizard's step count or step list.** `test_flow.py` does both (`test_step_values_exist`, `test_step_sequence_defined`). They are enum-existence tests, which ADR-001 classifies as waste, so TASK-003 deletes them instead of editing them.
- **Coverage drops below 80%.** Code leaves with its tests. The security package is well covered, so the total may dip by a fraction of a point. TASK-004 runs the full suite with the gate.
- **`adw validate` checks keys more strictly than `ConfigLoader`.** TASK-004 runs it against a `project.yaml` with a `security:` section.

## Acceptance Criteria

Every CLI check runs the code in this worktree: `uv run --project "$WORKTREE" adw …`, never the `adw` on `PATH`, which is installed from another checkout.

- [x] `grep -rn --exclude-dir=__pycache__ "SecurityInterceptor\|SecurityConfig\|SecurityError\|allow_dangerous\|allow-dangerous\|security_interceptor\|adw\.security" src tests` returns nothing, and so does the epic's literal phase-2.1 grep once stale `__pycache__` dirs are cleared. Evidence: both empty greps.
- [x] A `project.yaml` that still has a `security:` section loads without error: a unit test, and `adw validate` in a scratch project. Evidence: the pytest line and the `adw validate` transcript.
- [x] `adw init --wizard` asks no security questions. Evidence: a transcript of the wizard in a scratch repo, fed on stdin, with no "Security" prompt or summary line.
- [x] The dashboard settings page renders without a security section. Evidence: a unit test, and a screenshot of the settings page for a project whose `project.yaml` has a `security:` section.
- [x] `adw run --allow-dangerous` fails with "No such option". Evidence: the transcript.
- [x] `uvx vulture src/adw --min-confidence 60`, diffed against the merge-base, reports no new entry. Evidence: the empty diff.
- [x] `scripts/preflight.sh` passes, and `uv run pytest` is green with coverage ≥ 80%. Evidence: the preflight output and the pytest summary line.

## Tasks

Task state lives here. Tasks are appended by `scripts/add_task.py` and
`scripts/add_final_task.py`. Update the checkboxes as work progresses.

- [x] TASK-001: Delete the security package and its runtime wiring
- [x] TASK-002: Remove the security config section (depends on TASK-001)
- [x] TASK-003: Remove the wizard security step (depends on TASK-002)
- [x] TASK-004: Final Validation
