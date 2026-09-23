# TASK-004: Delete dead core symbols and their cascades

Depends on: TASK-003
Suggested commit: `refactor(core): delete unused orchestrator, artifact, run-directory and stats methods`

## Goal

This task deletes the core symbols the epic lists, except `PR_DESCRIPTION_ARTIFACT`, and the code that only they used. The cascades are `ConcurrentRunManager.unregister_run`, `WorktreeConfig.cleanup_branch_on_remove`, and the `git_config` parameter of `DocumentExtension` and `create_default_registry`.

## Files

- `src/adw/core/orchestrator.py`: delete `get_next_phase`, `abort` and `_cleanup_worktree`, and the "Keep these methods for backwards compatibility" comment above `_cleanup_worktree`.
- `src/adw/core/phase_runner.py`: delete `_merge_configs` (keep `_merge_configs_with_project`) and the module-level `ProgressCallback` alias.
- `src/adw/core/artifact_manager.py`: delete `store_text`, `get_auto`, `get_json` and `get_artifact_paths`. `store`, `get`, `store_json` and `list_artifacts` stay.
- `src/adw/core/run_directory.py`: delete `acquire_lock`, `list_runs` and `class RunInfo`. `ruff --fix` removes the imports they leave unused: `datetime`, `pydantic`, `ulid`.
- `src/adw/core/__init__.py`: drop `RunInfo` from the import and `__all__`.
- `src/adw/core/stats_aggregator.py`: delete `get_token_usage`.
- `src/adw/core/extensions/document.py`: delete `self._git_config`, the `git_config` parameter, and its docstring lines, including the class-docstring example.
- `src/adw/core/extensions/__init__.py`:
  - `create_default_registry` loses its `git_config` parameter, its docstring line and its example argument.
  - It now registers `DocumentExtension(runs_dir)`.
- `src/adw/cli/bootstrap.py:288`: call `create_default_registry(runs_dir, project_root=project_root)`. `git_config` is still passed to `Orchestrator` below, so it stays.
- `src/adw/worktree/concurrent.py`: delete `unregister_run` and the `unregister_run` line in the class docstring example (cascade: its only caller was `_cleanup_worktree`).
- `src/adw/models/config.py`: delete `WorktreeConfig.cleanup_branch_on_remove` and its two docstring lines (cascade: its only reader was `_cleanup_worktree`).
- `tests/unit/core/test_orchestrator.py`:
  - Delete `TestGetNextPhase` and `TestOrchestratorAbort`.
  - `TestWorktreeNoAutoDelete` (5 tests): replace the `orchestrator._cleanup_worktree = MagicMock()` mocks with `patch.object(WorktreeManager, "remove_worktree")`, and assert that isn't called. That keeps the "no auto-delete" invariant under test. In `test_cleanup_command_is_only_deletion_method`, update the docstring and comments to match.
  - `DocumentExtension(git_config, runs_dir)` becomes `DocumentExtension(runs_dir)` at L2227, 2336 and 2418.
- `tests/integration/test_document_phase.py:272,493`: `DocumentExtension(runs_dir)`.
- `tests/integration/cli/test_abort_integration.py`: delete `test_full_abort_flow_via_orchestrator`.
- `tests/unit/core/test_phase_runner.py`:
  - Delete the three `test_merge_configs_*` tests in `TestConfigMerging`. The `test_load_project_config_*` tests stay.
  - `store_text(` becomes `store(` in `test_diff_artifact_accessible_as_template_variable`.
  - `get_json(...)` becomes `json.loads(manager.get(...))` in `test_captures_tool_calls_as_artifact_if_present`.
- `tests/unit/core/test_artifact_manager.py`:
  - Delete `TestArtifactManagerText`, `TestArtifactManagerAutoDetect`, `TestArtifactPaths` and `TestArtifactPathsRunContextIntegration`.
  - In `TestArtifactManagerJSON`, keep `test_store_and_get_json`, rewritten to read back through `json.loads(manager.get(...))`, and delete the two `test_get_json_*` tests.
- `tests/integration/core/test_artifact_manager_integration.py`:
  - `store_text(` becomes `store(`, and `get_json(...)` becomes `json.loads(manager.get(...))`.
  - Delete `TestRunContextIntegration`, whose two tests exist only for `get_artifact_paths`.
- `tests/unit/core/test_run_directory.py`: delete the three `test_acquire_lock_*` tests in `TestFileLocking`, and the whole `TestRunListing`.
- `tests/integration/core/test_run_directory_integration.py`:
  - Delete `TestConcurrentAccess`.
  - In `test_complete_run_lifecycle`, `test_multiple_runs_workflow`, `test_special_characters_in_project_path` and `test_deeply_nested_project_path`, replace the `manager.list_runs()` checks with filesystem checks. Assert that `(runs_dir / run_id / "context.json").is_file()` for each created run id, and for the multi-run test, `sorted(p.name for p in runs_dir.iterdir()) == run_ids`.
- `tests/unit/core/test_stats_aggregator.py`: delete `TestGetTokenUsage`.
- `tests/integration/cli/test_global_stats_integration.py`: drop the `get_token_usage` stub from `_create_mock_aggregator_class`.
- `tests/unit/worktree/test_concurrent.py`: delete `test_unregister_run_removes_lock_file` and `test_unregister_run_nonexistent_is_safe`.

## Acceptance

- [ ] `grep -rnE "get_next_phase|_cleanup_worktree|\.abort\(|_merge_configs\(|ProgressCallback|store_text|get_auto|get_json|get_artifact_paths|acquire_lock|RunInfo|get_token_usage|_git_config|unregister_run|cleanup_branch_on_remove" src` returns nothing, and so does `grep -rn "RunDirectoryManager" src | grep list_runs`.
- [ ] `grep -rn "PR_DESCRIPTION_ARTIFACT" src` still shows `core/constants.py` and `cli/progress.py`, confirming the live constant stayed.
- [ ] `scripts/preflight.sh` passes.
- [ ] `uv run pytest tests/unit/core tests/unit/worktree tests/unit/models tests/integration/core tests/integration/cli tests/integration/test_document_phase.py -o addopts=""` passes.
- [ ] `TestWorktreeNoAutoDelete` fails when `remove_worktree` is called: a temporary one-line call to it in `Orchestrator.run` turns the tests red. Revert the call before committing.
- [ ] The `vulture` diff against this task's start shows no new entry, or each new entry is handled per the cascade rule.

Evidence: the empty greps, the pytest summary line, and the red run from the `remove_worktree` probe.

## Steps

### RED
- [ ] Save the `vulture` baseline.
- [ ] Retarget `TestWorktreeNoAutoDelete` onto `WorktreeManager.remove_worktree`. Confirm the retargeted tests pass at HEAD and go red with the temporary `remove_worktree` call. Then revert that call.

### GREEN
- [ ] Delete the orchestrator, phase_runner, artifact_manager, run_directory and stats_aggregator symbols, and the `RunInfo` re-export.
- [ ] Remove the `git_config` parameter from `DocumentExtension` and `create_default_registry`, and update `bootstrap` and the five test call sites.
- [ ] Delete `unregister_run` and `cleanup_branch_on_remove`.
- [ ] Delete or rewrite the tests listed under Files.
- [ ] Run the targeted pytest command.

### REFACTOR
- [ ] Run `uv run ruff check src/ --fix` and `uv run ruff format src/`.
- [ ] Take the `vulture` diff and apply the cascade rule.
- [ ] Run `scripts/preflight.sh`.

## Notes

- `PR_DESCRIPTION_ARTIFACT` is on the epic's list but `cli/progress.py:337,360` reads it, so it stays. Phase 1.7 reworks that code.
- `unregister_run` has no replacement. Every run is its own subprocess, and `get_active_runs` removes locks whose PID is gone. See RESEARCH.md.
- `WorktreeConfig` ignores unknown keys, so a `project.yaml` that still sets `cleanup_branch_on_remove` keeps loading.
