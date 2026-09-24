# Plan: Collapse the init wizard into a straight sequence

Status: in-progress
Branch: feature/adw-22
Risk: medium
Epic: 02 — Cleanup: remove inert features and consolidate ([epic](../../epics/02-cleanup-remove-and-consolidate.md))
Phase: 2.6 — Collapse the init wizard into a straight sequence
Linear: ADW-22
Created: 2026-09-24

## Goal

After this phase:

- `adw init --wizard` asks its questions in one plain sequence, driven by one `run_wizard(root)` function instead of a flow controller, a step enum, a state model and nine handler classes.
- The wizard says "files written" only after a successful write. On a cancel, an interrupt or a write failure it says nothing was written and exits non-zero.
- It asks nothing whose answer is thrown away: no LLM retry step, no ship "Build command" that never reaches a config file, and no back/cancel promise that works at one prompt out of about 70.
- It detects the project's language and test command with the same `ProjectTypeDetector` as `adw init --no-interactive`.

## Scope

- **Basics detection.** `cli/wizard/basics.py` uses `config/detector.ProjectTypeDetector` and loses `LANGUAGE_MARKERS`, `DEFAULT_TEST_COMMANDS`, `detect_language` and `detect_test_command`. The detector gains the two markers only the wizard knew, `setup.cfg` and `build.gradle.kts` (TASK-001).
- **Ship build command.** The phases step's ship options stop asking for a "Build command". The project-level `build_command`, asked in the basics step, is the one the ship phase uses. Delete `cli/wizard/ship.py`, which only the package re-exports, and its tests (TASK-002).
- **Retry step.** Delete `cli/wizard/retry.py` and its step (D5). The generator writes the `llm.retry` block as comments with `RetryConfig`'s defaults. Drop the summary's `LLM Retry:` line (TASK-003).
- **Flow.** Replace `WizardFlowController`, `StepHandler`, `WizardStep`, `STEP_TITLES`, `WizardState` (`models/wizard.py`) and the `*StepHandler` classes with `run_wizard(root)` in `cli/wizard/flow.py`. It calls each `run_*_step(console)` in order and collects `cfg: dict[str, dict[str, Any]]`. The summary, the YAML generator and `ProjectInitializer` read it with `cfg.get(section, {})`. Delete `cli/wizard/navigation.py`. Trim `cli/wizard/__init__.py` to export only `run_wizard` (TASK-004).
- **Honest reporting.** `run_summary_step` returns whether it wrote the files. `adw init --wizard` exits 1 when the user declines at the summary, when the write fails, or when stdin ends. Ctrl+C exits 130. Ctrl+C is held off while the files are written and the project registered, so an interrupt lands before the write or not at all. Drop the "start over" choice, which never started over, the unconditional "Wizard Complete!" panel, and the back/cancel lines of the welcome panel (TASK-005).
- **Tests.** Delete `test_navigation.py`, `test_state.py`, `test_retry.py` and `test_ship.py`. Rewrite `test_flow.py` around `run_wizard`. Drop the handler, package-export and state-integration tests from the other wizard test files, and move `test_summary.py` and `test_yaml_generator.py` from `WizardState` to plain dicts. The acceptance transcripts come from tests that drive `adw init --wizard` through `CliRunner` stdin.

## Out of Scope

- **The webhook step.** Phase 2.3 (draft PR #212) deletes `cli/wizard/webhooks.py`. Until it lands, `run_wizard` calls `run_webhooks_step(console)` like the other steps. Whichever of 2.3 and 2.6 merges second drops the other's webhook lines (see Risks).
- **Prompt wording and defaults inside the steps**, apart from the ship "Build command" prompt. The basics build-command default stays empty, although `ProjectTypeDetector` knows one (see Decisions).
- **The `registry` parameter of `YAMLWithComments` and the `ConfigRegistry` it takes.** Phase 2.8 drops both.
- **One `atomic_write` helper.** Phase 2.7 replaces `atomic_write_config` with a shared `atomic_write`. This phase keeps the wizard's function as it is.
- **The minimal `adw init` path**, apart from `ProjectInitializer._write_config` moving from `WizardState` to a dict and the interrupt exit code. Its `ProjectInitializer.initialize` writes files one by one, so a Ctrl+C in the middle can leave a partial `.adw/` while the handler prints "No files created". That predates this phase and stays as it is.

## Research Summary

See [RESEARCH.md](./RESEARCH.md). In short:

- **The step functions ignore their state.** None of the `run_*_step` functions reads `state`; three mark it `# noqa: ARG001`. Each handler class only forwards to its function. The flow controller's back/forward machinery serves one prompt: `nav_confirm_ask("Add input files?")` in `phases.py`.
- **The wizard reports success it didn't have.** `WizardFlowController.run()` shows "Wizard Complete! … files have been written" after the summary step, whatever the step returned. Declining at the summary returns `action: "cancel"` or `"start_over"`, and the controller ignores both: nothing starts over, the panel still claims the write, and `adw init` exits 0. A `ConfigWriteError` also ends in the same panel and exit 0.
- **Two answers go nowhere.** The phases step's ship options put a "Build command" into `commands["build"]`. `ShipCommandsConfig` has no `build` field and `_add_ship_phase_settings` writes only `version_bump` and `publish`, so the answer is dropped. The generator's `ship` merge in `generate_all_phase_configs` and the summary's `Ship:` line read a `ship` section that no step fills since the ship step left the sequence.
- **Detection has drifted.** The wizard's `LANGUAGE_MARKERS` treats `setup.cfg` as Python but not `requirements.txt`, knows `build.gradle.kts` where the detector doesn't, and its Java and PHP test commands (`./gradlew test`, `./vendor/bin/phpunit`) differ from the detector's (`gradle test`, `vendor/bin/phpunit`), which minimal init writes.
- **Docs.** Nothing under `docs/` outside `artifacts/`, `README.md` or `AGENTS.md` mentions the wizard.
- **Baseline.** `uv run pytest` on `5f40b3bb`: 3354 passed, 5 skipped, coverage 84.81% (gate 80%).

## Decisions

- **Stop asking for the ship build command, rather than writing it.** `ShipCommandsConfig` deliberately has no `build` field; its docstring points at `ProjectConfig.build_command`, which `PhaseRunner` injects into the ship template as `commands.build`. The basics step already asks for that value. Writing a second copy would give two sources for one setting.
- **Declining at the summary cancels; there is no "start over".** The start-over branch never worked, because the controller ignored it. A loop back to the first step would be new behaviour, and re-running `adw init --wizard` does the same thing.
- **Exit codes: 1 for a decline, a write failure or end of input, 130 for Ctrl+C.** 130 is the shell convention for SIGINT. `init.py`'s interrupt handler, which exits 0 today, covers both the wizard and minimal init, so minimal init's Ctrl+C also exits 130. Its message ("No files created") stays.
- **Ctrl+C is ignored while the files are written and the project registered** (validation round 1, #1). `init.py`'s SIGINT handler raises `SystemExit`, which `atomic_write_config`'s `except OSError` rollback never sees, so an interrupt mid-write would leave files behind and print "No files created". A `_hold_interrupts()` context manager in `summary.py` sets SIGINT to `SIG_IGN` around the write, the registration and the success message, and restores the previous handler afterwards. An interrupt before the block finds nothing written; one inside it is dropped, and the success message reports the write. After the block only `run_summary_step`'s and `run_wizard`'s `return True` run before `init()` restores the original handler, so a false "No files created" needs a SIGINT in those few bytecodes (round 2, #5). Rolling back on `BaseException` was the alternative, but it leaves the post-write registration window unhandled.
- **`run_wizard` returns a bool, and `init.py` turns `False` into `SystemExit(1)`.** Only the CLI layer decides exit codes, as the existing "cannot overwrite" path in `init()` does.
- **`EOFError` counts as a cancel.** Rich's `Prompt.ask` raises it when stdin ends (Ctrl+D, or piped input that runs out). Today Typer turns it into `Aborted.` and exit 1, which never says whether anything was written. `run_wizard` catches it and says so; the exit code stays 1.
- **Steps take `console` only; `run_basics_step` also takes `root`.** The epic names `run_*_step(console)`. Basics needs the root for detection. The global-registry step keeps defaulting its display name to `Path.cwd().name`, which is `root` for every caller.
- **Step titles live in `run_wizard`'s step list**, as `(section, title, step)` tuples. The enum, the title dict and the "Step N/M" counter all collapse into that one list.
- **`cli/wizard/__init__.py` exports only `run_wizard`.** Tests import from the submodules. The package-export tests (`TestPackageExports`) go, as ADR-001 import-smoke tests.
- **The basics build-command default stays empty.** The detector has a build default (`npm run build`, `go build`, …), but Rich's `Prompt.ask` returns the default on an empty answer, so a user could no longer skip it without typing a space. Changing the prompt is out of scope.
- **Tests drive the real prompts through `CliRunner` stdin.** The accept and cancel transcripts the epic asks for come from `adw init --wizard` in a `git init` scratch dir, fed a string of answers, and the accept case runs `adw validate` on the result. The step unit tests keep patching `Prompt.ask`/`Confirm.ask`, as they do today.
- **Task order keeps every commit green.** TASK-001 to TASK-003 shrink the wizard while the controller still exists. TASK-004 swaps the controller for `run_wizard` and keeps its reporting as it is, so its diff stays structural. TASK-005 changes the reporting and exit codes.

## Risks

- **PR #212 (phase 2.3) conflicts with this branch.** It deletes `webhooks.py` and edits `flow.py`, `init.py`, `wizard/__init__.py`, `summary.py`, `yaml_generator.py`, `test_flow.py`, `test_summary.py` and `test_yaml_generator.py`, all of which this phase rewrites. It is a draft and already conflicts with `staging`. Mitigation: fetch and rebase before the PR and again before merging. If #212 lands first, drop the webhook step from `run_wizard` and the summary on rebase. If this lands first, #212's rebase deletes the `run_webhooks_step` line and the summary's `Webhooks:` block.
- **Removing the controller changes the prompts' order or count, and a user notices.** Mitigation: `run_wizard` keeps the controller's step order minus the retry step. `test_run_wizard_calls_steps_in_order_and_hands_cfg_to_summary` pins the call order, and the accept-defaults transcript test asserts the `Step 1/7` … `Step 7/7` headers in order.
- **The stdin-driven tests run `git` and write `.adw/`.** Mitigation: they run under `tests/unit/cli/`, whose autouse `isolated_cwd` fixture enters `tmp_path`, and the global-registry step writes under the per-test `HOME` from the root `isolated_home` fixture.

## Acceptance Criteria

- [ ] `adw init --wizard` in a scratch git repo, accepting every default, writes files that `adw validate` accepts. Evidence: the transcript test, RED then GREEN, and a transcript from a scratch repo under the session scratchpad.
- [ ] Declining at the summary writes no files, prints that nothing was written, and exits non-zero. Evidence: the cancel transcript test, RED then GREEN, and a scratch-repo transcript with `echo $?`.
- [ ] A write failure prints the error, says nothing was written, prints no success line, and exits non-zero. Evidence: the write-failure test, RED then GREEN.
- [ ] Ctrl+C at a prompt exits 130 and writes nothing, and Ctrl+C cannot interrupt the write or the dashboard registration. Evidence: `test_write_holds_off_ctrl_c`, RED then GREEN, and a scratch-repo transcript of `adw init --wizard` sent SIGINT at a prompt, with its exit code and `ls -a`.
- [ ] `grep -rn -I --exclude-dir=__pycache__ "WizardFlowController\|WizardState\|StepHandler\|nav_prompt_ask" src tests` returns nothing. (`-I` and the exclude skip the stale `.pyc` files that `git rm` leaves behind.) Evidence: the grep output.
- [ ] The wizard asks no retry questions and no ship build command, and its welcome panel promises no back/cancel keys. Evidence: the accept transcript, and the phases-step test that the ship options prompt only for version bump and publish.
- [ ] The wizard's language and test-command defaults match `ProjectTypeDetector`'s. Evidence: the basics tests with marker files, RED then GREEN.
- [ ] Lint and tests pass. Evidence: `scripts/preflight.sh` and the tail of `uv run pytest`, with coverage ≥ 80%.

## Tasks

Task state lives here. Tasks are appended by `scripts/add_task.py` and
`scripts/add_final_task.py`. Update the checkboxes as work progresses.

- [x] TASK-001: Detect the language and test command with ProjectTypeDetector
- [x] TASK-002: Stop asking for a ship build command and delete ship.py
- [x] TASK-003: Drop the LLM retry step
- [x] TASK-004: Replace the flow controller and WizardState with run_wizard (depends on TASK-001,TASK-002,TASK-003)
- [ ] TASK-005: Report honestly whether files were written (depends on TASK-004)
- [ ] TASK-006: Final Validation
