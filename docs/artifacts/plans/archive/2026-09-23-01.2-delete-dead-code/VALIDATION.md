# Validation: Delete dead modules and symbols

Validated: 2026-09-23 at `31e81e5d`. CI is green on every task commit of PR #206.

| Criterion | Result |
|---|---|
| `grep -rn "adw.validation\|adw.utils\|jsonschema\|CommandLoader" src tests pyproject.toml` is empty | Met |
| The plan's symbol grep over `src` is empty | Met, with `find_hook` matched as a word (below) |
| `vulture` at HEAD reports no entry that the pre-plan code lacked | Met: one new entry, `MockExecutor.call_count`, kept by the plan's rule (below) |
| `scripts/preflight.sh` passes; `uv run pytest` green, coverage ≥ 80% | Met: 4039 passed, 5 skipped, 84.09% |
| Scratch repo: `adw run --dry-run "noop"` lists all five phases | Met: transcript below |
| Scratch repo: `adw validate` shows plan…ship `OK` | Met: transcript below |
| `src` shrinks by ≥ 2,000 lines from 46,993 | Met: 46,993 → 44,596 (**−2,397**) |

## Greps

```
$ grep -rn "adw.validation\|adw.utils\|jsonschema\|CommandLoader" src tests pyproject.toml
(empty, exit 1)

$ grep -rnE "LoadedCommand|SchemaValidator|escape_feature_description|\bfind_hook\b|get_next_phase|SessionContext|ProjectContext|ArtifactType|from_yaml_file|cleanup_branch_on_remove|unregister_run|json_schema_extra" src
(empty, exit 1)
```

The plan writes the symbol grep with a bare `find_hook`, which also matches `CommandResolver._find_hook_path` in `commands/resolver.py`. That method is the live hook lookup, and TASK-006 keeps it on purpose, so the grep above matches `find_hook` as a whole word.

Two per-task greps have the same kind of substring match, and the matches are expected:

- TASK-004's `\.abort\(` matches the vendored `dashboard/static/htmx.min.js` (`xhr.abort()`), and its `get_json` matches `PRDescription.get_json_schema`, a different method.
- TASK-006's `all_prompts` matches `MockExecutor._all_prompts`, which `call_count` reads.

## Dead-code check

`vulture --min-confidence 60`, run on `src` at the merge base `7e8b06db` and at HEAD, with line numbers stripped:

```
base: 227 entries    HEAD: 174 entries

$ comm -13 vb.txt vh.txt
src/adw/executors/mock.py: unused property 'call_count' (60% confidence)
```

### Kept

| Entry | Why it stays |
|---|---|
| `MockExecutor.call_count` | `MockExecutor` is a test double, so its API is live while a test uses it. `tests/unit/executors/test_retry.py` asserts on `call_count` 3 times. Phase 1.6 deletes that file. |

Every other entry that a task's `vulture` diff reported was deleted in that task. TASK-001 to TASK-005 each reported no new entry.

## Preflight and suite

```
$ scripts/preflight.sh
==> ruff check
All checks passed!
==> ruff format --check
156 files already formatted
==> mypy
Success: no issues found in 156 source files
preflight: ok

$ uv run pytest
Required test coverage of 80% reached. Total coverage: 84.09%
================= 4039 passed, 5 skipped in 199.79s (0:03:19) ==================
```

`uv run python -c "import adw.cli.app, adw.dashboard.routes, adw.models, adw.core"` exits 0.

## Smoke test in a scratch repo

A fresh `git init` repository with `HOME` set to a scratch directory:

```
$ adw run --dry-run "noop"
              Phases to Execute
┏━━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━━┓
┃ Phase    ┃ Enabled ┃ Pre-Hook ┃ Post-Hook ┃
┡━━━━━━━━━━╇━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━━┩
│ plan     │ ✓       │ pre.sh   │ —         │
│ build    │ ✓       │ —        │ post.sh   │
│ validate │ ✓       │ —        │ —         │
│ document │ ✓       │ —        │ post.sh   │
│ ship     │ ✓       │ pre.sh   │ post.sh   │
└──────────┴─────────┴──────────┴───────────┘
Dry run mode - no execution will occur
exit=0

$ adw validate
  .adw/project.yaml ....................... 1 error
  plan .................................... OK
  build ................................... OK
  validate ................................ OK
  document ................................ OK
  ship .................................... OK
    ✗ Project config file not found
  Result: 1 error, 0 warnings — configuration has errors
exit=1
```

`adw validate` is the only CLI path that calls the moved `get_config_class` for every phase. Its one error is the missing `.adw/project.yaml` in a bare repository, which RESEARCH.md expected. The evidence is the five phase rows.

## Size

`find src -name '*.py' | xargs cat | wc -l`:

| Point | Lines |
|---|---|
| Epic baseline `cdb2003f` | 47,016 |
| Before TASK-001 | 46,993 |
| HEAD | 44,596 |

This phase removes 2,397 lines of `src`. Against the epic baseline the total is −2,420, so the epic's 3,000-line target still needs about 580 more.

## Divergences from the tasks

- **Branch.** The plan branch is the worktree's `feature/adw-8`, the repo's convention (phase 1.1 used `feature/adw-7`), rebased onto `origin/staging`. `prepare_branch.sh` was not run.
- **TASK-001.** Deleting `src/adw/validation` left a directory holding only `__pycache__`. It was removed so Python couldn't import it as a namespace package.
- **TASK-003.** `test_resolved_command_has_pre_hook_paths_list` was renamed to `test_resolved_command_pre_hook_paths_is_list`, so the task's `has_pre_hook` grep over `tests` returns nothing.
- **TASK-004.**
  - `test_runs_persist_after_manager_recreated` also called `list_runs()`, and the task's list of callers missed it. It now checks the runs directory, like the other four.
  - The `remove_worktree` probe ran twice. In `Orchestrator.run`, it turned the 3 run-based guards red. On the shared `_execute_phase_with_transitions` path, it turned all 5 guards red. Both probes were reverted, and the diff was checked empty.
  - `test_cleanup_command_is_only_deletion_method` points the mocked manager's `remove_worktree` at the same patched mock, so a call on either path counts.
- **TASK-005.** The module docstring of `tests/unit/models/test_context.py` named the deleted classes and was updated.
