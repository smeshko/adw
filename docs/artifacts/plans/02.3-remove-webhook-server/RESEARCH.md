# Research: Remove the webhook server

Curated findings only — no raw conversation transcripts.

## Key Files & Directories

- **Deleted whole** (source / tests):
  - `src/adw/webhook/`: 16 modules, 2,583 LOC. Its tests are `tests/unit/webhook/`, 10 files, 2,652 LOC.
  - `src/adw/server/`: `app.py`, holding `create_app` and `RequestIDMiddleware`, 79 LOC. Its tests are `tests/unit/server/test_app.py`, 148 LOC.
  - `src/adw/models/webhook.py`: `WebhookConfig`, `ProviderConfig`, `WebhookEvent`, `RunParams` and the `Linear*` models, 932 LOC. Its tests are `tests/unit/models/test_webhook_events.py` and `test_webhook_linear.py`, 375 LOC.
  - `src/adw/cli/webhook.py`: `webhook_app`, 145 LOC, 26% covered, with no test file.
  - `src/adw/cli/wizard/webhooks.py`: `WebhooksStepHandler` and `run_webhooks_step`, 355 LOC. Its tests are `tests/unit/cli/wizard/test_webhooks.py`, 551 LOC.
- **Edited** (line numbers as of `be1d5bf8`):
  - `src/adw/cli/app.py:27`: `from adw.cli.webhook import webhook_app`. At `:512-513`: the comment `# Register the webhook subapp (Story 13.1)` and `app.add_typer(webhook_app, name="webhook")`.
  - `src/adw/models/logging.py:87,96`: the `WEBHOOK` docstring bullet and enum member.
  - `src/adw/logging/handler.py:116,129-132`: the docstring bullet and the `elif "webhook" in name_lower` branch, which sits before the `hook` branch. `tests/unit/logging/test_handler.py:83-93` parametrizes the categories and has no webhook row.
  - `src/adw/logging/live_stream.py:61`: `LogCategory.WEBHOOK: "cyan"`.
  - `src/adw/cli/wizard/flow.py:50,78,92`: `WizardStep.WEBHOOKS`, its `STEP_SEQUENCE` entry and its `STEP_TITLES` entry.
  - `src/adw/cli/init.py:171,199`: the `WebhooksStepHandler` import and `register_step_handler(WizardStep.WEBHOOKS, …)`.
  - `src/adw/cli/wizard/__init__.py:26-27,108-111,131,156`: the docstring, import and `__all__` entries.
  - `src/adw/cli/wizard/summary.py:183,274-286`: `webhooks = state.get_step_config("webhooks")` and the "Webhooks:" panel lines.
  - `src/adw/config/yaml_generator.py:127,232-233,327-387`: the state read, the call site, and `_add_webhook_section`. `_format_yaml_value` stays, because 6 other call sites use it.
  - `src/adw/models/config.py:13,557-560`: the import and the `webhook: WebhookConfig` field.
  - `src/adw/models/__init__.py:18,75,143-145`: the docstring, import and `__all__` entries.
  - `src/adw/config/registry.py`:
    - `:63`: `"webhook"` in `SECTION_ORDER`
    - `:97`: the model import
    - `:117-118`: the `webhook` and `webhook_provider` catalog entries
    - `:196-218`: `_extract_webhook_settings`
  - `src/adw/config/checker.py:149-216`: `check_project_config`, with layers existence → syntax → empty → schema → semantics. `data` is the raw `yaml.safe_load` result.
  - `src/adw/dashboard/server.py:19,70-78`: the `_create_base_app` import and call. The module docstring names the shared factory.
  - `src/adw/cli/dashboard_web.py:64-65`: a docstring sentence, shown in `adw dashboard web --help`: "runs independently of the webhook server (port 8000)".
  - `src/adw/core/run_trigger.py:1-5,38-43,46-52`: docstrings naming the webhook, the `project_dir` parameter and `self._project_dir`.
- **Tests that mention the webhook**, outside the deleted files:
  - `tests/unit/cli/wizard/test_flow.py:30`: `"webhooks"` in the expected step list.
  - `tests/unit/cli/wizard/test_summary.py`:
    - `"webhooks"` keys in about 18 state fixtures
    - `:114`: `assert "Webhooks:" in output`
    - `:426-457`: `test_generate_project_yaml_with_webhooks`
  - `tests/unit/config/test_yaml_generator.py`:
    - `:31`: `"webhooks": {}` in a fixture
    - `:123`: `assert "# === Webhook Server ===" in yaml_content`
    - `:520-623`: `TestWebhookFieldEmission`, 4 tests
  - `tests/unit/dashboard/test_server.py:55-60`: `test_health_includes_request_id`.
  - `tests/unit/core/test_run_trigger.py`:
    - `RunTrigger(project_dir=…)` in about 10 places
    - `:67-70`: `test_default_project_dir`
    - `:152-170`: `test_project_path_overrides_default`, which duplicates the `cwd` assertion in `test_successful_start`
- **Docs**:
  - `docs/features/new-run-modal-form-submission.md`: lines 8, 12, 29, 39 and 101 describe the webhook module and `WebhookRunTrigger`.
  - `docs/CONDITIONAL_DOCS.md:119`: "When extracting shared logic from webhook module to core for dashboard use".

## Architecture Facts

- **Importers of `adw.server.app.create_app`**: `webhook/server.py:15` and `dashboard/server.py:19`, nothing else.
- **Importers of `adw.models.webhook`**:
  - `cli/webhook.py:10`, deleted by TASK-001
  - `models/config.py:13`
  - `models/__init__.py:75`
  - `config/registry.py:97`
- **Importers of `adw.webhook.*`** outside the package: none. `core/run_trigger.py` mentions it only in docstrings.
- **`RunTrigger` constructors in `src`**: `dashboard/dependencies.py:166`, which calls `RunTrigger()`, and `webhook/runner.py:70`, which passes `project_dir=`. `_project_dir` is never read.
- **Stale keys.** `ProjectConfig` sets `model_config = {"frozen": False, "validate_assignment": True}` with no `extra`, so Pydantic's default `ignore` applies. The command configs in `models/command.py` use `extra="forbid"`, but those are phase `config.yaml` models, not `project.yaml`.
- **`adw validate`** calls `ConfigChecker.check_all()` or `check_project_config()`. `_get_exit_code` returns 1 on any error, or on any warning under `--strict`. `CheckResult(severity, file_path, message, field, suggestion)` is the finding type, and the existing warnings use `field` for the dotted key.
- **Dashboard lifespan and state.** `create_dashboard_app(host, port)` passes `state={"dashboard_host", "dashboard_port"}` to the base factory. `_dashboard_lifespan` reads those two attributes. `tests/unit/dashboard/test_server.py` asserts them, as well as the title, `/health`, `/` and `/static/htmx.min.js`.
- **The dashboard settings page** has no webhook section. `grep -ri webhook src/adw/dashboard` is empty, and `_SECTION_FIELD_MAP` in `mutations.py` has no webhook entry.
- **This repo's own `.adw/project.yaml`** has only the commented-out `# webhook:` block, so no warning fires for it.

## Constraints

- **Coverage gate 80%**; the baseline is 85.05%. Coverage of the removed modules: `webhook/*` 62–100%, `models/webhook.py` 97%, `server/app.py` 100%, `cli/wizard/webhooks.py` 100%, `cli/webhook.py` 26%.
- **ADR-001**: leave help-text and import-smoke tests unwritten. `adw --help` without `webhook` is shown by transcript, not by a test.
- **The evidence run is `adw run`, started by New Run**, so it goes in a scratch repo with a temp `HOME` (see AGENTS.md).
- **Stage explicitly**, with no `git add -A`. Deleted directories are staged with `git rm -r <path>`.

## Useful Commands

```bash
# pre-epic wizard webhook block (captured at be1d5bf8 via generate_project_yaml)
cat <<'YAML'
name: legacy
language: python
webhook:
  port: 9000
  host: "127.0.0.1"
  providers:
    linear:
      enabled: true
      secret_env: LINEAR_WEBHOOK_SECRET
      command_prefix: /run
      trigger_label: ai
    github:
      enabled: true
      secret_env: GITHUB_WEBHOOK_SECRET
      # command_prefix: "/adw"  # Command prefix
      # trigger_label: adw  # Trigger label
  mappings:
    linear:
      issue.created:
        trigger: true
        require_label: "adw:auto"
YAML

# acceptance greps
grep -rn "adw.webhook\|adw.server\|WebhookConfig" src tests
grep -rni webhook src                        # only src/adw/config/checker.py
grep -rni webhook docs --exclude-dir=artifacts

# partial runs (no coverage gate)
uv run pytest tests/unit/config tests/unit/cli/wizard tests/unit/dashboard/test_server.py tests/unit/core/test_run_trigger.py -o addopts=""
```

## Uncertainty

- **Silent ignore or a warning for a stale `webhook:`?** Resolved: `adw validate` warns and loading stays silent (user's choice).
- **Remove `LogCategory.WEBHOOK` now or in 2.9?** Resolved: now (user's choice).
- **Docs now or in 3.5?** Resolved: now, for the two files that mention webhooks (user's choice).
- **Does the pre-epic wizard write `webhook.enabled`?** No. When enabled, `_add_webhook_section` writes `port`, `host`, `providers` and `mappings` without `enabled`, and when disabled it writes only a commented block. The fixture above reflects that.

## References

- Epic 02, phase 2.3: `docs/artifacts/epics/02-cleanup-remove-and-consolidate.md`
- Linear ADW-19 (sub-issue of ADW-5)
- Baseline suite at `be1d5bf8`: 3817 passed, 5 skipped, 85.05% coverage in 173.6 s
