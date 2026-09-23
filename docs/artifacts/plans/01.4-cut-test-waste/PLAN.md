# Plan: Cut test waste outside the dashboard

Status: in-progress
Branch: feature/adw-10
Risk: medium
Epic: 01 — Cleanup: test safety, dead code and bug fixes ([epic](../../epics/01-cleanup-safety-dead-code-bugs.md))
Phase: 1.4 — Cut test waste outside the dashboard
Linear: ADW-10
Created: 2026-09-23

## Goal

The suite loses at least 150 tests that check nothing: `pass` placeholders, prompt and instruction prose, trivial existence checks and duplicated fixtures. Coverage stays at or above 80 %, and ADR-001 names the new waste categories so they don't come back.

## Scope

- Delete the prompt-wording tests and replace them with one parametrized structural check per bundled phase in `tests/unit/commands/test_bundled_commands.py`. The check covers three things: `config.yaml` validates, `prompt.md` exists, and every `instructions.xml` parses.
- Delete the `pass`-placeholder files in `tests/unit/ship/`. Move `test_ship_phase_fixes.py` to `tests/unit/core/test_ship_extension.py` without its trivial `TestFlatTemplateVariables`, then remove `tests/unit/ship/`.
- Remove the six unused root fixtures from `tests/conftest.py`, the fixture data in `tests/fixtures/{llm,configs,runs}/`, and `tests/unit/core/test_constants.py`.
- Delete the six local `git_repo` definitions (4 files) in favour of the root fixture. Collapse the 7 identical `sample_context` copies in `test_snapshot_manager.py` into one module-level fixture.
- `tests/unit/executors/test_claude_code.py`:
  - delete `TestClaudeCodeExecutorClass`
  - move the three `_resolve_timeout` precedence tests to `tests/unit/hooks/test_runner.py`
  - drop `test_handles_json_array`
  - collapse the 11 `executor` copies into one module-level fixture
  - move the two integration copies to a new `tests/integration/conftest.py`
- ADR-001: three new rows in "Categories to Eliminate".

## Out of Scope

- `tests/dashboard/` and `tests/unit/dashboard/`, including the HTML-markup-substring tests. The ADR row lands here; the cleanup is a later phase.
- Deleting tests for code that phase 1.2 removes (`find_hook`, `CommandLoader`, `MockExecutor` helpers, …). Phase 1.2 owns those.
- Hoisting identical fixtures across packages: `sample_context` in `unit/core` vs `integration/core`, and `unit/core/test_resume_manager.py` vs `unit/models/test_resume.py`. The root conftest would then define a `sample_context` shape that every package inherits.
- Linting `tests/` in `scripts/preflight.sh` and CI: phase 1.5. This plan runs `ruff` on `tests/` by hand.
- ADR-001's stale "Metrics" table.

## Research Summary

See [RESEARCH.md](./RESEARCH.md). Headlines:

- **Baseline** (`f61f8873`): 4,296 collected; 4,291 passed and 5 skipped in 163 s; coverage 84.33 %.
- **The named deletion targets collect 170 tests.** After the moves and the new parametrized test, the expected net is −172 (→ ~4,124), which clears the ≥150 target.
- **Every `pass`-only test body in `tests/` sits in two files:** `ship/test_failure_diagnosis.py` (36) and `ship/test_command_execution.py` (16). The other 11 `^\s*pass$` hits in `tests/unit` are stub classes and `except` blocks, not test bodies.
- **The epic's premise about `TestAdditionalParsingCoverage` is wrong.** A branch-coverage diff over `tests/unit/executors` + `tests/integration` shows each of its tests is the only one reaching a `_parse_output` branch. The exception is `test_handles_json_array`, which duplicates `test_handles_non_dict_json`.
- `_resolve_timeout` is tested nowhere except `TestHookRunnerTimeoutResolution`, so the precedence tests move rather than go.
- All six bundled `.xml` files parse today, and every `CommandConfig` subclass sets `extra="forbid"`, so "validates" is a real check.

## Decisions

- **The bundled-phase check parametrizes over `PHASE_SEQUENCE`, not over a directory glob.** `PHASE_SEQUENCE` is the source of truth for which phases ship, and a missing phase dir must fail rather than silently shrink the parameter list. The check resolves files through `importlib.resources.files("adw")`, as the existing bundled tests do, so it checks the packaged location.
- **Hoisting uses the nearest shared scope** (user's choice). Copies in one file become one module-level fixture. Copies across files in the same package go to that package's `conftest.py`. Cross-package matches stay put. Result: `executor` 13 → 2, `sample_context` 21 → 15.
- **In `TestAdditionalParsingCoverage`, only `test_handles_json_array` goes** (user's choice). The other four are error and edge-path tests, which ADR-001 keeps.
- **Adjacent cleanups in files this phase already touches** (user's choice):
  - fold the 6 existence tests in `TestBundledCommands` into the new check
  - drop `TestFlatTemplateVariables`, whose 3 tests assign to a local dict and run no production code
  - drop `test_default_hook_timeout_constant_value`
  - rename `test_ship_phase_fixes.py` to `test_ship_extension.py` on the move
- **`test_git_diff.py` switches to the root fixture's `README.md`.** Its local fixture differs only by an `initial.txt` file and a `test_repo/` subdir, and no test takes both `git_repo` and `tmp_path`. Two tests update their file name and expected diff line.
- **The executor copies in `tests/integration/` go to a new `tests/integration/conftest.py`.** They are identical, both live in the `tests/integration` package, and no other integration test depends on an `executor` fixture from an outer scope.

## Risks

- **Phase 1.2 moves `get_config_class`** from `adw.commands.loader` to `adw.models.command` and deletes `loader.py`. Whichever phase merges second fixes the new test's import. Mitigation: TASK-001 imports it from wherever it lives at implementation time, and the note in that task names both paths.
- **Merge conflicts with phase 1.2 in `test_claude_code.py`, `hooks/test_runner.py` and `tests/conftest.py`.** Both phases delete from these files. Mitigation: rebase before `create-pr`; the conflicts are deletion against deletion.
- **A module-level fixture can shadow the root one.** A new module-level `executor` or `sample_context` could silently change what another class in the same file receives. Mitigation: every copy being collapsed hashes identical (AST body, arguments, decorators); `RESEARCH.md` lists the groups. Run the whole file after each collapse.
- **The root `git_repo` differs slightly from the local copies:** `user.name "Test"`, `README.md` reading "# Test Repository", and a worktree-cleanup teardown. Mitigation: `RESEARCH.md` lists what each consumer reads. Only `test_git_diff.py` depends on its fixture's file content.
- **Coverage could drop.** Mitigation: the deleted tests reach no `src` lines beyond `core/constants.py` (imported everywhere) and `_resolve_timeout` (moved). TASK-007 compares the full-run total against 84.33 %.

## Acceptance Criteria

- [ ] No test function in `tests/` has a body of only `pass` (docstring allowed). `grep -rn "^\s*pass$" tests/unit` hits only the 11 known stub-class and `except` lines listed in `RESEARCH.md`. Evidence: the AST scan output (`total 0`) and the grep output.
- [ ] `uv run pytest --collect-only -q | tail -1` drops by at least 150 from 4,296. Evidence: the before/after lines in `VALIDATION.md`.
- [ ] A full `uv run pytest` is green with coverage ≥ 80 %. Evidence: the summary and `TOTAL` lines, compared with the 84.33 % baseline.
- [ ] The new bundled-phase check fails when a bundled `config.yaml` gains an unknown key or an `instructions.xml` is malformed. Evidence: the RED output from TASK-001's temporary mutation.
- [ ] ADR-001's "Categories to Eliminate" table lists HTML markup substrings, prompt/instruction prose and `pass` placeholders. Evidence: the ADR diff.
- [ ] `scripts/preflight.sh`, `uv run ruff check tests/` and `uv run ruff format --check tests/` pass.

## Tasks

Task state lives here. Tasks are appended by `scripts/add_task.py` and
`scripts/add_final_task.py`. Update the checkboxes as work progresses.

- [x] TASK-001: Replace prompt-wording tests with one bundled-phase check
- [x] TASK-002: Delete ship placeholder tests and move the ship extension tests to core (depends on TASK-001)
- [x] TASK-003: Remove unused root fixtures and fixture data
- [x] TASK-004: Deduplicate git_repo and sample_context fixtures (depends on TASK-003)
- [x] TASK-005: Trim test_claude_code.py and hoist its executor fixture
- [ ] TASK-006: Add the three waste categories to ADR-001
- [ ] TASK-007: Final Validation
