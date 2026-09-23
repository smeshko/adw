# Plan: Delete dead modules and symbols

Status: in-progress
Branch: feature/adw-8
Risk: medium
Epic: 01 — Cleanup: test safety, dead code and bug fixes ([epic](../../epics/01-cleanup-safety-dead-code-bugs.md))
Phase: 1.2 — Delete dead modules and symbols
Linear: ADW-8
Created: 2026-09-23

## Goal

`src/adw` no longer contains the modules and symbols that no production path reaches, the code that only they kept alive, or the tests that only exercised them.

## Scope

- Delete the modules `src/adw/validation/`, `src/adw/utils/`, `commands/validator.py` and `commands/loader.py`, plus the `jsonschema` and `types-jsonschema` dependencies. `get_config_class` and `PHASE_CONFIG_CLASSES` move to `models/command.py`.
- Delete every symbol the epic lists except `PR_DESCRIPTION_ARTIFACT`, which is live (see Decisions).
- Follow cascades. Also delete what becomes dead once the listed code is gone:
  - `adw.exceptions.ValidationError`, raised only by `SchemaValidator`.
  - `ResolvedCommand.has_pre_hook` and `has_post_hook`, read only by `CommandLoader`.
  - `WorktreeConfig.cleanup_branch_on_remove` and `ConcurrentRunManager.unregister_run`, used only by `Orchestrator._cleanup_worktree`.
  - The `git_config` parameter of `DocumentExtension` and `create_default_registry`, and the `console` parameter of `ClaudeCodeExecutor`.
  - Imports, re-exports (`__all__`), and docstring lines naming a deleted symbol.
- Tests:
  - Delete the tests whose only subject is a deleted symbol.
  - Rewrite the tests that merely borrow a deleted helper onto the surviving API.
  - Move the `get_config_class` tests to `tests/unit/models/test_command.py`.
- Docs:
  - Drop the `ValidationConfig`/`adw.validation` line from `AGENTS.md`.
  - Drop the two `src/adw/validation/` rows from `docs/architecture/deep-dive/validate-phase.md`.

## Out of Scope

- Dead code that exists before this phase and that no deletion here makes dead. The `vulture` baseline has 227 entries at 60% confidence, mostly false positives, and includes things like `ResumeManager.get_resume_status`, `SnapshotManager.load_snapshot` and `ConfigRegistry.get_section_order`. The PR lists the credible ones for Epic 02.
- `MockExecutor.call_count`. `tests/unit/executors/test_retry.py` still uses it; phase 1.6 deletes that file.
- `PR_DESCRIPTION_ARTIFACT` and the `pr_result` plumbing around it: phase 1.7.
- The rest of `exceptions.py`, and the `__init__.py` re-export trimming beyond the deleted names: phase 1.3.
- Test fixtures that were already unused: phase 1.4. Fixtures that only the deleted tests used *are* deleted.
- `docs/analysis/validation-phase-redesign.md`, a historical analysis, and the other deep-dive docs: Epic 03 rewrites them.

## Research Summary

See [RESEARCH.md](./RESEARCH.md). The plan was prototyped on a scratch copy of `src` and a throwaway clone:

- Every epic-listed symbol was re-verified by grep across `src/adw` (`.py`, `.sh`, `.yaml`, `.md`, `.html`, `.xml`). All are dead except `PR_DESCRIPTION_ARTIFACT`, which `cli/progress.py:337,360` reads.
- `vulture src/adw --min-confidence 60` was diffed before and after the deletions. It reached a fixpoint after two rounds, and the cascades in Scope are what it found. A grep pass added `adw.exceptions.ValidationError`, whose name `vulture` can't separate from pydantic's.
- After the deletions and `ruff --fix`, `mypy src/adw` passes, and `src/adw` shrinks from 46,993 to 44,705 lines (−2,288).
- Suite against the prototype, with only the whole-file test deletions applied: 79 failed, 6 collection errors, 3,918 passed. Every failure is a test this plan deletes or rewrites; none were unexpected.
- `jsonschema` leaves `uv.lock` entirely; no other package depends on it.

## Decisions

- **Keep `PR_DESCRIPTION_ARTIFACT`.** The epic says to re-verify each symbol first, and this one has two live readers in `cli/progress.py`. Phase 1.7 reworks that code.
- **Follow all cascades (user's choice).** A symbol that loses its last `src` reference to this phase's deletions is deleted here too. Each task diffs `vulture` output from before and after its change. Every new entry is either deleted after a grep of templates, YAML and `.sh`, or recorded in the PR with the reason it stays.
- **Two rules decide what counts as dead:**
  - A production symbol is dead once nothing in `src` references it; tests don't keep it alive.
  - `MockExecutor` is a test double, so its API is dead only once nothing in `src` or `tests` uses it. That keeps `call_count`.
- **Delete `adw.exceptions.ValidationError` here, not in 1.3.** It is a direct cascade of deleting `SchemaValidator`. Phase 1.3's target list of classes doesn't change.
- **`unregister_run` goes without replacement.** Every run is its own `adw` subprocess (`core/run_trigger.py` uses `Popen`), so the lock's PID dies with the run, and `get_active_runs` deletes stale locks. The method's only caller, `_cleanup_worktree`, was already dead, so behaviour doesn't change.
- **Dropping `cleanup_branch_on_remove` breaks no config.** `WorktreeConfig` uses pydantic's default `extra="ignore"`, so a `project.yaml` that still sets the key loads and ignores it. Nothing in the wizard, the dashboard or `yaml_generator` renders it.
- **How tests that borrow deleted helpers are rewritten:**

  | Deleted helper | Replacement |
  |---|---|
  | `store_text` | `store` |
  | `get_json` | `json.loads(manager.get(...))` |
  | `ProjectConfig.from_yaml` | `ProjectConfig.model_validate(yaml.safe_load(...))` |
  | `HookResult.is_success` | `exit_code == 0` |
  | `generate_run_id()` | `str(ULID())` |
  | `has_pre_hook` / `has_post_hook` | `pre_hook_paths` / `post_hook_paths` |
  | `RunDirectoryManager.list_runs` | filesystem checks on `runs_dir` |

  This keeps unrelated behaviour coverage, such as unicode and large-content integrity and resolver hook detection. Cutting tests is phase 1.4's job.
- **Delete `tests/unit/utils/test_diff.py` and `tests/unit/commands/test_module_structure.py` too.** The epic doesn't list them. The first only covers `adw.utils.diff`. The second is import-smoke (ADR-001), and half of it imports `CommandLoader`.
- **The `TestWorktreeNoAutoDelete` guard gets a new subject.** Its 5 tests replace `orchestrator._cleanup_worktree` with a mock and assert it isn't called, and assigning to a deleted attribute passes silently. They now patch `WorktreeManager.remove_worktree` and assert that isn't called, which is the real "no auto-delete" invariant.
- **Runtime evidence (user's choice):**
  - `adw run --dry-run "noop"` lists all five phases, as the epic asks.
  - `adw validate` in the same scratch repo shows plan…ship `OK`. It is the only CLI path that runs the moved `get_config_class` on every phase; dry-run uses `CommandConfig` directly.
- **One commit per layer (user's choice):** modules first, then core, models, and the remaining packages. Each task leaves `preflight.sh` and its touched tests green.

## Risks

- **A symbol is referenced from a template, YAML or shell file that `vulture` and mypy can't see.** Mitigation: each deletion is grepped across `src/adw` with no `--include` filter before removal. The prototype's grep found no such reference for any symbol in this plan.
- **A deletion breaks an import that only runs lazily**, like the function-local `get_config_class` imports in `dashboard/partials.py` and `dashboard/mutations.py`. Mitigation: mypy follows function-local imports, and the dashboard tests exercise both routes. TASK-003 greps for `commands.loader` afterwards.
- **Coverage drops below 80%.** Dead code and its tests leave together, so the ratio barely moves (84.33% at HEAD). Mitigation: TASK-007 runs the full suite. If the gate fails, the rewrite rule above applies rather than restoring deleted code.
- **The flaky `test_stats_display_with_real_data`.** Mitigation: rerun it once, as `AGENTS.md` says.
- **A user relies on a custom `schema.json` in `.adw/commands/` being enforced by `SchemaValidator`.** Nothing calls `SchemaValidator`: `PhaseRunner` only injects `schema.json` as the `{{schema}}` template variable (`core/phase_runner.py:494`), and that stays.

## Acceptance Criteria

- [ ] `grep -rn "adw.validation\|adw.utils\|jsonschema\|CommandLoader" src tests pyproject.toml` returns nothing. Evidence: the empty grep output.
- [ ] `grep -rnE "LoadedCommand|SchemaValidator|escape_feature_description|find_hook|get_next_phase|SessionContext|ProjectContext|ArtifactType|from_yaml_file|cleanup_branch_on_remove|unregister_run|json_schema_extra" src` returns nothing. Evidence: the empty grep output.
- [ ] `uvx vulture src/adw --min-confidence 60`, diffed against the baseline taken at the start of TASK-001, reports no new entry. Evidence: the empty `comm -13` output.
- [ ] `scripts/preflight.sh` passes, and `uv run pytest` is green with coverage ≥ 80%. Evidence: the preflight output and the pytest summary line with the coverage total.
- [ ] In a scratch repo:
  - `adw run --dry-run "noop"` lists all five phases.
  - `adw validate` reports `OK` for plan, build, validate, document and ship.

  Evidence: both transcripts.
- [ ] `find src -name '*.py' | xargs cat | wc -l` drops by at least 2,000 against 46,993. Evidence: the before/after numbers in `VALIDATION.md`.

## Tasks

Task state lives here. Tasks are appended by `scripts/add_task.py` and
`scripts/add_final_task.py`. Update the checkboxes as work progresses.

- [x] TASK-001: Delete adw.validation and adw.utils
- [x] TASK-002: Delete SchemaValidator, ValidationError and jsonschema (depends on TASK-001)
- [x] TASK-003: Move get_config_class into models and delete CommandLoader (depends on TASK-002)
- [x] TASK-004: Delete dead core symbols and their cascades (depends on TASK-003)
- [ ] TASK-005: Delete dead model symbols and schema examples (depends on TASK-004)
- [ ] TASK-006: Delete dead executor, hook, logging, worktree and cli symbols (depends on TASK-005)
- [ ] TASK-007: Final Validation
