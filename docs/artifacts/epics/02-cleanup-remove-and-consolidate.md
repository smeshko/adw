# Epic 02 — Cleanup: remove inert features and consolidate

Status: planned
Created: 2026-09-23
Depends on: Epic 01
Project: none
Linear: ADW-5 (https://linear.app/ivo-tsonev/issue/ADW-5)
Milestone: none

## Overview

Second third of the codebase simplification. It first removes features that do nothing or duplicate something else:

- security checks that never run
- port allocation that nothing wires up
- the webhook server
- the terminal dashboard
- editing settings from the web dashboard
- the wizard's back/forward machinery

It then consolidates what remains, so each shared concern has one implementation: git calls, formatting, run paths and status, config loading, logging, ticket sync, dashboard helpers and CLI error handling. Each phase is sized to land as one small-to-medium pull request, driven by a single plan under `../plans/`.

## Architecture references

- [AGENTS.md](../../../AGENTS.md): architecture notes that phases 2.1–2.8 change (config hierarchy, packages).
- [Settings page config viewing](../../features/settings-page-config-viewing.md): the read-only view that phase 2.5 keeps.
- [Phase config editor](../../features/phase-config-editor.md), [Complex field editors](../../features/complex-field-editors-task-manager-security.md), [Reset defaults & changed indicators](../../features/reset-defaults-changed-indicators-validation.md): the editing features phase 2.5 removes.
- [Dashboard design system](../../design-system-brutalist.md): styles phase 2.11 trims.
- [PhaseRunner deep dive](../../architecture/deep-dive/phase-runner.md): config merging, which phase 2.8 simplifies.
- [Simplification audit report](https://claude.ai/artifact/P59fUpiUcp7rATwMUSjjmp) (private): findings and evidence. Bug IDs `B*` and decision IDs `D1`–`D6` refer to it.

## Dependencies

- Epic 01: tests must be isolated and dead code gone before features are removed. Phase 1.9 must land before 2.7 and 2.8, because it removes the shell hooks that import `adw.hooks.git_*` and `adw.config.ConfigLoader`.

## Out of scope

- Restructuring the run loop (orchestrator, lifecycle, resume, interrupts, extensions): Epic 03.
- Replacing the security package with real enforcement, such as a generated Claude Code PreToolUse hook. That would be a new feature and a new epic.
- Renaming CLI commands. Commands are removed or merged here, but surviving names stay stable.
- Rewriting the BMAD-derived workflow prompts.

## Phase 2.1 — Remove the security package

**Plan**: [02.1-remove-the-security-package](../plans/archive/2026-09-24-02.1-remove-the-security-package/PLAN.md) · status: done

**Linear**: ADW-17 (https://linear.app/ivo-tsonev/issue/ADW-17)

**Goal**: No configuration surface claims to block commands that nothing actually blocks.

### What to build

- Delete `src/adw/security/` (all of it), `src/adw/models/security.py`, the `ProjectConfig.security` field and `SecurityError`. Nothing ever calls the interceptor's check, and every run passes `--dangerously-skip-permissions` (B18, D1).
- Remove the wiring:
  - the `SecurityInterceptor` construction in `cli/bootstrap.py`
  - the `security_interceptor` parameter of `ClaudeCodeExecutor`
  - the `--allow-dangerous` flag and the `allow_dangerous` plumbing
- Remove the config surfaces:
  - `cli/wizard/security.py` and its wizard step
  - the security sections in `config/yaml_generator.py` and `config/registry.py`
  - the dashboard security display and editor
- Keep `logging/redactor.py` and `RedactionConfig`. They are separate, and they work.
- Delete `tests/unit/security/*`, `test_security_error.py` and `cli/wizard/test_security.py`, plus the security cases in the dashboard and YAML-generator tests.

### Acceptance criteria

- [x] `grep -rn "SecurityInterceptor\|SecurityConfig\|SecurityError\|allow_dangerous\|adw.security" src tests` returns nothing.
- [x] A `project.yaml` that still has a `security:` section loads without error.
- [x] `adw init --wizard` asks no security questions.
- [x] The dashboard settings page renders without a security section.
- [x] Lint and tests pass.

### Validation

Include `adw validate` against a copy of a `project.yaml` that has a `security:` section, an `adw init --wizard` transcript, and a screenshot of the settings page in the PR.

---

## Phase 2.2 — Remove port allocation

**Plan**: [02.2-remove-port-allocation](../plans/02.2-remove-port-allocation/PLAN.md) · status: planned

**Linear**: ADW-18 (https://linear.app/ivo-tsonev/issue/ADW-18)

**Goal**: Port allocation, which nothing wires up, is gone from code, config, wizard and run listings.

### What to build

- Delete the modules: `worktree/ports.py`, `cli/wizard/ports.py` and its wizard step, and `models/worktree.py`, which holds only `PortAllocation`.
- Remove the config: `PortRangeConfig`, `WorktreeConfig.port_range`, and the `PORT_ALLOCATION_*` error codes.
- Remove the port code from the hooks: the `port_allocation` parameter in `hooks/runner.py`, and the ports and `.ports.env` handling in `hooks/environment.py`.
- Remove the port fields on `ActiveRun` and the port columns in `adw list --running`.
- Remove the ports sections from the YAML generator, the settings catalog and the dashboard settings view.
- Keep `max_concurrent`: `ConcurrentRunManager` uses it.
- Delete `tests/unit/worktree/test_ports.py` and `tests/unit/cli/wizard/test_ports.py`, plus the port cases in `test_environment.py`.

### Acceptance criteria

- [ ] `grep -rn "PortAlloc\|port_range\|ports.env" src tests` returns nothing.
- [ ] `adw list --running` shows no port columns.
- [ ] A `project.yaml` that still has `worktree.port_range` loads without error.
- [ ] `max_concurrent` is still enforced: a second run past the limit is refused.
- [ ] Lint and tests pass.

### Validation

Include `adw list --running` output with one mocked run active, and the `adw validate` output against an old config, in the PR.

---

## Phase 2.3 — Remove the webhook server

**Plan**: _not yet created_

**Linear**: ADW-19 (https://linear.app/ivo-tsonev/issue/ADW-19)

**Goal**: The webhook server and its config, models, CLI and wizard step are gone, leaving the dashboard as the only HTTP app.

### What to build

- Delete these modules: `src/adw/webhook/` (all of it), `src/adw/models/webhook.py`, `cli/webhook.py`, and `cli/wizard/webhooks.py`.
- Delete `src/adw/server/`, the shared base app factory. Its only feature, `RequestIDMiddleware`, served the webhook. `dashboard/server.py` builds a plain `FastAPI()` instead.
- Remove the config and wiring:
  - the `ProjectConfig.webhook` field
  - the `adw webhook` command group registration
  - the wizard step
  - the webhook sections in the YAML generator and settings catalog
- Keep `core/run_trigger.RunTrigger`, which the dashboard's New Run uses. Drop its unused `_project_dir`.
- Removing the code also removes bugs B6 (Linear accepts unsigned requests) and B7 (GitHub mappings never match).
- Delete `tests/unit/webhook/**`, `tests/unit/server/` and `tests/unit/cli/wizard/test_webhooks.py`, plus the webhook cases in other tests.

### Acceptance criteria

- [ ] `adw --help` lists no `webhook` group.
- [ ] `grep -rn "adw.webhook\|adw.server\|WebhookConfig" src tests` returns nothing.
- [ ] A `project.yaml` with a `webhook:` section loads without error.
- [ ] `adw dashboard web` starts, the overview page returns 200, and New Run starts a mocked run.
- [ ] Lint and tests pass.

### Validation

Include `adw --help`, a curl of the dashboard overview, and a screenshot of a run started from the New Run modal in the PR.

---

## Phase 2.4 — Remove the terminal dashboard

**Plan**: [02.4-remove-terminal-dashboard](../plans/archive/2026-09-23-02.4-remove-terminal-dashboard/PLAN.md) · status: done

**Linear**: ADW-20 (https://linear.app/ivo-tsonev/issue/ADW-20)

**Goal**: The web dashboard is the only dashboard.

### What to build

- Delete `cli/dashboard.py`, the Rich/termios TUI of 1,097 LOC (D4). Delete the `adw global dashboard` command in `cli/global_commands.py`, and any hints that point to it.
- Delete `tests/unit/cli/test_dashboard.py` and `tests/integration/cli/test_dashboard_integration.py`, which contains the known flaky `test_stats_display_with_real_data`. Also delete the TUI references in `test_global_commands.py`.
- Remove the flaky-test gotcha from `AGENTS.md`.

### Acceptance criteria

- [x] `adw global --help` lists no `dashboard`.
- [x] `adw dashboard web` is unaffected.
- [x] `grep -rn "cli.dashboard import\|cli/dashboard.py\|test_stats_display_with_real_data" src tests AGENTS.md` returns nothing.
- [x] Lint and tests pass.

### Validation

Include `adw global --help` and a full-suite pass in the PR.

---

## Phase 2.5 — Make dashboard settings read-only

**Plan**: [02.5-make-dashboard-settings-read-only](../plans/archive/2026-09-23-02.5-make-dashboard-settings-read-only/PLAN.md) · status: done

**Linear**: ADW-21 (https://linear.app/ivo-tsonev/issue/ADW-21)

**Goal**: The settings page shows configuration without editing it, so it can no longer lose data on save.

### What to build

- Delete the editing path (D2, B15):
  - in `dashboard/mutations.py`: `save_settings`, `save_phase_settings`, `_render_*_error`, the form parsers, `_atomic_write_config` and `_SECTION_FIELD_MAP`
  - the `task_manager_fields` and `phase_config_partial` routes
  - reset-to-defaults and changed indicators
  - the templates `settings_phase_editor.html` and `settings_task_manager_fields.html`, and the form controls in `settings_content.html`
- Replace the four places that build settings context with one read-only `settings_context(project)` that shows effective project and per-phase values.
- Delete the dead `_build_phase_settings`, `has_project_config` and the `PHASE_DEFAULTS` copy.
- Keep the CSRF protection that New Run and Abort still use.
- Delete the edit tests in `tests/dashboard/test_settings_{save,phase,indicators}.py`. Move the remaining `test_settings_route.py` into `tests/unit/dashboard/` and delete the top-level `tests/dashboard/` package.

### Acceptance criteria

- [x] The settings page renders every remaining section for this repo's `.adw` config.
- [x] The only POST routes left are run start and abort. List them from `app.routes`.
- [x] Visiting every settings view leaves `.adw/project.yaml` and `.adw/commands/*/config.yaml` byte-identical.
- [x] `tests/dashboard/` no longer exists.
- [x] Lint and tests pass.

### Validation

Include screenshots of the settings page, the route list from `app.routes`, and `shasum` of the config files before and after browsing the settings views, in the PR.

---

## Phase 2.6 — Collapse the init wizard into a straight sequence

**Plan**: _not yet created_

**Linear**: ADW-22 (https://linear.app/ivo-tsonev/issue/ADW-22)

**Goal**: adw init asks its questions in one plain sequence and reports honestly whether files were written.

### What to build

- Replace `WizardFlowController`, the `WizardStep` enum, `STEP_TITLES`, `WizardState` (`models/wizard.py`) and the 11 `*StepHandler` classes with one `run_wizard(root)`. It calls the remaining `run_*_step(console)` functions in order, collects a dict, and hands it to the summary and YAML generator (`cfg.get(section, {})`).
- Delete `cli/wizard/navigation.py`, whose back/cancel works in only one of about 70 prompts, and `cli/wizard/ship.py`, which is only re-exported. Trim the 165-line re-export list in `cli/wizard/__init__.py`.
- Drop the retry step, `cli/wizard/retry.py` (D5). The retry defaults stay on `RetryConfig` and are written as comments by the generator.
- Summary:
  - Print "files written" only after a successful write.
  - On cancel or failure, say so and exit non-zero.
  - Remove the back/cancel promise from the welcome panel.
- `wizard/basics.py` uses `config/detector.ProjectTypeDetector` instead of its own copies (`LANGUAGE_MARKERS`, `detect_language`, `detect_test_command`), which have drifted.
- Either write the ship "Build command" answer to `project.yaml` or stop asking for it.

### Acceptance criteria

- [ ] `adw init --wizard` in a scratch repo, accepting the defaults, produces files that `adw validate` accepts.
- [ ] Cancelling at the summary writes no files, prints that nothing was written, and exits non-zero.
- [ ] `grep -rn "WizardFlowController\|WizardState\|StepHandler\|nav_prompt_ask" src tests` returns nothing.
- [ ] Lint and tests pass.

### Validation

Include both transcripts (accept and cancel) from a scratch repo, driven by a test that feeds stdin, in the PR.

---

## Phase 2.7 — One home for git, formatting, paths and run status

**Plan**: _not yet created_

**Linear**: ADW-23 (https://linear.app/ivo-tsonev/issue/ADW-23)

**Goal**: Each shared primitive — git calls, formatting, run paths, run status — has exactly one implementation.

### What to build

- `src/adw/git.py`:
  - One `git(*args, cwd, check=False, timeout=60)` plus the commit, diff and branch helpers now spread across `hooks/git_branch.py`, `hooks/git_commit.py`, `hooks/git_diff.py` and `worktree/branch.py`. Delete those four modules.
  - Route every other `git` and `gh` call through it. Today there are 36 `subprocess.run` sites in 10 files, and only two set timeouts, so `git pull` and `git fetch` can hang.
- `src/adw/format.py`: one formatter each for duration, tokens, relative time, cost and file size, and one status→style map. Today there are 9 duration formatters in 4 styles and 5 status→colour maps that disagree. The CLI modules, `task_managers/comments.py` and the dashboard use it; the dashboard registers the formatters as Jinja filters.
- A `RunStatus` StrEnum in `models/context.py`, used by `RunContext`, `IndexEntry` and every CLI and dashboard status set. `PHASE_SEQUENCE` replaces the 4 hand-written phase lists.
- One `atomic_write(path, text)`, used by the context, snapshot and artifact managers and the wizard summary.
- The single `runs_dir()` helper from 1.8 replaces `bootstrap.get_runs_dir`, `logs._get_runs_dir` and `list._get_runs_dir`. Only `adw run` creates the directory, so read-only commands stop creating `.adw/runs` in whatever directory they run from.

### Acceptance criteria

- [ ] `grep -rnE 'subprocess\.(run|Popen)\(\s*\[\s*"(git|gh)"' src` matches only `src/adw/git.py`.
- [ ] Each formatter and the status-style map is defined exactly once; checked with grep and listed in the PR.
- [ ] A `git fetch` through the helper against a fake `git` that sleeps times out and raises instead of hanging.
- [ ] `adw status` in a directory without `.adw` exits with an error and creates nothing.
- [ ] Lint and tests pass.

### Validation

Include the greps, the timeout test, and `adw list` / `adw status` output showing identical colours for every status, in the PR.

---

## Phase 2.8 — One config loading path

**Plan**: _not yet created_

**Linear**: ADW-24 (https://linear.app/ivo-tsonev/issue/ADW-24)

**Goal**: Project and phase config are each loaded by one function with one set of error rules.

### What to build

- Put `load_command_config(path, phase, *, strict)` next to `get_config_class` in `models/command.py`. It replaces the five remaining read sites:
  - `PhaseRunner._load_command_config`
  - `PhaseRunner._load_project_config`
  - the ship extension's loader
  - `cli/dry_run.py`, which uses the base class and drops phase-specific fields
  - `dashboard/settings.py` (`_phase`), which also copies `PhaseRunner`'s tier-merge rules (moved there by phase 2.5)
- `PhaseRunner` caches loaded configs per instance. Project config is parsed once per run, not 3 times per phase plus 5 more in bootstrap.
- Fold `PhaseConfig` into `CommandConfig`. Its docstring documents a `phases:` key that doesn't exist. Merge `lint_command`, `doc_mappings` and the ship commands by the same rule as `enabled`, `input_files` and `llm`, and document that rule.
- Replace the `ConfigLoader` class with a `load_project_config(root)` function.
- `config/yaml_generator.py`: drop the registry parameter it never reads and `_format_setting_as_comment`, and read defaults from the models rather than hard-coding them.
- Rename `config/registry.py` to `settings_catalog.py`, and drop the sections and methods nothing reads. Since phase 2.5, only tests call `get_all_settings` and `get_phase_settings`.
- `config/checker.py`: one helper replaces the 6 copies of the "executable on PATH" check.

### Acceptance criteria

- [ ] In a full mocked run, `project.yaml` is parsed once and each phase `config.yaml` once. A spy on `yaml.safe_load` asserts this.
- [ ] `adw run --dry-run` shows phase-specific fields, such as the validate phase's `lint_command`, that it drops today.
- [ ] A malformed phase config still fails with `INVALID_CONFIG`, and a malformed `project.yaml` with `INVALID_PROJECT_CONFIG`.
- [ ] `grep -rn "PhaseConfig\b\|class ConfigLoader" src` returns nothing.
- [ ] `dashboard/settings.py` reads phase configs through `load_command_config`. `grep -rn "yaml.safe_load\|model_validate" src/adw/dashboard` returns nothing.
- [ ] Lint and tests pass.

### Validation

Include the spy test, `adw run --dry-run` output before and after, and both error transcripts, in the PR.

---

## Phase 2.9 — Logging on stdlib with a redaction filter

**Plan**: _not yet created_

**Linear**: ADW-25 (https://linear.app/ivo-tsonev/issue/ADW-25)

**Goal**: Log records go through stdlib logging with one redaction filter, and -v shows DEBUG.

### What to build

- Delete `logging/manager.py` (`LogManager`), `logging/handler.py` (`LogManagerHandler`), the `Transport` protocol, and `LogEvent`, `LogContext` and `LogCategory` in `models/logging.py`. Keep `Verbosity`.
- Add a `setup_logging(verbosity, run_dir)` that attaches three things to the `adw` logger:
  - a Rich console handler that keeps the spinner-stop behaviour of `set_active_live`
  - one `live.log` handler per run (`bootstrap.py` builds two writers today)
  - a redacting `logging.Filter` that wraps `Redactor`
- Send LLM text and tool-call lines written to `live.log` through the redactor too. They skip it today.
- Write `live.log` timestamps in UTC, like everything else.
- Delete the docstrings that describe `logs.jsonl` and `StructuredFileTransport`, which don't exist. Delete `Redactor.redact_dict` and `_redact_list` if only tests use them.

### Acceptance criteria

- [ ] `adw run -v --dry-run "x"` prints DEBUG lines (B8).
- [ ] A value matching a redaction pattern, emitted in mocked LLM output, appears as `[REDACTED]` in `live.log`.
- [ ] Exactly one writer holds `live.log` during a run, and the per-line file lock is gone.
- [ ] `logging/` contains only `redactor.py`, `console.py`, `live_stream.py` and the setup function.
- [ ] Lint and tests pass.

### Validation

Include the `-v` output and an excerpt of `live.log` from a mocked run with a planted secret in the PR.

---

## Phase 2.10 — Collapse task-manager layers

**Plan**: _not yet created_

**Linear**: ADW-26 (https://linear.app/ivo-tsonev/issue/ADW-26)

**Goal**: Ticket updates live in one Linear manager and one TicketSync, with errors handled once.

### What to build

- Replace `task_managers/factory.py` with a `create_task_manager(config)` function. Inline `task_managers/resolver.py` (`InputResolver`, `ResolvedInput`, `InputType`) into its single caller in `cli/app.py`.
- Merge `linear_client.py` into `linear.py`: one `LinearTaskManager` with a private `_gql()` that raises `TaskError`, one label-id lookup, and both caches in one place.
- Replace `sync.py` (`StatusSyncService`) and `labels.py` (`LabelManager`) with `ticket_sync.py`. Its `TicketSync` has `on_run_start`, `on_phase_start`, `on_phase_complete`, `on_run_failed` and `on_run_complete`, each updating status, labels and comment inside a single try/except. The orchestrator and lifecycle call it; the 6 repeated `task_info`/`sync_comments` guards go.
- Trim the `TaskManager` Protocol: drop the `metadata` parameter, which Linear ignores. Delete the dead `sync_phase_transition` and `sync_run_complete`, and `comments.py`'s duplicate `elif` branch.
- `adw resume` passes the task manager, so resumed runs update their ticket.

### Acceptance criteria

- [ ] A mocked Linear API (`httpx.MockTransport`) driven through a plan→ship run receives the same ordered sequence of status, label and comment calls as a golden list recorded before the refactor.
- [ ] A 500 on one Linear call logs one warning, and the run continues.
- [ ] Resuming a Linear-linked run updates the ticket.
- [ ] `task_managers/` contains `base.py`, `null.py`, `linear.py`, `comments.py`, `ticket_sync.py` and `__init__.py`.
- [ ] Lint and tests pass.

### Validation

Include the golden-sequence test, the error-path test and the resume test. Also include one real run against a Linear sandbox issue, with a screenshot of the ticket's comments and labels.

---

## Phase 2.11 — Simplify dashboard internals and its tests

**Plan**: _not yet created_

**Linear**: ADW-27 (https://linear.app/ivo-tsonev/issue/ADW-27)

**Goal**: Dashboard modules share one set of helpers instead of importing each other's privates, and tests check behaviour rather than markup.

### What to build

- Move the helpers shared across `routes.py`, `partials.py` and `mutations.py` into `dashboard/views.py`: run lookup, the name map, the pipeline builder, the `live.log` parser and one log-line renderer. This removes the 14 function-level cross-imports.
- Add `IndexManager.get_run(run_id)`. It replaces the 7 `get_recent_runs(limit=100000)` scans and `_find_run_entry`.
- Move both SSE streams into `dashboard/sse.py`. Render `toast.html` instead of the 4 inline copies. Have the out-of-band pipeline update render the `phase_pipeline` macro instead of HTML built in Python. Add one `_render(request, name, ctx)` for the `HX-Request` branches.
- Delete the dead code:
  - the `/partials/projects` route
  - `get_config_loader` and `get_config_registry`
  - unused CSS variables and utilities
  - the lifespan banner, which repeats the CLI's and shows the wrong port under `--reload`
- Fix `.kbd-nav-active`: it uses a DaisyUI v4 variable that doesn't exist in v5.
- Tests:
  - Replace the markup-substring tests (about 300–400) with one parametrized "page renders with the expected data" test per page, plus tests for the logic: costs, filters, pagination and status mapping.
  - Rewrite `test_run_detail.py` against real `context.json` files instead of 65 `ContextManager` patches.

### Acceptance criteria

- [ ] No dashboard module imports another dashboard module inside a function body.
- [ ] `grep -rn "limit=100000" src` returns nothing.
- [ ] Every page renders against a fixture project that has one run in each status.
- [ ] The dashboard test count drops by at least 300, and the coverage gate still passes.
- [ ] Lint and tests pass.

### Validation

Include a screenshot of every page against the fixture project, before and after (they should look the same apart from intended fixes), and the test counts, in the PR.

---

## Phase 2.12 — Thin the CLI

**Plan**: _not yet created_

**Linear**: ADW-28 (https://linear.app/ivo-tsonev/issue/ADW-28)

**Goal**: Each command lives in one place, errors are handled once, and duplicate commands are gone.

### What to build

- Fold `list_display.py`, `status_display.py`, `validate_config_display.py` and `run_display.py` into their single callers as plain functions. Either make `validate --verbose` work or remove it.
- One `@cli_errors` decorator replaces the 12 copies of print-message-and-suggestion-then-exit. Register `abort`, `cleanup` and `cleanup-orphans` directly, without the wrappers in `app.py` that re-declare every option.
- Delete `adw list --global`, which duplicates `adw global list`. Merge `register.py`, `unregister.py` and `projects.py` into one module; the command names stay the same.
- `logs.py`:
  - Use `SnapshotManager` and `ContextManager` instead of its own copies of their loaders.
  - Export tar only, without the temp-dir copy.
  - Drop the unreachable similar-runs fallback and the hint for a flag that doesn't exist.
- Delete the fields `progress.py` writes but never reads, and its no-op `on_llm_progress`. `global clean` uses `IndexManager`'s public API and one sample printer. `global stats --format` becomes `--json`, like the other commands.
- `run` and `resume` share one `_execute()`. Config is loaded once per `adw run`, and `resume` writes `live.log`.

### Acceptance criteria

- [ ] `src/adw/cli/` contains no `*_display.py`.
- [ ] `adw --help` and each group's `--help` match the target command tree in the audit report.
- [ ] Every command's error path exits non-zero and prints its code and suggestion. A parametrized test covers this.
- [ ] `adw resume` of an interrupted mocked run writes `live.log`.
- [ ] Lint and tests pass.

### Validation

Include the full `--help` tree and the error-path test output in the PR.

---

<!-- PHASES -->

## Epic-level acceptance criteria

- [ ] Every phase merged and its acceptance criteria met
- [ ] Status row in [EPICS.md](./EPICS.md) updated to `Done`
- [ ] `src/adw` has no `security/`, `webhook/`, `server/`, `validation/` or `utils/` package, and no `cli/dashboard.py`
  - `cli/dashboard.py` is gone as of phase 2.4.
- [ ] A `project.yaml` written by the pre-epic wizard with every optional section filled in still passes `adw validate`
- [ ] `adw init --wizard`, a mocked `adw run`, `adw resume`, `adw pr` and `adw dashboard web` each work end to end in a scratch repo
