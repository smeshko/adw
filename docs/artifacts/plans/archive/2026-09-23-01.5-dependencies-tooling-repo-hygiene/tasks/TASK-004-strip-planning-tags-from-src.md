# TASK-004: Strip planning tags from src

Depends on: None
Suggested commit: `docs: strip planning-ticket tags from src comments and help text`

## Goal

No comment, docstring, help string or template comment in `src/adw` cites a Story, ISS, Epic, UX, FR, NFR or AC tag. `adw run --help` and `adw pr --help` read clean, and no code behaviour changes.

## Files

Set `P='Story [0-9]|ISS-[0-9]|Epic [0-9]|\bUX-[A-Z0-9]|\bN?FR-?[0-9]+\b|\bAC ?#?[0-9]+\b|\bAC:'` (the tag pattern, reused by TASK-005). It matches 235 lines in 45 files: `git grep -nP "$P" -- src/adw`.

- Densest files: `core/run_lifecycle.py` (35), `core/orchestrator.py` (33), `core/phase_runner.py` (26), `cli/app.py` (24), `cli/bootstrap.py` (11).
- Runtime strings, which change user-visible output:
  - `cli/app.py:200`, the `--no-worktree` help: `"Run in current directory instead of isolated worktree"`.
  - `cli/app.py:242`, the `# Task manager integration (Story 12.4)` line inside the `run` docstring's example block, which `adw run --help` prints.
  - `cli/pr.py`: the module docstring and the command docstrings at ~95 and ~142 (`ISS-026: …`), which `adw pr --help` prints. Rewrite them as plain statements: "The base branch comes from `git.base_branch` in `project.yaml`."
  - `models/context.py:117`, the `RunContext.pr_url` `Field` description: `"… Set after document phase completes."`
- Non-Python files: `dashboard/static/dashboard.css`, `dashboard/templates/base.html`, `dashboard/templates/partials/{focus_mode,phase_detail,terminal_mode}.html` and `defaults/commands/plan/pre.sh`.
- History-only comments to rewrite or delete under the tag-rewrite rule (`PLAN.md` → Decisions):
  - `core/constants.py:13-16`: the `verify`-removed and `ship`-added NOTEs.
  - `core/run_lifecycle.py:~223-232`: "runs created before ISS-039".
  - `models/config.py:534`: "phases field removed in ISS-029".
  - `cli/app.py:484-515`: the `# Register the … command (Story N.M)` lines.
- Mixed tags on one line: drop every family at once. For example, `(Story 12.4 Task 4)`, `(UX-12, Story 6.1)`, `(Story UX-FIX-ISS-002)`, `(Story 7.2, ISS-003, ISS-006 fix)`.
- A stale note that the pattern misses: `cli/init.py:157-159`, the `_run_wizard_setup` docstring's `Note: Full implementation will be added in Task 4. For now, this is a stub…`. The function is fully implemented, so delete the Note.

Leave alone:
- the BMAD workflow files under `defaults/commands/` (`*.xml`, `*.md`, `*.yaml`)
- `ADR-001` references
- test-data IDs such as `ENG-42` and `RULE-123`

## Acceptance

- [ ] `git grep -nP "$P" -- src/adw` returns nothing, and so does the epic's `grep -rnE "Story [0-9]|ISS-[0-9]|Epic [0-9]" src/adw`.
- [ ] `uv run adw run --help | grep -niE "story|ISS-|epic|UX-"` and the same for `adw pr --help` print nothing.
- [ ] The AST check (see Notes) reports only `src/adw/cli/app.py` (the help string) and `src/adw/models/context.py` (the `Field` description) as changing anything beyond comments and docstrings.
- [ ] `git diff --stat -- src/adw` touches no file outside the pattern's file list plus `cli/init.py`.
- [ ] `scripts/preflight.sh` passes, and `uv run pytest` is green with coverage at or above 80%.

Evidence:
- the empty greps
- both `--help` greps
- the AST-check output
- the pytest summary line

## Steps

- [ ] Record the file list: `git grep -lP "$P" -- src/adw > "$S/src-tag-files.txt"`.
- [ ] Edit the files in that list one package at a time (`core`, `cli`, then the rest), applying the tag-rewrite rule. Keep line lengths within 88.
- [ ] Delete the stale Note in `cli/init.py`.
- [ ] Run the greps, the `--help` checks and the AST check.
- [ ] Run `scripts/preflight.sh`, then `uv run pytest`.

## Notes

- `$S` is the session scratchpad directory.
- AST check: save it as `$S/ast_check.py` and run it with `uv run python "$S/ast_check.py" src/adw`. It drops docstrings, then compares `ast.dump` for HEAD and the working tree. Comments never appear in the AST.

  ```python
  import ast, subprocess, sys
  def norm(src: str) -> str:
      tree = ast.parse(src)
      for n in ast.walk(tree):
          body = getattr(n, "body", None)
          if (isinstance(n, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
                  and body and isinstance(body[0], ast.Expr)
                  and isinstance(body[0].value, ast.Constant) and isinstance(body[0].value.value, str)):
              n.body = body[1:]  # drop docstrings, so edited and deleted ones compare equal
      return ast.dump(tree)
  files = subprocess.run(["git", "diff", "HEAD", "--name-only", "--", f"{sys.argv[1]}/*.py"],
                         capture_output=True, text=True, check=True).stdout.split()
  for f in files:
      old = subprocess.run(["git", "show", f"HEAD:{f}"], capture_output=True, text=True, check=True).stdout
      if norm(old) != norm(open(f).read()):
          print("non-comment change:", f)
  ```
- Parenthesised tags inside a sentence usually delete cleanly: `# Preserve worktree for debugging (ISS-020)` → `# Preserve worktree for debugging`. A bare trailing `# ISS-023` comment with nothing else goes entirely.
- Keep the "why" when the tag was the only hint of it. `# Validate branch before committing (ISS-025)` → `# Validate the branch before committing, so a mismatch never commits to the wrong branch`.
