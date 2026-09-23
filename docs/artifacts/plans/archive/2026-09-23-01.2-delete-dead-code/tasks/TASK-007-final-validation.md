# TASK-007: Final Validation

Depends on: all prior tasks
Suggested commit: `chore: final validation for 01.2-delete-dead-code`

## Goal

Confirm the plan is fully implemented and production-ready.

## Steps

- [ ] All task checkboxes in `PLAN.md` are ticked
- [ ] Project analyzer/linter passes with no issues: `scripts/preflight.sh`
- [ ] Full test suite passes: `uv run pytest` is green with coverage ≥ 80%. If `test_stats_display_with_real_data` fails, rerun it once, as `AGENTS.md` says.
- [ ] Module/import boundaries respected: `uv run python -c "import adw.cli.app, adw.dashboard.routes, adw.models, adw.core"` exits 0
- [ ] The epic's grep returns nothing: `grep -rn "adw.validation\|adw.utils\|jsonschema\|CommandLoader" src tests pyproject.toml`
- [ ] The plan's symbol grep (`PLAN.md` Acceptance Criteria, second bullet) returns nothing
- [ ] Nothing new is dead. Rebuild the baseline from the commit before TASK-001, compare it with HEAD, and expect empty output:

  ```bash
  mkdir -p "$SCRATCH/base" && git archive "$(git merge-base HEAD origin/staging)" src | tar -x -C "$SCRATCH/base"
  uvx vulture "$SCRATCH/base/src/adw" --min-confidence 60 | sed -E 's/^[^ ]*src\/adw/src\/adw/; s/:[0-9]+:/:/' | sort > "$SCRATCH/vb.txt"
  uvx vulture src/adw --min-confidence 60 | sed -E 's/:[0-9]+:/:/' | sort > "$SCRATCH/vh.txt"
  comm -13 "$SCRATCH/vb.txt" "$SCRATCH/vh.txt"
  ```

- [ ] Manual smoke test performed in a scratch repo with `HOME` set to a scratch dir (commands in `RESEARCH.md`):
  - `adw run --dry-run "noop"` lists plan, build, validate, document and ship.
  - `adw validate` shows all five phase rows as `OK`.
- [ ] LOC: `find src -name '*.py' | xargs cat | wc -l` is at most 44,993, a drop of at least 2,000 from 46,993
- [ ] Write `docs/artifacts/plans/01.2-delete-dead-code/VALIDATION.md` with:
  - a table of each acceptance criterion and its evidence
  - the preflight output and the pytest summary and coverage lines
  - both greps, the `vulture` diff, and the LOC before/after
  - the dry-run and `adw validate` transcripts
  - the "kept" list from the tasks' cascade reviews
- [ ] `PLAN.md` acceptance criteria all met, each with its Evidence produced (test output, screenshot, log) — no criterion ticked on "the code looks right"

### Epic update (only if `PLAN.md`'s `Epic:`/`Phase:` are not `none`)

- [ ] In `docs/artifacts/epics/01-cleanup-safety-dead-code-bugs.md`:
  - Tick phase 1.2's `### Acceptance criteria`.
  - The dry-run criterion's evidence is the dry-run plus the `adw validate` transcript.
  - On the epic-level LOC criterion, note this phase's progress (46,993 → N), as phase 1.1 did for timing.
- [ ] In phase 1.3's "Delete from `exceptions.py`" list, mark `ValidationError` as already deleted by phase 1.2 (TASK-002)
- [ ] Mark the phase done: `python3 ~/.claude/skills/create-epic/scripts/link_plan.py 01 --phase 1.2 --plan 01.2-delete-dead-code --status done`
- [ ] Update the epic's row in `docs/artifacts/epics/EPICS.md`:
  - `In progress` after the first phase merges; `Done` when this is the last phase.
  - On `Done`, tick the remaining epic-level criteria and note any newly-unblocked epics.
