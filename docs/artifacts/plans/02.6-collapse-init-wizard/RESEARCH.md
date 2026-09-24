# Research: Collapse the init wizard into a straight sequence

Curated findings only — no raw conversation transcripts.

## Key Files & Directories

- `src/adw/cli/init.py` — `init()` installs a SIGINT handler (`_interrupt_handler`, exits 0 with "Setup cancelled. No files created."), handles the existing-config prompt, then calls `_run_wizard_setup(project_root)` or `_run_minimal_setup`. `_run_wizard_setup` builds a `WizardState`, a `WizardFlowController`, registers eight handlers and ignores `controller.run()`'s result.
- `src/adw/cli/wizard/flow.py` (299 lines) — `StepHandler` protocol, `WizardStep` enum (8 members), `WizardFlowController` with `STEP_SEQUENCE`, `STEP_TITLES`, its own SIGINT handler, `run()`, `advance()`, `go_back()`, `cancel()`, and the welcome and completion panels.
- `src/adw/models/wizard.py` (137 lines) — `WizardState`: `current_step`, `completed_steps`, `collected_config`, `navigation_history`, `history_position`, plus navigation methods. Re-exported from `models/__init__.py`. Also used by `config/initializer.py` (`_write_config`) to feed the generator.
- `src/adw/cli/wizard/navigation.py` (149 lines) — `NavigationSignal`, `NavigationError`, `check_navigation`, `nav_prompt_ask` (no callers outside the package's re-exports) and `nav_confirm_ask` (one caller: `phases._prompt_input_files`).
- `src/adw/cli/wizard/__init__.py` (137 lines) — a 30-line docstring and a 41-name re-export list. Only `init.py` imports from the package; tests import some names through it.
- `src/adw/cli/wizard/basics.py` — `LANGUAGE_MARKERS`, `DEFAULT_TEST_COMMANDS`, `detect_language`, `detect_test_command`, `BasicsStepHandler`, `run_basics_step(state, console, project_root=None)`.
- `src/adw/cli/wizard/{git,global_registry,task_manager,phases,webhooks}.py` — each has a `*StepHandler` whose `execute(state, console)` forwards to `run_*_step(state, console)`. No step function reads `state`; `git`, `global_registry` and `ship` mark it `# noqa: ARG001`.
- `src/adw/cli/wizard/retry.py` (328 lines) — the LLM retry step and four validators. Only the flow and its tests use it.
- `src/adw/cli/wizard/ship.py` (121 lines) — `ShipStepHandler`/`run_ship_step`. Not in `STEP_SEQUENCE`; its docstring says it is "retained for backwards compatibility". Only the package re-exports and `test_ship.py` use it.
- `src/adw/cli/wizard/phases.py` — `_configure_ship_phase` prompts "Version bump command", "Build command", "Publish command" and "Wait for CI before merging PR?". The build answer lands in `commands["build"]`.
- `src/adw/cli/wizard/summary.py` — `SummaryStepHandler`, `run_summary_step(state, console, project_root)`, `generate_summary_panel(state)`, `generate_project_yaml(state)`, `generate_phase_configs(state)`, `atomic_write_config`, `ConfigWriteError`, `_prompt_start_over_or_cancel`, `_register_in_global_dashboard`, `_show_success_message`.
- `src/adw/config/yaml_generator.py` — `YAMLWithComments.generate_project_yaml(state)` reads `basics`, `git`, `task_manager`, `llm_retry` and `webhooks` through `state.get_step_config`. `generate_all_phase_configs(state, registry)` reads `phases` and merges a `ship` section into the ship phase.
- `src/adw/config/detector.py` — `ProjectTypeDetector.detect(root)` returns a project type (`nodejs` for `package.json`, `generic` when nothing matches). `get_defaults(type)` returns `language`, `test_command`, `build_command`, and falls back to `generic` for an unknown type. It has a `javascript` alias.
- `src/adw/models/command.py:110` — `ShipCommandsConfig` has only `version_bump` and `publish`, and its docstring says the build command is configured at the project level.
- `src/adw/core/phase_runner.py:440` — injects `ProjectConfig.build_command` into the ship template as `commands["build"]`.
- `src/adw/models/config.py:18` — `RetryConfig` with defaults `max_retries=3`, `base_delay_seconds=1.0`, `max_delay_seconds=60.0`, `multiplier=2.0`; it sits at `ProjectConfig.llm.retry`.

## Architecture Facts

- **Flow order today**: basics → global_registry → git → task_manager → phases → llm_retry → webhooks → summary. `init.py` registers a handler for each.
- **Only one prompt honours back/cancel.** `nav_confirm_ask("Add input files?")` in `phases._prompt_input_files` is the sole caller of the navigation helpers; every other prompt uses Rich's `Prompt.ask`/`Confirm.ask` directly. The welcome panel still advertises `n`/`b`/`c` keys.
- **The summary's outcome never reaches the caller.** `WizardFlowController.run()` stores the summary's return dict in `state` and then calls `_show_completion()`, which prints "Your project has been configured and files have been written." `run_summary_step` returns `{"confirmed": False, "action": "cancel"|"start_over"}` on a decline, and `{"action": "error"}` on a `ConfigWriteError`. `_run_wizard_setup` returns `None` either way, so `adw init --wizard` exits 0.
- **Both SIGINT handlers exit 0.** `init._interrupt_handler` and `WizardFlowController._handle_interrupt` print "Setup cancelled. No files created." and `raise SystemExit(0)`. The controller's handler replaces `init`'s for the duration of `run()`.
- **Dead summary lines.** `generate_summary_panel` prints a `Ship:` line from `state.get_step_config("ship")`, which no registered step fills, so it always says "Default (no commands, manual merge)", even when the user set ship commands in the phases step. It also prints `LLM Retry:`, which goes with the retry step.
- **Detection drift** between `wizard/basics.py` and `config/detector.py`:

  | | wizard | detector |
  |---|---|---|
  | Python markers | `pyproject.toml`, `setup.py`, `setup.cfg` | `pyproject.toml`, `setup.py`, `requirements.txt` |
  | Java markers | `pom.xml`, `build.gradle`, `build.gradle.kts` | `build.gradle`, `pom.xml` |
  | Java test | `./gradlew test` | `gradle test` |
  | PHP test | `./vendor/bin/phpunit` | `vendor/bin/phpunit` |
  | no markers | `unknown` | type `generic` → language `unknown` |

- **The generator already comments out untouched sections.** When `retry_custom` is false, `generate_project_yaml` writes `# llm:` and `#   path: "claude"`. The retry defaults appear nowhere unless the user customised them.
- **Rich prompts and stdin.** `Prompt.ask`/`Confirm.ask` read through `Console.input` → `input()`. On an empty answer they return the default. When stdin ends they raise `EOFError`. `Confirm.ask` re-prompts on anything but y/n, so an unexpected answer consumes the next line.
- **The accept path touches `HOME` and git.** The global-registry step defaults to "yes" and registers the project through `ProjectRegistryManager` under `~/.adw`. The git step runs `git rev-parse --is-inside-work-tree` and exits 1 outside a repository.

## Constraints

- mypy `--strict` and ruff gate CI (`scripts/preflight.sh`).
- ADR-001: test behaviour, error paths and I/O; no import-smoke, enum-existence or trivial-attribute tests.
- Tests under `tests/unit/cli/` run from `tmp_path` via the autouse `isolated_cwd` fixture; `HOME` is per-test via `isolated_home`.
- Draft PR #212 (phase 2.3, branch `feature/adw-19`) edits the same wizard, summary, generator and test files. It already conflicts with `staging`.

## Useful Commands

```bash
# the wizard tests
uv run pytest tests/unit/cli/wizard tests/unit/cli/test_init.py tests/unit/config/test_yaml_generator.py tests/unit/config/test_initializer.py -o addopts=""

# the acceptance grep
grep -rn "WizardFlowController\|WizardState\|StepHandler\|nav_prompt_ask" src tests

# a scratch-repo transcript (session scratchpad, isolated HOME). Call this
# worktree's binary: a bare `adw` is the main checkout's editable install,
# which runs `staging`, not this branch.
ADW=/Users/A1E6E98/Developer/Projects/adw/adw-final/.worktrees/adw-22/.venv/bin/adw
d=$(mktemp -d "$SCRATCH/wiz.XXXX"); cd "$d" && git init -q && HOME="$d/home" "$ADW" init --wizard < answers.txt; echo "exit=$?"; HOME="$d/home" "$ADW" validate
```

## Baseline

- `uv run pytest` on `5f40b3bb`: 3354 passed, 5 skipped in 182 s, coverage 84.81% (gate 80%).

## Uncertainty

- **Exactly how many answers the accept path needs.** It depends on whether the language is detected (a `Confirm` instead of a `Prompt`) and on the global-registry "yes" adding a name prompt. Resolved by feeding a long run of newlines: every prompt accepts its default on an empty line, the summary's "Create configuration?" defaults to yes, and surplus lines are never read.
- **Whether anything outside the wizard imports `WizardState`.** Resolved: `config/initializer.py` and `models/__init__.py` only.

## References

- Epic 02, phase 2.6 (`docs/artifacts/epics/02-cleanup-remove-and-consolidate.md`)
- Simplification audit decision D5 (drop the retry step), via the epic's architecture references
- `docs/architecture/adrs/ADR-001-test-reduction-strategy.md`
