# Validation: Cut test waste outside the dashboard

Measured on `feature/adw-10` at `0a6ca43a` on 2026-09-23. The baseline is `f61f8873`, per `RESEARCH.md`.

## Summary

| Check | Before | After |
|---|---|---|
| Collected tests | 4,296 | **4,124** (−172) |
| Full run | 4,291 passed, 5 skipped | 4,119 passed, 5 skipped |
| Coverage | 84.33 % | **84.34 %** |
| `pass`-only test bodies | 52 | **0** |
| `git_repo` definitions | 7 | 1 |
| `executor` definitions | 13 | 2 |
| `sample_context` definitions | 21 | 15 |
| `src/` files changed | — | 0 |

## Test count

```
$ uv run pytest --collect-only -q -o addopts="" | tail -1
4296 tests collected in 1.38s     # before (f61f8873)
4124 tests collected in 3.68s     # after  (0a6ca43a)
```

Per task: 4,296 → 4,186 (TASK-001) → 4,131 (TASK-002) → 4,130 (TASK-003) → 4,130 (TASK-004) → 4,124 (TASK-005). Each figure matches the task's expected count.

## Full suite and coverage

```
$ uv run pytest
TOTAL                                    13593   1853   3882    408    84%
Required test coverage of 80% reached. Total coverage: 84.34%
================= 4119 passed, 5 skipped in 213.75s (0:03:33) ==================
```

Baseline: `TOTAL 13593 1855 3882 408 84%`, 84.33 %. Coverage rose by 0.01 pt.

## Lint gates

```
$ scripts/preflight.sh
All checks passed!
166 files already formatted
Success: no issues found in 166 source files
preflight: ok
$ uv run ruff check tests/ && uv run ruff format --check tests/
All checks passed!
223 files already formatted
```

`git diff --stat origin/staging... -- src/` is empty.

## Bundled-phase check: RED (TASK-001)

Both temporary mutations were reverted with `git checkout`, and `git status --short src/` was empty afterwards.

```
mutation 1: `bogus_key: 1` appended to src/adw/defaults/commands/validate/config.yaml
E         Extra inputs are not permitted [type=extra_forbidden, input_value=1, input_type=int]
FAILED tests/unit/commands/test_bundled_commands.py::test_bundled_phase_files_are_well_formed[validate]
1 failed, 7 passed in 0.09s

mutation 2: last line (`</workflow>`) removed from src/adw/defaults/commands/ship/instructions.xml
E                   xml.etree.ElementTree.ParseError: no element found: line 1082, column 0
FAILED tests/unit/commands/test_bundled_commands.py::test_bundled_phase_files_are_well_formed[ship]
1 failed, 7 passed in 0.10s
```

GREEN: `test_bundled_phase_files_are_well_formed[plan|build|validate|document|ship]` and the three `test_resolve_bundled_*` tests, 8 passed.

## Placeholders

The pass-only AST scan (`RESEARCH.md` → Useful Commands):

```
# before
16 tests/unit/ship/test_command_execution.py
36 tests/unit/ship/test_failure_diagnosis.py
total 52
# after
total 0
```

`grep -rn "^\s*pass$" tests/unit` returns the 11 lines listed in `RESEARCH.md`. An AST lookup of each hit's direct parent shows that none is a test function body:

```
tests/unit/webhook/providers/test_base.py:78     ClassDef TestClass
tests/unit/core/test_context_manager.py:463      FunctionDef __exit__
tests/unit/core/test_run_directory.py:140        With
tests/unit/task_managers/test_base.py:53         FunctionDef update_status
tests/unit/task_managers/test_base.py:59         FunctionDef close_task
tests/unit/task_managers/test_base.py:65         FunctionDef add_label
tests/unit/task_managers/test_base.py:68         FunctionDef remove_label
tests/unit/task_managers/test_base.py:71         FunctionDef post_comment
tests/unit/executors/test_protocol.py:35         ClassDef BadExecutor
tests/unit/commands/test_template.py:534         ClassDef CustomObject
tests/unit/logging/test_manager.py:63            FunctionDef write
```

## Fixtures

The duplicate-fixture scan (`RESEARCH.md` → Useful Commands), after:

```
executor e3291a 2
    tests/integration/conftest.py:10
    tests/unit/executors/test_claude_code.py:27
git_repo 513ea1 1
    tests/conftest.py:68
sample_context 2b1f6c 1
    tests/integration/core/test_snapshot_integration.py:26
sample_context ac90f7 1
    tests/unit/core/test_snapshot_manager.py:26
```

Before: `git_repo` had 7 definitions in 5 hash groups. `sample_context 2b1f6c` had 8 entries, 7 of them in `test_snapshot_manager.py`.

The plan expected `sample_context 2b1f6c ×2`. The scan hashes the argument list, so the new module-level fixture (no `self`) hashes as `ac90f7`. Its body is identical to the integration copy's: a body-only hash gives `b15c52` for both. `sample_context` totals 15 definitions.

The five files that TASK-004 touched: 80 passed before the change and 80 after.

## `claude_code.py` branch coverage (TASK-005)

`uv run pytest tests/unit/executors tests/integration -o addopts="" --cov=adw.executors.claude_code --cov-branch --cov-report=term-missing`:

```
# before: 398 passed, 5 skipped
src/adw/executors/claude_code.py  233  29  94  13  85%   252->256, 258, 286-299, 369, 436->431, 472, 474->404, 529, 531->536, 537, 559, 626-632, 651-652, 655, 667-673
# after: 389 passed, 5 skipped
src/adw/executors/claude_code.py  233  29  94  13  85%   252->256, 258, 286-299, 369, 436->431, 472, 474->404, 529, 531->536, 537, 559, 626-632, 651-652, 655, 667-673
```

The missing-lines lists are identical, so `417-418`, `461->404`, `467->404` and `477->404` are still covered. `TestResolveTimeout` in `tests/unit/hooks/test_runner.py`: 3 passed.

## No-touch check

`git status --short`, `git branch` and `git worktree list --porcelain` (paths and branches) were identical before and after the full run.

## Deviations from the plan

- **Branch:** the plan ran on the existing worktree branch `feature/adw-10`, rebased onto `origin/staging`. Plan 01.1 did the same with `feature/adw-7`. The plan did not cut a new `feature/adw-10-01.4-cut-test-waste`.
- **TASK-003:** the task's second grep also matches `"llm"` as a run-directory name and as a config section (60+ unrelated lines). The narrower check, `grep -rn fixtures tests | grep -E "llm|configs|runs|minimal.yaml|…"`, returns nothing.
- **TASK-004:** see the `ac90f7` note under Fixtures.
- **TASK-006:** the commit subject is shortened to `docs(adr): add markup, prose and placeholder tests to ADR-001` to stay under 72 characters.
