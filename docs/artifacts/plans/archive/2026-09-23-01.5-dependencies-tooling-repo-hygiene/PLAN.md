# Plan: Dependencies, tooling and repo hygiene

Status: done
Branch: feature/adw-11
Risk: small
Epic: 01 — Cleanup: test safety, dead code and bug fixes ([epic](../../../epics/01-cleanup-safety-dead-code-bugs.md))
Phase: 1.5 — Dependencies, tooling and repo hygiene
Linear: ADW-11
Created: 2026-09-23

## Goal

After this phase:

- `adw` installs only the dependencies it uses: `typer` and `uvicorn` without extras.
- `pyproject.toml` carries no tool config for files, modules or markers that don't exist.
- `scripts/preflight.sh` and CI lint and format-check `tests/` as well as `src/`.
- Version bumps go through a thin `uv version` wrapper that updates `pyproject.toml` and `uv.lock` together. The install command is documented.
- Neither `src/adw` nor `tests` carries planning-ticket tags (Story/ISS/Epic/UX/FR/NFR/AC), so `adw --help` output is clean.
- The main checkout has no directories that hold only `__pycache__`.

## Scope

- `pyproject.toml` (TASK-001):
  - `typer[all]` → `typer`, `uvicorn[standard]` → `uvicorn`. Re-lock.
  - Delete the mypy overrides for `httpx`, `httpx.*`, `playwright` and `playwright.*`. Keep `markdown`, which has no stubs installed.
  - Delete the ruff per-file ignore for `src/adw/models/evidence.py`.
  - Delete the pytest `python_files`, `python_classes` and `python_functions` settings, and the `markers` list (`slow` and `integration`, which no test uses).
- `scripts/preflight.sh` and `.github/workflows/ci.yml` (TASK-002):
  - Run `ruff check src/ tests/` and `ruff format --check src/ tests/`.
  - The CI test step becomes `uv run pytest`, since `addopts` already sets the coverage flags.
  - Fix the one existing lint error in tests: `F401` in `tests/unit/cli/test_progress.py`.
- Release and install (TASK-003):
  - Replace `update.sh` with `scripts/bump.sh <major|minor|patch>`. It runs `uv version --bump`, then commits `pyproject.toml` and `uv.lock`. It doesn't push or install.
  - Document the bump and `uv tool install --editable .` in `AGENTS.md` and `README.md`.
- Strip planning tags from `src/adw` (TASK-004) and from `tests` (TASK-005): comments, docstrings, help text, a pydantic `Field` description, Jinja/CSS comments, `.sh` comments and one assertion message. The pattern is `Story [0-9]|ISS-[0-9]|Epic [0-9]|\bUX-[A-Z0-9]|\bN?FR-?[0-9]+\b|\bAC ?#?[0-9]+\b|\bAC:`. It matches 235 lines in 45 src files and 227 lines in 67 test files.
- Delete the `__pycache__`-only directories in the main checkout (TASK-006). This is local housekeeping, outside git.

## Out of Scope

- The audit bug IDs `(B3)`, `(B11)` and so on in regression-test docstrings. The epic-level AC traces B1–B21 through those tests, so they stay until Epic 01 closes.
- BMAD-derived workflow content under `src/adw/defaults/commands/`: the `epics/epic-3.md` example in `workflow.xml`, and the `dev-story/` and `create-story/` directory names. The epic excludes rewriting these.
- Tags in `docs/`: architecture docs, epics and archived plans record history.
- The run-id literal `01HQTEST_ISS008_INTEGRATION` in `tests/integration/worktree/test_worktree_cleanup_integration.py`. It's fixture data, not a tag.
- Deleting `defaults/commands/plan/pre.sh` (phase 1.9). This plan only strips its two tag comments.
- The other ruff per-file ignores (`cli/logs.py`, `models/__init__.py`), release tagging and PyPI publishing.

## Research Summary

- **Extras:** typer 0.21's lock entry has no extras; it already depends on `rich` and `shellingham`. `uvicorn[standard]` is the only thing that pulls `httptools`, `uvloop`, `watchfiles` and `websockets`. Nothing in `src` imports any of them. The dashboard's SSE is a plain `StreamingResponse`. uvicorn 0.40 falls back to `StatReload` when `watchfiles` is missing (`uvicorn/supervisors/__init__.py`), so `adw dashboard web --reload` and `adw webhook … --reload` keep working.
- **Tool config:** `httpx` ships `py.typed`. `playwright` isn't imported anywhere. `src/adw/models/evidence.py` doesn't exist. No test uses `pytest.mark.slow` or `pytest.mark.integration`. No `*_test.py` file exists, so dropping `python_files` (default `test_*.py *_test.py`) collects the same tests.
- **Tests lint:** `ruff check tests/` reports 1 error (`F401`, `tests/unit/cli/test_progress.py:10`), and `ruff format --check tests/` reports 209 files already formatted.
- **update.sh:** it edits only `pyproject.toml`, leaving `uv.lock`'s `adw` version behind. It pushes directly, and it runs `pip install -e .` into whichever pip is first on PATH. Today that's conda: `/opt/homebrew/Caskroom/miniconda/base/bin/adw`, an editable install of the main checkout. `~/.local/bin` comes before the conda bin on PATH, so a `uv tool install` shim wins. `uv 0.8.22` supports `uv version --bump`.
- **Tags in help output:** `adw run --help` shows `(Story 10.1)` from the `--no-worktree` help string and `(Story 12.4)` from a docstring example. `adw pr --help` shows `ISS-026` from the command docstring.
- **`__pycache__`-only directories in the main checkout:** `src/adw/evidence`, `src/adw/utils`, `src/adw/validation/validators`, `tests/unit/evidence`, `tests/unit/utils`, `tests/unit/ship` and `tests/unit/validation/validators`. Their parents `src/adw/validation` and `tests/unit/validation` hold nothing else either.

## Decisions

See [DECISIONS.md](./DECISIONS.md) for the three choices that weighed real options: the `uvicorn` extras, the `update.sh` replacement, and the tag scope. Other rules:

- **The tag-rewrite rule:**
  - Drop the tag and keep the sentence.
  - When what's left only narrates history ("added in", "removed in", "runs created before X"), rewrite it to state today's behaviour, or delete it if it adds nothing.
  - Runtime strings follow the same rule: help text, `Field` descriptions and assertion messages.
  - No behavioural code changes.
- **All tasks are `checklist`, not RED/GREEN.** The changes are config, tooling and comment edits. ADR-001 rules out help-text tests. Runtime commands prove each behaviour: clean-clone sync, `--help` output, a scratch-clone bump, an isolated install.
- **Install evidence comes from an isolated uv tool dir** (`UV_TOOL_DIR`/`UV_TOOL_BIN_DIR` under the scratchpad), so validation never touches the real install. Switching the real install happens after merge (user's choice). See [Post-merge](#post-merge).

## Risks

- **A tag edit changes a string that a test asserts on.** Mitigation: the only runtime strings are the `--no-worktree` help, the `RunContext.pr_url` `Field` description and one assertion message. TASK-004 and TASK-005 each end with the full suite.
- **Re-locking changes pins beyond the removed extras.** Mitigation: TASK-001 runs `uv lock` without `--upgrade`, and checks that `git diff uv.lock` only removes packages and extras metadata.
- **`scripts/bump.sh` pushes or commits into the real repo during its demonstration.** Mitigation: it has no push, and TASK-003 runs it only in a scratch `git clone`.
- **Conflicts with phase 1.3 (exception and re-export trims) and 1.9 (hook scripts), which touch some of the same files.** Mitigation: these hunks are comment-only and small, so a rebase is mechanical.

## Acceptance Criteria

- [x] `uv sync --locked` and `scripts/preflight.sh` pass on a clean clone. Evidence: transcript from a `git clone` of the branch into the scratchpad.
- [x] `uv.lock` no longer lists `httptools`, `uvloop`, `watchfiles` or `websockets`, and `adw dashboard web --reload --no-browser` still serves `/`. Evidence: `grep -c` on `uv.lock`, the `StatReload` startup line, and `curl -s -o /dev/null -w '%{http_code}'` returning `200`.
- [x] `uv run pytest --collect-only -q | tail -1` gives the same count before and after the pytest-config trim.
- [x] `scripts/preflight.sh` and the CI lint job both check `tests/`, and the CI test step runs a bare `uv run pytest`. Evidence: the diff, plus preflight output showing the `tests/` checks.
- [x] `update.sh` is gone. In a scratch clone, `scripts/bump.sh patch` makes one commit that changes only `pyproject.toml` and `uv.lock` to the next patch version, and `uv sync --locked` passes afterwards.
- [x] The documented install command gives an `adw` whose `adw --version` matches `pyproject.toml`. Evidence: `which adw && adw --version` with the isolated tool bin dir first on `PATH`.
- [x] `git grep -nP 'Story [0-9]|ISS-[0-9]|Epic [0-9]|\bUX-[A-Z0-9]|\bN?FR-?[0-9]+\b|\bAC ?#?[0-9]+\b|\bAC:' -- src/adw tests` returns nothing. This covers the epic's `grep -rnE "Story [0-9]|ISS-[0-9]|Epic [0-9]" src/adw`.
- [x] `adw run --help` and `adw pr --help` show no tag.
- [x] The main checkout has no directory under `src/` or `tests/` that holds only `__pycache__`.
- [x] `uv run pytest` is green with coverage at or above 80%.

## Post-merge

After the PR merges and the main checkout is on the updated `staging` (user's choice), switch the real install to the documented path:

1. `/opt/homebrew/Caskroom/miniconda/base/bin/pip uninstall -y adw`
2. From the main checkout (`/Users/A1E6E98/Developer/Projects/adw/adw-final`): `uv tool install --editable .`
3. Check `which adw && adw --version`. It should print `~/.local/bin/adw` and the `pyproject.toml` version.

## Tasks

Task state lives here. Tasks are appended by `scripts/add_task.py` and
`scripts/add_final_task.py`. Update the checkboxes as work progresses.

- [x] TASK-001: Drop unused dependency extras and stale tool config
- [x] TASK-002: Lint and format tests in preflight and CI
- [x] TASK-003: Replace update.sh with a uv version-bump script
- [x] TASK-004: Strip planning tags from src
- [x] TASK-005: Strip planning tags from tests (depends on TASK-004)
- [x] TASK-006: Final Validation
