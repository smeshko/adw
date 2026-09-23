# Research: Delete dead modules and symbols

Curated findings only — no raw conversation transcripts.

## Key Files & Directories

Modules to delete:

| Path | Lines | Importers in `src` | Tests |
|---|---|---|---|
| `src/adw/validation/` (`__init__`, `models`, `phase`, `report`, `state_manager`) | 530 | `models/__init__.py:84` (`ValidationResult`) only | `tests/unit/validation/` (5 files) |
| `src/adw/utils/` (`diff.py`, `ulid.py`) | 203 | none | `tests/unit/utils/test_ulid.py` and `test_diff.py`. `generate_run_id` is also imported by `tests/unit/core/test_run_directory.py:14` and `tests/integration/core/test_run_directory_integration.py:16` |
| `src/adw/commands/validator.py` (`SchemaValidator`) | 208 | `commands/__init__.py` only | `tests/unit/commands/test_validator.py` |
| `src/adw/commands/loader.py` (`CommandLoader`, `get_config_class`, `PHASE_CONFIG_CLASSES`) | 300 | `get_config_class` is live, imported by `core/phase_runner.py:19`, `core/extensions/ship.py:16`, `config/checker.py:19`, and function-locally by `dashboard/partials.py:1313` and `dashboard/mutations.py:750`. `CommandLoader` is imported only by `commands/__init__.py` | `tests/unit/commands/test_loader.py` (`TestPhaseConfigClasses` at L625 is the only part that survives), `tests/unit/commands/test_module_structure.py`, `tests/integration/test_document_phase.py::TestDocumentPhaseDocMappings` (L518) |

Symbols: production references found by grep, and the tests that touch each.

- **core**
  - `Orchestrator.get_next_phase`: `test_orchestrator.py::TestGetNextPhase`.
  - `Orchestrator.abort`: `test_orchestrator.py::TestOrchestratorAbort` and `integration/cli/test_abort_integration.py::test_full_abort_flow_via_orchestrator`. `adw abort` and the dashboard call `InterruptionHandler.abort_gracefully` directly.
  - `Orchestrator._cleanup_worktree`: `test_orchestrator.py::TestWorktreeNoAutoDelete` (5 tests) mocks it and asserts it isn't called.
  - `PhaseRunner._merge_configs` (`_merge_configs_with_project` stays): the first 3 tests of `test_phase_runner.py::TestConfigMerging`.
  - `ProgressCallback`: no tests. `Callable` becomes an unused import.
  - `ArtifactManager.store_text`, `get_auto`, `get_json`, `get_artifact_paths` (`store`, `get`, `store_json`, `list_artifacts` stay):
    - `test_artifact_manager.py`: `TestArtifactManagerJSON`, `TestArtifactManagerText`, `TestArtifactManagerAutoDetect`, `TestArtifactPaths`, `TestArtifactPathsRunContextIntegration`.
    - `test_phase_runner.py`: 2 tests use them as helpers.
    - `integration/core/test_artifact_manager_integration.py`: most tests use them as helpers, and `TestRunContextIntegration` exists only for `get_artifact_paths`.
  - `RunDirectoryManager.acquire_lock`, `list_runs`, and `RunInfo`:
    - `test_run_directory.py`: `TestFileLocking` (3 of 7 tests) and `TestRunListing` (all 6).
    - The integration file: `TestConcurrentAccess`, plus 4 tests that call `list_runs()` as a check.
    - After deletion, `datetime`, `pydantic` and `ulid` imports in `run_directory.py` go unused.
  - `StatsAggregator.get_token_usage`: `test_stats_aggregator.py::TestGetTokenUsage`, and a stub method in `integration/cli/test_global_stats_integration.py::_create_mock_aggregator_class`.
  - `DocumentExtension._git_config` is assigned and never read.
    - Its `git_config` parameter is passed by `core/extensions/__init__.py::create_default_registry`, which is called by `cli/bootstrap.py:288`.
    - Test call sites: `test_orchestrator.py:2227,2336,2418` and `integration/test_document_phase.py:272,493`.
    - `bootstrap` still passes `git_config` on to `Orchestrator`, so that argument stays there.
  - `PR_DESCRIPTION_ARTIFACT`: **live**, read at `cli/progress.py:337,360`. It stays.
- **models**
  - `SessionContext`, `ProjectContext`: `test_context.py::TestSessionContext` and `TestProjectContext`, and `test_template.py::test_session_context_as_context`.
  - `RunContext.resolve_artifact_path` and `get_runs_dir`: `test_context.py::TestRunContextArtifactPathResolution` (the whole class). The `get_runs_dir` hits in `tests/unit/cli/*` patch the unrelated `cli.bootstrap.get_runs_dir`.
  - `phase.Artifact`, `ArtifactType`: no tests.
  - `ProjectConfig.from_yaml` and `from_yaml_file`:
    - Tests: `test_config.py::TestProjectConfig` (7 tests), `test_config_task_manager.py` (1), `webhook/test_server.py::TestWebhookConfigInYAML` (2).
    - Also used in the class docstring (`models/config.py:509`) and in the `tests/conftest.py:209` fixture docstring.
    - `yaml` and `Path` go unused in `models/config.py`.
  - `HookResult.is_success`: `test_hook_result.py::test_is_success_property`. It's also used as an assertion in `hooks/test_runner.py` (4 tests) and `integration/test_hooks.py` (6).
  - `json_schema_extra` example blocks: 10 blocks in `models/{phase,index,registry(2),worktree,logging(2),config,hook,context}.py`, plus one in `validation/models.py`. Only `ValidationResult`'s is ever asserted (`model_json_schema()` in `tests/unit/validation/test_models.py`). `models/pr.py:254` calls `model_json_schema()` on its own model, which has no example block.
- **executors, hooks, logging, worktree, cli**
  - `MockExecutor.all_prompts`, `last_prompt`, `reset`, `assert_called_once`, `assert_called_with` are unused in both `src` and `tests`. `call_count` is used by `tests/unit/executors/test_retry.py` and stays.
  - `ClaudeCodeExecutor.console` is assigned and never read. `cli/bootstrap.py:273` passes `console=console`, and `bootstrap` still uses `console` for `ProgressDisplay`. Its test is `test_claude_code.py::TestRealTimeStreaming::test_accepts_custom_console`.
  - `hooks.runner.find_hook` (re-exported in `hooks/__init__.py`): `hooks/test_runner.py::TestFindHook` (7 tests) and 2 tests in `integration/test_hooks.py`. The live lookup is `CommandResolver._find_hook_path`.
  - `LiveStreamTransport.write_phase`, `write_raw`: no tests.
  - `ConsoleTransport.is_tty` (`_is_tty` stays): `test_console.py::TestConsoleTransportTTYDetection` (4 tests). `TestConsoleTransportTTYVsNonTTY` covers the TTY behaviour through the output.
  - `WorktreeBranchManager.create_branch`: `test_branch.py::TestBranchCreation` (3 tests). `WorktreeError` becomes an unused import.
  - `ConcurrentRunManager.can_start_run`, `get_run_info`: 5 tests in `test_concurrent.py`. `check_can_start_or_raise` is the live check.
  - `escape_feature_description` is in `commands/template.py` and its `__all__`, and `cli/app.py:28,343` imports it and discards the result. Test: `tests/unit/commands/test_escape.py`.

Cascades that `vulture` found once the listed code was gone:

| Symbol | Why it dies | Tests |
|---|---|---|
| `ResolvedCommand.has_pre_hook` and `has_post_hook` (`@computed_field`, `models/command.py:340,346`) | Only `CommandLoader` read them. `ResolvedCommand` is never serialized. | Assertions in `test_directory_validation.py` (6), `test_resolved_command.py` (2), `test_resolver.py` (5) and `ship/test_ship_phase_fixes.py` (1). The kwargs in `core/test_artifact_passing.py:294-295` are ignored by pydantic but are dropped anyway. |
| `WorktreeConfig.cleanup_branch_on_remove` (`models/config.py:261`) | Its only reader is `_cleanup_worktree`. | None found by grep. |
| `ConcurrentRunManager.unregister_run` | Its only caller is `_cleanup_worktree`. | `test_concurrent.py::test_unregister_run_*` (2) |

Cascade found by grep, since `vulture` can't tell the name apart from pydantic's:

- `adw.exceptions.ValidationError` (`exceptions.py:435`) is raised only in `commands/validator.py`. The `except ValidationError` clauses in `context_manager`, `snapshot_manager` and `phase_runner` catch pydantic's.

## Architecture Facts

- Runs never share a process. The dashboard and webhook start runs through `core/run_trigger.py`'s `subprocess.Popen`.
  - `RunLifecycle` registers a concurrent-run lock with the run's PID (`run_lifecycle.py:632`).
  - `ConcurrentRunManager.get_active_runs` deletes the locks of dead PIDs, which is why `unregister_run` is redundant.
- `ProjectConfig` and `WorktreeConfig` don't set `extra`, so pydantic ignores unknown keys, and removing a field is backward compatible for existing `project.yaml` files.
- `adw run --dry-run` loads each phase's `config.yaml` with `CommandConfig.model_validate` (`cli/dry_run.py:147`). It never calls `get_config_class` and renders no prompt. `adw validate` (`config/checker.py:300`) calls `get_config_class` for all five phases.
- `models/__init__.py` imports `adw.validation.models`, and `validation/phase.py` imports `adw.models.command`. Deleting `validation/` removes that cycle.
- `preflight.sh` lints and type-checks `src/` only. Tests aren't checked by ruff or mypy, so an assignment to a deleted attribute in a test (`orchestrator._cleanup_worktree = MagicMock()`) passes silently.

## Constraints

- Each task is one commit and leaves `scripts/preflight.sh` plus the touched test files green (`uv run pytest` on the touched test paths with `-o addopts=""`).
- No behaviour change: only deletions, import moves, and test rewrites onto the surviving API.
- `AGENTS.md`: tests that touch git run in `git_repo`/`tmp_path`, and `HOME` is isolated per test. The rewritten tests keep their existing fixtures.

## Useful Commands

```bash
# cascade detector: run at task start and at task end, then diff
uvx vulture src/adw --min-confidence 60 | sed -E 's/:[0-9]+:/:/' | sort > "$SCRATCH/vulture-before.txt"
uvx vulture src/adw --min-confidence 60 | sed -E 's/:[0-9]+:/:/' | sort > "$SCRATCH/vulture-after.txt"
comm -13 "$SCRATCH/vulture-before.txt" "$SCRATCH/vulture-after.txt"   # newly dead → delete or record

# re-verify a symbol before deleting it (no --include filter: catches .sh/.yaml/.html/.xml)
grep -rn "SYMBOL" src/adw

# LOC measure used by the epic-level criterion
find src -name '*.py' | xargs cat | wc -l

# runtime evidence in a scratch repo (HOME isolated so ~/.adw is untouched)
mkdir -p "$SCRATCH/repo" "$SCRATCH/home" && cd "$SCRATCH/repo" && git init -q && git commit -q --allow-empty -m init
HOME="$SCRATCH/home" uv run --project "$CHECKOUT" adw run --dry-run "noop"
HOME="$SCRATCH/home" uv run --project "$CHECKOUT" adw validate   # five phase rows must read OK
```

## Uncertainty

- **Is `PR_DESCRIPTION_ARTIFACT` dead, as the epic says?** No: `cli/progress.py` reads it on the PR-failed and no-PR-result branches. It stays, and phase 1.7 revisits it.
- **Does deleting `unregister_run` leak locks?** Resolved: no. Runs are separate processes, and the stale-PID sweep removes their locks. The method was already unreachable.
- **Coverage after deletion?** Not measured: the prototype run carried 79 expected failures, so its coverage number is meaningless. HEAD is at 84.33%, and dead code leaves with its tests. TASK-007 measures the real number.
- **Does `adw validate` exit 0 in a bare scratch repo?** No: it reports a missing `.adw/project.yaml` (exit 1). The evidence is the five phase rows reading `OK`, not the exit code.

## References

- Epic: [01 — phase 1.2](../../../epics/01-cleanup-safety-dead-code-bugs.md)
- [ADR-001 test reduction strategy](../../../../architecture/adrs/ADR-001-test-reduction-strategy.md)
- Previous phase: [01.1-isolate-test-suite](../2026-09-23-01.1-isolate-test-suite/PLAN.md)
