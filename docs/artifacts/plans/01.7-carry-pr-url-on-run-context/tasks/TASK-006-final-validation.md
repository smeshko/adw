# TASK-006: Final Validation

Depends on: all prior tasks
Suggested commit: `chore: final validation for 01.7-carry-pr-url-on-run-context`

## Goal

Confirm the plan is fully implemented and production-ready, and write the PR evidence to `docs/artifacts/plans/01.7-carry-pr-url-on-run-context/VALIDATION.md`, including one real `adw pr` against a private scratch GitHub repo.

## Steps

- [ ] All task checkboxes in `PLAN.md` are ticked.
- [ ] `scripts/preflight.sh` passes with no issues.
- [ ] Full test suite: `uv run pytest` is green with coverage ≥ 80%. Rerun `test_stats_display_with_real_data` once if it flakes (AGENTS.md).
- [ ] Module boundaries: `grep -rn "from adw.cli\|import adw.cli" src/adw/core/pr.py src/adw/core/extensions/document.py` returns nothing.
- [ ] The three phase greps from `PLAN.md` → Acceptance Criteria. Paste their (empty or expected) output into `VALIDATION.md`.
- [ ] **Regression evidence for the epic.** Each bug's test must fail on the pre-epic code. Paste the RED line recorded in its task:
  - B1: `test_auto_close_leaves_ticket_open_and_warns_once` (TASK-002)
  - B12: `test_pr_sets_pr_url` (TASK-005)
- [ ] **Real `gh`, no Claude.** Run this in the scratchpad directory, never in the checkout:
  1. `gh repo create adw-pr-scratch-<YYYYMMDD> --private --add-readme --clone`, then `cd` into it. Its default branch is `main`, so this also exercises the new default.
  2. `git checkout -b feature/pr-scratch`, then commit one file.
  3. Seed a completed run with this worktree's code:

     ```
     uv run --project <worktree> python -c '…'
     ```

     The snippet builds a `RunContext` with:
     - `status="completed"`
     - `branch_name="feature/pr-scratch"`
     - `worktree_path=<scratch repo>`
     - `phase_history=[…, "document"]`

     It saves the context through `ContextManager(Path(".adw/runs"))` after creating the run dir, and writes a valid `artifacts/document/pr_description.md` (Summary/Changes/Testing).
  4. `uv run --project <worktree> adw pr <run-id>`. Capture the output.
  5. Capture the evidence:
     - `jq .pr_url .adw/runs/<run-id>/context.json`
     - `gh pr view <url> --json baseRefName,headRefName,isDraft,url`, which should show `baseRefName: main` and `headRefName: feature/pr-scratch`
  6. Run `adw pr <run-id>` again. It must print the same URL without calling `gh`, and `gh pr list` must still show exactly one PR.
  7. Close the PR (`gh pr close <url>`). **Ask Ivo before deleting the scratch repo.** `gh repo delete` needs the `delete_repo` scope and can't be undone.
- [ ] Write `VALIDATION.md` with:
  - the preflight and full-suite summary lines
  - the greps
  - the B1 and B12 RED/GREEN lines
  - the real-run transcript (steps 4–6) and the `context.json` `pr_url` excerpt
- [ ] Every `PLAN.md` acceptance criterion is met with its evidence produced. None is ticked on "the code looks right".

### Epic update

- [ ] Tick phase 1.7's `### Acceptance criteria` in `docs/artifacts/epics/01-cleanup-safety-dead-code-bugs.md`. Next to the epic-level "Bugs B1–B5, B9–B12…" criterion, note that B1 and B12 now have regression tests (the criterion stays open until the epic closes).
- [ ] In `docs/artifacts/epics/04-plan-driven-runs.md`, change the Phase 1.7 dependency line to the landed signature `create_pr(context, body, *, base, draft=False)`, and state that the default base branch is `GitConfig.base_branch` (`main`).
- [ ] Mark the phase done: `python3 ~/.claude/skills/create-epic/scripts/link_plan.py 01 --phase 1.7 --plan 01.7-carry-pr-url-on-run-context --status done`.
- [ ] Epic 01's row in `docs/artifacts/epics/EPICS.md` stays `In progress`. This isn't the epic's last phase.
