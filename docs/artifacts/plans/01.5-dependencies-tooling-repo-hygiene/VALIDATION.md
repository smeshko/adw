# Validation: Dependencies, tooling and repo hygiene

Validated: 2026-09-23, first at `9a525ebe`, then again after rebasing onto `staging` at `f949798e`, which brought in PRs #208, #209 and #211. Numbers are from the rebased tree unless marked otherwise.

| Criterion | Result |
|---|---|
| `uv sync --locked` and `scripts/preflight.sh` pass on a clean clone | Met: transcript below |
| `uv.lock` drops `httptools`, `uvloop`, `watchfiles`, `websockets`; `--reload` dashboard still serves `/` | Met: `grep -c` prints `0`, `StatReload`, `200` |
| Collect-only count unchanged by the pytest-config trim | Met: 3822 before and after on the original base; 3735 on the rebased tree, with or without the old settings |
| Preflight and CI lint check `tests/`; CI test step is a bare `uv run pytest` | Met: diff and preflight output below |
| `update.sh` gone; `scripts/bump.sh patch` in a scratch clone makes one commit touching only `pyproject.toml` and `uv.lock` | Met: transcript below |
| The documented install gives an `adw` whose `--version` matches `pyproject.toml` | Met: `0.1.67` both |
| The tag grep over `src/adw tests` returns nothing | Met: empty, and so is the epic's grep |
| `adw run --help` and `adw pr --help` show no tag | Met: both greps empty |
| No `__pycache__`-only directory under `src/` or `tests/` in the main checkout | Met: before/after listing below |
| `uv run pytest` green, coverage ≥ 80% | Met: 3730 passed, 5 skipped, 85.56% |

## Clean clone

```
$ git clone -q <worktree> "$S/clean-clone" && git -C "$S/clean-clone" checkout feature/adw-11
aea7cdd9 chore: finalize 01.5-dependencies-tooling-repo-hygiene
$ uv sync --locked
exit=0
$ scripts/preflight.sh
==> ruff check
All checks passed!
==> ruff format --check
365 files already formatted
==> mypy
Success: no issues found in 153 source files
preflight: ok
exit=0
```

`ruff format --check` covers 365 files, `src/` (153) plus `tests/` (212). Before TASK-002 it covered only `src/`.

## Dependencies and tool config (TASK-001)

```
$ uv lock
Removed httptools v0.7.1
Removed uvloop v0.22.1
Removed watchfiles v1.1.1
Removed websockets v16.0
$ git diff --stat uv.lock
 uv.lock | 158 ++--------------------------------------------------------------
 1 file changed, 3 insertions(+), 155 deletions(-)
$ git diff uv.lock | grep '^+' | grep -v '^+++'
+    { name = "uvicorn" },
+    { name = "typer", specifier = ">=0.21.0" },
+    { name = "uvicorn", specifier = ">=0.32.0" },
$ grep -cE '^name = "(httptools|uvloop|watchfiles|websockets)"' uv.lock
0
```

The three `+` lines are the `typer`/`uvicorn` requirement lines, with the `extra`/`extras` markers dropped. No package changed version.

```
$ uv run mypy src/adw          # without the httpx override
Success: no issues found in 154 source files
$ uv run pytest --collect-only -q | tail -1     # before the edit
======================== 3822 tests collected in 10.65s ========================
$ uv run pytest --collect-only -q | tail -1     # after, on the original base
======================== 3822 tests collected in 4.04s =========================
$ uv run pytest --collect-only -q | tail -1     # rebased tree
======================== 3735 tests collected in 6.28s =========================
$ uv run pytest --collect-only -q -o python_files='test_*.py' -o python_classes='Test*' -o python_functions='test_*' | tail -1
======================== 3735 tests collected in 3.47s =========================
$ adw dashboard web --reload --no-browser --port 8199 ; curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8199/
INFO:     Started reloader process [60910] using StatReload
http_code=200
(server stopped, port 8199 free)
```

## Lint scope and CI (TASK-002)

```diff
       - name: Run ruff linting
-        run: uv run ruff check src/
+        run: uv run ruff check src/ tests/

       - name: Run ruff format check
-        run: uv run ruff format --check src/
+        run: uv run ruff format --check src/ tests/
 ...
       - name: Run pytest with coverage
-        run: uv run pytest --cov=adw --cov-report=term-missing --cov-fail-under=80
+        run: uv run pytest
```

With `import os` planted in `tests/unit/cli/test_progress.py`, preflight fails on it, and the plant is reverted before staging:

```
==> ruff check
F401 [*] `os` imported but unused
  --> tests/unit/cli/test_progress.py:8:8
planted preflight exit=1
```

A bare `uv run pytest` still enforces the gate through `addopts`: `Required test coverage of 80% reached. Total coverage: 85.04%`.

## Version bump and install (TASK-003)

`scripts/bump.sh` was run only in a scratch clone of the branch:

```
$ scripts/bump.sh patch
adw 0.1.67 => 0.1.68
[feature/adw-11 76c1320d] chore: bump version to 0.1.68
 2 files changed, 2 insertions(+), 2 deletions(-)
$ git show --stat --format='%s' HEAD
chore: bump version to 0.1.68

 pyproject.toml | 2 +-
 uv.lock        | 2 +-
$ grep '^version' pyproject.toml; grep -A1 '^name = "adw"' uv.lock
version = "0.1.68"
name = "adw"
version = "0.1.68"
$ uv sync --locked
exit=0
$ scripts/bump.sh bogus
usage: scripts/bump.sh [major|minor|patch]
exit=1
$ echo >> pyproject.toml; scripts/bump.sh
bump: pyproject.toml or uv.lock has uncommitted changes; commit or revert them first
exit=1
HEAD unchanged: 76c1320d chore: bump version to 0.1.68
```

`git grep -nF "update.sh" -- ':!docs/artifacts/'` returns nothing.

The documented install, into an isolated tool dir, with its bin dir first on `PATH`:

```
$ UV_TOOL_DIR="$T/tools" UV_TOOL_BIN_DIR="$T/bin" uv tool install --editable .
$ PATH="$T/bin:$PATH" sh -c 'which adw && adw --version'; grep '^version' pyproject.toml
$S/uvtool/bin/adw
adw version 0.1.67
version = "0.1.67"
```

The tool dir was uninstalled and removed afterwards. `~/.local/bin/adw` doesn't exist, so the real install is untouched.

## Planning tags (TASK-004, TASK-005)

```
$ git grep -nP 'Story [0-9]|ISS-[0-9]|Epic [0-9]|\bUX-[A-Z0-9]|\bN?FR-?[0-9]+\b|\bAC ?#?[0-9]+\b|\bAC:' -- src/adw tests
(empty, exit 1)
$ grep -rnE "Story [0-9]|ISS-[0-9]|Epic [0-9]" src/adw
(empty, exit 1)
$ uv run adw run --help | grep -niE "story|ISS-|epic|UX-"
(empty, exit 1)
$ uv run adw pr --help | grep -niE "story|ISS-|epic|UX-"
(empty, exit 1)
```

Before: 235 lines in 45 `src` files, and 227 lines in 67 test files. Each commit touches only the files the pattern listed, plus `cli/init.py` for the stale stub note.

The rebase onto `staging` conflicted in several files:

- #208 deleted `tests/unit/cli/test_dashboard.py`, and #209 deleted `defaults/commands/plan/pre.sh`. Both deletions stand.
- #211 rewrote `commands/template.py`, `core/phase_runner.py` and `tests/unit/commands/test_template.py`, and #209 refactored `core/run_lifecycle.py` and two integration tests. Each takes the `staging` version with the tag strip re-applied. `template.py` had no tags left. #209 had added three new tags, in `run_lifecycle.py`, `test_progress_integration.py` and `test_orchestrator_integration.py`, and those are stripped too.
- #209 moved `test_progress_integration.py` onto a real git repo, so its `enabled=False` comments now give #209's reason, `# no remote to fetch`, rather than `tmp_path is not a git repo`.

The AST check drops docstrings and compares `ast.dump` at HEAD and in the working tree. It reported only the planned runtime-string changes:

```
$ uv run python "$S/ast_check.py" src/adw
non-comment change: src/adw/cli/app.py          # --no-worktree help
non-comment change: src/adw/models/context.py   # RunContext.pr_url Field description
non-comment change: src/adw/models/llm.py
$ uv run python "$S/ast_check.py" tests
non-comment change: tests/integration/cli/test_run_integration.py   # startup-time assertion message
```

Re-run against `origin/staging` on the rebased tree, with attribute docstrings stripped too: `src` reports `cli/app.py` and `models/context.py`, and `tests` reports `test_run_integration.py` plus `tests/unit/cli/test_progress.py`, where TASK-002 removed an unused import.

`models/llm.py` is a false positive. The edit is to the attribute docstring under `LLMResult.final_output`, which the script doesn't strip because it isn't a node's first statement. Pydantic ignores it: `use_attribute_docstrings` isn't set anywhere in `src`. A variant of the script that strips every bare string statement reports only `cli/app.py` and `models/context.py`.

The `(Bn)` audit IDs survive in `tests`: 9 before and after on the original base, 11 on `staging` and on the rebased tree, since #209 added two. So does the run-id literal `01HQTEST_ISS008_INTEGRATION`.

## Preflight and suite

```
$ scripts/preflight.sh
==> ruff check
All checks passed!
==> ruff format --check
365 files already formatted
==> mypy
Success: no issues found in 153 source files
preflight: ok

$ uv run pytest
Required test coverage of 80% reached. Total coverage: 85.56%
================= 3730 passed, 5 skipped in 202.42s (0:03:22) ==================
```

## Main-checkout housekeeping

Run in `/Users/A1E6E98/Developer/Projects/adw/adw-final`, outside git. The deleted directories held only `.pyc` files, none of them tracked.

```
$ for d in $(find src tests -type d ! -name __pycache__ ! -path '*/__pycache__/*'); do
    [ "$(find "$d" -mindepth 1 -maxdepth 1 ! -name __pycache__ | wc -l)" -eq 0 ] && echo "$d"
  done; true
tests/unit/evidence
tests/unit/utils
tests/unit/ship
src/adw/evidence
src/adw/utils
tests/unit/validation/validators
src/adw/validation/validators

$ rm -rf <each of the above>, then the emptied parents src/adw/validation and tests/unit/validation
$ <same loop>
(empty)
$ git status --short
(empty)
```

## Size

`find src -name '*.py' | xargs cat | wc -l`: 42,102 at `staging` `f949798e` → 42,085 (−17). Against the original base `be1d5bf8` it was 43,445 → 43,420 (−25). #208 deleted some of the tagged lines first.

## Notes

- **Tags outside the pattern:** two tags in files already in the list were stripped too: `(Story ADW-6)` in `cli/app.py` and `(Story ISS-XXX)` in `core/orchestrator.py`. The pattern needs a digit after `Story `, so it misses both.
- **Bare `Task N` references remain in tests:** for example `"""Tests for Task 1: Template Engine Module Structure."""` in `tests/unit/commands/test_template.py`, and more in `tests/unit/commands/test_resolver*.py`. They fall outside this plan's tag families, so they're a follow-up.
- **`uv tool install` doesn't read `uv.lock`:** it resolves dependencies fresh. The isolated install picked up uvicorn 0.53.0, while the lock pins 0.40.0.

## Post-merge

After the PR merges and the main checkout is on the updated `staging`:

1. `/opt/homebrew/Caskroom/miniconda/base/bin/pip uninstall -y adw`
2. From `/Users/A1E6E98/Developer/Projects/adw/adw-final`: `uv tool install --editable .`
3. `which adw && adw --version` should print `~/.local/bin/adw` and the `pyproject.toml` version.
