# Plan: Remove the webhook server

Status: in-progress
Branch: feature/adw-19
Risk: medium
Epic: 02 — Cleanup: remove inert features and consolidate ([epic](../../epics/02-cleanup-remove-and-consolidate.md))
Phase: 2.3 — Remove the webhook server
Linear: ADW-19
Created: 2026-09-23

## Goal

After this phase:

- The webhook server is gone: its package, models, config field, `adw webhook` CLI group, wizard step, generator section, settings-catalog sections and log category.
- The dashboard is the only HTTP app, built on a plain `FastAPI()`.
- A `project.yaml` that still has a `webhook:` section loads without error, and `adw validate` warns that the section is ignored.

## Scope

- **Package and CLI group.** Delete `src/adw/webhook/`, `src/adw/cli/webhook.py` and the `app.add_typer(webhook_app, name="webhook")` registration in `cli/app.py`. Delete `LogCategory.WEBHOOK` and its two consumers:
  - the `"webhook"` branch in `logging/handler.py:_infer_category`
  - the colour entry in `logging/live_stream.py:CATEGORY_COLORS`

  This also removes bugs B6 (Linear accepts unsigned requests) and B7 (GitHub mappings never match).
- **Wizard step.** Delete `cli/wizard/webhooks.py` and remove it from:
  - `WizardStep`, `STEP_SEQUENCE` and `STEP_TITLES` in `cli/wizard/flow.py`
  - the handler registration in `cli/init.py`
  - the re-exports in `cli/wizard/__init__.py`
  - the summary panel in `cli/wizard/summary.py`
  - `_add_webhook_section` in `config/yaml_generator.py`
- **Config.** Delete `ProjectConfig.webhook`, `src/adw/models/webhook.py` and its re-exports in `models/__init__.py`. Delete the `webhook` and `webhook_provider` sections of `config/registry.py`. `config/checker.py` gains `REMOVED_PROJECT_SECTIONS`, so `adw validate` warns once per removed top-level section still present in `project.yaml`.
- **Server factory.** Delete `src/adw/server/`, including `RequestIDMiddleware`. `dashboard/server.py` builds `FastAPI(...)` directly and sets `app.state.dashboard_host`/`dashboard_port` itself. The `adw dashboard web --help` text stops mentioning the webhook server.
- **RunTrigger.** Drop the unused `project_dir` parameter and `_project_dir` attribute from `core/run_trigger.RunTrigger`, and the webhook mentions in its docstrings.
- **Tests.** Delete these:
  - `tests/unit/webhook/`, `tests/unit/server/` and `tests/unit/cli/wizard/test_webhooks.py`
  - `tests/unit/models/test_webhook_events.py` and `test_webhook_linear.py`
  - the webhook cases in `test_flow.py`, `test_summary.py`, `test_yaml_generator.py`, `test_run_trigger.py` and `dashboard/test_server.py`

  Add a back-compat load test and a validate-warning test.
- **Docs.** Remove the webhook mentions in `docs/features/new-run-modal-form-submission.md` and `docs/CONDITIONAL_DOCS.md` (user's choice).

## Out of Scope

- The security (2.1) and port (2.2) removals, although they touch the same wizard, generator, registry and checker files. `REMOVED_PROJECT_SECTIONS` is built so 2.1 can add `security`. 2.2's `worktree.port_range` is nested, so 2.2 extends the lookup.
- Warning about a stale `webhook:` section at run time (`ConfigLoader.load`). Only `adw validate` warns (user's choice).
- The dashboard lifespan banner and the rest of `dashboard/server.py` (phase 2.11).
- `LogCategory` itself, `LogManager` and the handler's other heuristics (phase 2.9).
- The rest of the `docs/features/*` and `CONDITIONAL_DOCS.md` rewrite (phase 3.5).
- A replacement intake mechanism for Linear/GitHub events (epic 08).
- Dependencies: `fastapi`, `uvicorn`, `python-multipart` and `httpx` are all still used by the dashboard or the Linear client.

## Research Summary

See [RESEARCH.md](./RESEARCH.md). In short:

- **Imports.** Nothing outside `src/adw/webhook/` imports `adw.webhook`. `adw.server` has two importers, `webhook/server.py` and `dashboard/server.py`. `adw.models.webhook` has four: `cli/webhook.py`, `models/config.py`, `models/__init__.py` and `config/registry.py`.
- **Stale keys.** `ProjectConfig` has no `extra=` setting, so Pydantic ignores unknown keys, and a leftover `webhook:` section loads silently once the field is gone. `ConfigChecker.check_project_config` holds the raw `data` dict, so it can see removed keys before the schema layer.
- **Request IDs.** Nothing outside the webhook reads `request.state.request_id` or `x-request-id`. The only other reference is the dashboard test `test_health_includes_request_id`.
- **`RunTrigger._project_dir`** is set in `__init__` and never read. `start_run` always uses its `project_path` argument, and `get_run_trigger()` builds `RunTrigger()` with no arguments.
- **The dashboard settings page** shows no webhook section; no template or dashboard module mentions webhooks.
- **Baseline.** `uv run pytest`: 3817 passed, 5 skipped, coverage 85.05% (gate 80%). The removed `src` modules are 62–100% covered, so the gate holds.

## Decisions

- **`adw validate` warns about a removed section; loading stays silent** (user's choice).
  - `REMOVED_PROJECT_SECTIONS: dict[str, str]` in `config/checker.py` maps each removed top-level key to what was removed.
  - The check runs on the raw YAML dict, after the empty-file check and before the schema layer, so the warning appears even when another field is invalid.
  - It is a `WARNING`, so plain `adw validate` exits 0 and `--strict` exits 1.
  - `ConfigLoader.load` is unchanged and ignores the key.
- **Remove `LogCategory.WEBHOOK` here** (user's choice). No module is named `*webhook*` after TASK-001, so the category is unreachable. Removing it lets `grep -rni webhook src` match only `config/checker.py`.
- **Fix the two docs here** (user's choice), rather than leaving them to phase 3.5.
- **`dashboard/server.py` builds `FastAPI()` inline, with no middleware.** The request-ID header served only webhook log correlation. A dashboard-local copy would keep dead code alive.
- **Delete `RunTrigger`'s `project_dir` parameter, not just the attribute.** The parameter exists only to set `_project_dir`, and its one production caller passes nothing.
- **The back-compat fixture is the literal block the pre-epic wizard writes.** It was captured from today's `generate_project_yaml` with Linear and GitHub providers and a mapping (see RESEARCH.md), so the test doesn't depend on the generator it outlives.
- **Task order keeps every commit green.** TASK-001 deletes the importers of `adw.server`, `adw.models.webhook` and `RunTrigger(project_dir=…)`, so TASK-003, TASK-004 and TASK-005 each become a local change.

## Risks

- **Parallel worktrees touch neighbouring lines.**
  - Phase 1.5 (ADW-11) strips `(Story 13.1)` from the `cli/app.py` comment this plan deletes.
  - Phase 2.4 (ADW-20) edits `cli/app.py` registrations.
  - Phases 2.1 and 2.2 later edit the same wizard, generator, registry and checker files.

  Mitigation: each task removes only webhook lines, and none reformats the code around them, so rebases are mechanical.
- **`adw validate --strict` now fails for a project with a leftover `webhook:` section.** This is intended: strict turns warnings into errors. Nothing in `src`, CI or `scripts/` runs `--strict`.
- **The evidence run starts a real `adw run` from the dashboard's New Run**, which creates branches and worktrees in the target project. Mitigation: a temp `HOME` and a scratch git repo registered through `adw register`, with `ADW_MOCK_EXECUTOR=1` exported to the dashboard so the child run inherits it. Never register or target this checkout. Stop the server afterwards.
- **Deleting a Rich wizard step could shift prompt sequences in tests.** No test drives the full wizard. `test_init.py` only cancels with `c\n`, and `test_flow.py` asserts the step list, which TASK-002 updates.

## Acceptance Criteria

- [ ] `uv run adw --help` lists no `webhook` group, and `uv run adw webhook --help` exits non-zero with "No such command". Evidence: both transcripts.
- [ ] `grep -rn "adw.webhook\|adw.server\|WebhookConfig" src tests` returns nothing, and `grep -rni webhook src` matches only `src/adw/config/checker.py`. Evidence: the grep output.
- [ ] `src/adw/webhook/`, `src/adw/server/`, `src/adw/models/webhook.py`, `src/adw/cli/webhook.py` and `src/adw/cli/wizard/webhooks.py` no longer exist. Evidence: `ls` output.
- [ ] A `project.yaml` holding the pre-epic wizard's `webhook:` block loads through `ConfigLoader`, and the loaded config carries no `webhook` key. Evidence: `test_load_ignores_removed_webhook_section`, RED then GREEN.
- [ ] `adw validate` against that `project.yaml` reports 0 errors and one warning on field `webhook`, and exits 0. `--strict` exits 1. Evidence: `test_removed_webhook_section_warns`, RED then GREEN, plus a scratch-repo transcript of both commands.
- [ ] `adw init --wizard` shows no webhook step, and the generated `project.yaml` has no webhook block. Evidence: `test_flow.py` step list and the `test_yaml_generator.py`/`test_summary.py` assertions, RED then GREEN.
- [ ] `adw dashboard web` starts, `curl` of `/` returns 200, and New Run starts a mocked run in a scratch project. Evidence: the curl transcript, a screenshot of the run-started view, and the new run's entry in the scratch `~/.adw` index.
- [ ] `grep -rni webhook docs --exclude-dir=artifacts` returns nothing. Evidence: the grep output.
- [ ] `scripts/preflight.sh` passes, and `uv run pytest` is green with coverage ≥ 80%. Evidence: the tail of both runs.

## Tasks

Task state lives here. Tasks are appended by `scripts/add_task.py` and
`scripts/add_final_task.py`. Update the checkboxes as work progresses.

- [x] TASK-001: Delete the webhook package and the adw webhook command group
- [x] TASK-002: Remove the webhook step from the init wizard
- [x] TASK-003: Drop ProjectConfig.webhook and warn on a leftover webhook section (depends on TASK-001)
- [x] TASK-004: Build the dashboard on a plain FastAPI app (depends on TASK-001)
- [x] TASK-005: Drop RunTrigger's unused project_dir (depends on TASK-001)
- [x] TASK-006: Remove webhook references from the docs (depends on TASK-001,TASK-004,TASK-005)
- [ ] TASK-007: Final Validation
